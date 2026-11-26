"""Trace statically sampled branches in the registered DaCapo workloads."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from corpus import ROOT, read_rows, sha

APPS = {
    "luindex": ("lucene-core-2.4.jar", "org/apache/lucene/index/"),
    "pmd": ("pmd-4.2.5.jar", "net/sourceforge/pmd/ast/"),
    "xalan": ("xalan.jar", "org/apache/xalan/templates/"),
    "sunflow": ("sunflow-0.07.2.jar", "org/sunflow/core/"),
}


def call(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
    log = proc.stdout.decode("utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode})\n{log[-4000:]}")
    return log


def check_javap(javap, jar, static, work):
    classes = defaultdict(list)
    for site in static:
        classes[site["class_name"]].append(site)
    for name, sites in classes.items():
        log = call([javap, "-p", "-c", "-s", "-classpath", jar, name.replace("/", ".")], work)
        method, desc, found = -1, None, set()
        for line in log.splitlines():
            if re.match(r"^  \S", line) and ("(" in line or line.strip() == "static {};"):
                method += 1
            if match := re.match(r"\s+descriptor: (\S+)", line):
                desc = match[1]
            if match := re.fullmatch(r"\s*(\d+):\s+(if\w+)\s+(\d+)\s*", line):
                found.add((method, desc, int(match[1]), match[2].upper(), int(match[3])))
        for s in sites:
            key = tuple(s[k] for k in ("method_index", "method_descriptor", "original_bci", "branch_opcode", "target_bci"))
            if key not in found or s["fallthrough_bci"] != s["original_bci"] + 3:
                raise ValueError(f"javap disagrees with {s['branch_id']} in {name}: {key}")


def trace(app, size, trial, suite, runtime, agent, inventory, work, static, out):
    benchdir = work / f"{app}-{size}-{trial}"
    benchdir.mkdir()
    cmd = [runtime, "-Xmx1500m", "-Xverify:all", "-Djava.awt.headless=true", "-Duser.language=en",
           "-Duser.country=US", "-Duser.timezone=UTC", "-Dfile.encoding=UTF-8"]
    if trial:
        cmd += [f"-Xbootclasspath/a:{agent}", f"-Dbranchpilot.inventory={inventory}", f"-javaagent:{agent}={benchdir}"]
    cmd += ["-jar", suite, "-n", "1", "-t", "1", "-s", size, app]
    log = call(cmd, benchdir)
    marker = re.search(rf"^===== DaCapo .* {app} PASSED in .*?=====$", log, re.M)
    if not marker or " validation FAILED" in log:
        raise ValueError(f"No validated run for {app}/{size}/{trial}\n{log[-3500:]}")
    record = dict(application=app, size=size, trial=trial, validation=marker.group(),
                  log_sha256=hashlib.sha256(log.encode()).hexdigest())
    if trial:
        loaded = (benchdir / "loaded.txt").read_text().splitlines()
        counts = [list(map(int, s.split(","))) for s in (benchdir / "counts.csv").read_text().splitlines()]
        if len(counts) != len(static) or any(len(c) != 2 or min(c) < 0 for c in counts):
            raise ValueError("Invalid trace counts")
        path = out / (f"{size}.jsonl" if trial == 1 else f"{size}-repeat.jsonl")
        with path.open("w") as stream:
            for s, (t, f) in zip(static, counts, strict=True):
                if (t or f) and s["class_name"] not in loaded:
                    raise ValueError("Probe fired in an uninstrumented class")
                row = dict(schema_version="v0", branch_id=s["branch_id"], workload_id=size,
                           taken_count=t, fallthrough_count=f, p_taken=t / (t+f) if t+f else None)
                stream.write(json.dumps(row) + "\n")
        record.update(loaded=loaded, counts_sha256=sha(path))
    shutil.rmtree(benchdir)
    return record


def run(suite, runtime, output):
    suite, runtime, output = [p.resolve() for p in (suite, runtime, output)]
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    jdk = Path(os.environ["JAVA_HOME"]) / "bin"
    cp = os.pathsep.join([str(ROOT / "java/target/classes"), (ROOT / "java/target/runtime-classpath.txt").read_text().strip()])
    version = call([runtime, "-version"], ROOT)
    if '"1.8.' not in version:
        raise ValueError("Use a Java 8 runtime for the legacy benchmark")
    suite_hash = sha(suite)
    if suite_hash != "be3db084adcb2867760e1197b3ccf541c3213d918daa19386d8e236648d24be8":
        raise ValueError("DaCapo release digest mismatch")
    manifest = dict(suite_sha256=suite_hash, runtime=version, preparation_jdk=call([jdk/"javac","-version"],ROOT).strip(),
                    projects={})
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        result = work / "result"
        result.mkdir()
        classes = work / "helper"
        classes.mkdir()
        call([jdk/"javac", "--release", "8", "-d", classes, ROOT/"java/external/TraceAgent.java",
              ROOT/"java/src/main/java/org/branchpilot/Counters.java"], work)
        mf = work / "manifest.mf"
        mf.write_text("Premain-Class: org.branchpilot.TraceAgent\n")
        agent = work / "agent.jar"
        call([jdk/"jar", "cfm", agent, mf, "-C", classes, "."], work)
        with zipfile.ZipFile(suite) as archive:
            for app, (filename, prefix) in APPS.items():
                print(f"Preparing {app}", flush=True)
                config = archive.read(f"cnf/{app}.cnf").decode()
                paths = {}
                for lib in re.findall(r'"([^"]+\.jar)"', re.search(r"\bjars\s+(.*?);", config, re.S)[1]):
                    entry, = [n for n in archive.namelist() if n.rsplit("/", 1)[-1] == lib]
                    paths[lib] = entry
                    (work / lib).write_bytes(archive.read(entry))
                jar = work / filename
                app_cp = os.pathsep.join([cp, *(str(work / lib) for lib in paths)])
                inventory, out = work / app, result / app
                out.mkdir()
                call([jdk/"java", "-cp", app_cp, "org.branchpilot.ExternalInventory",
                      jar, prefix, inventory], work)
                static = read_rows(inventory/"static.jsonl")
                check_javap(jdk/"javap", jar, static, work)
                for file in ("static.jsonl", "context.jsonl", "population.json"):
                    shutil.copy(inventory/file, out/file)
                runs = []
                for size in ("small", "default"):
                    for trial in (0, 1, 2):
                        print(f"{app} {size} run {trial}", flush=True)
                        runs.append(trace(app, size, trial, suite, runtime, agent, inventory, work, static, out))
                manifest["projects"][app] = dict(jar=paths[filename], jar_sha256=sha(jar), package=prefix, runs=runs)
        (result/"manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        result.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("suite", "java8", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.suite, args.java8, args.output)
