"""Reproduce the eight-project corpus with JDK 25, Maven 3.9.11 and Python 3.11+."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/configs/corpus.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd):
    env = {**os.environ, "TZ": "UTC"}
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"{Path(str(cmd[0])).name} exit {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def select(rows, key):
    return {r[key] for r in rows}


def verify(javap_output, static, contexts, normal, shift, config):
    heads = re.compile(r"^  .*?([\w$]+)\([^;]*\).*;$")
    cond = re.compile(r"^\s*(\d+):\s+(if\w+)\s+(\d+)\s*$")
    ground = []
    method = desc = None
    for line in javap_output.splitlines():
        if m := heads.match(line):
            method = m[1]
        if m := re.match(r"^\s+descriptor:\s+(\S+)", line):
            desc = m[1]
        if method in config["method_names"] and (m := cond.match(line)):
            ground.append((method, desc, int(m[1]), m[2].upper(), int(m[3])))
    actual = [(s["method_name"], s["method_descriptor"], s["original_bci"], s["branch_opcode"], s["target_bci"])
              for s in static]
    if not ground or actual != ground:
        raise ValueError(f"javap disagrees with selected bytecode sites in {config['project']}: "
                         f"{(Counter(ground)-Counter(actual)).most_common(3)} "
                         f"{(Counter(actual)-Counter(ground)).most_common(3)}")
    ids = select(static, "branch_id")
    if len(ids) != len(static) or any(s["branch_id"] != f'{s["artifact_sha256"]}:{s["method_index"]}:{s["original_bci"]}'
                                     or s["fallthrough_bci"] != s["original_bci"] + 3 for s in static):
        raise ValueError("Invalid static identity or fallthrough")
    for name, rows in [("context", contexts), ("normal", normal), ("shift", shift)]:
        if len(rows) != len(ids) or select(rows, "branch_id") != ids:
            raise ValueError(f"Invalid {name} join")
        for r in rows:
            if name == "context":
                if any(sum(line.startswith(">> ") for line in r[col].splitlines()) != 1
                       for col in ["context", "masked_context"]):
                    raise ValueError("Missing unique focal instruction")
                continue
            t, f = r["taken_count"], r["fallthrough_count"]
            if t < 0 or f < 0 or r["p_taken"] != (t / (t+f) if t+f else None) or r["workload_id"] != name:
                raise ValueError("Invalid counts or probability")


def jar_file(cfg, cache):
    path = cache / cfg["url"].rsplit("/", 1)[1]
    if not path.exists():
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as tmp:
            partial = Path(tmp.name)
        try:
            with urllib.request.urlopen(cfg["url"], timeout=60) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
            if sha(partial) != cfg["sha256"]:
                raise ValueError(f"Download digest mismatch: {cfg['project']}")
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    if sha(path) != cfg["sha256"]:
        raise ValueError(f"Cached JAR digest mismatch: {path}")
    return path


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main(output, cache):
    cfg = json.loads(CONFIG.read_text())
    output, cache = output.resolve(), cache.resolve()
    if output.exists():
        raise FileExistsError(f"Use a new destination: {output}")
    cache.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    jdk = Path(os.environ["JAVA_HOME"]).resolve()
    java, javac, javap = (jdk / "bin" / name for name in ["java", "javac", "javap"])
    release = dict(line.split("=", 1) for line in (jdk / "release").read_text().splitlines() if "=" in line)
    if not run([javac, "-version"]).startswith("javac 25."):
        raise RuntimeError("JAVA_HOME must reference JDK 25")
    maven = run(["mvn", "-v"]).splitlines()[0]
    if "3.9.11" not in maven:
        raise RuntimeError("Use Maven 3.9.11")
    jars = {p["project"]: jar_file(p, cache) for p in cfg["projects"]}
    build = run(["mvn", "-B", "-ntp", "-f", "java/pom.xml", "clean", "test", "dependency:build-classpath",
                 "-DincludeScope=runtime", "-Dmdep.outputFile=target/runtime-classpath.txt"])
    if "BUILD SUCCESS" not in build:
        raise RuntimeError("Maven build did not complete")
    library_cp = (ROOT / "java/target/runtime-classpath.txt").read_text().strip()
    base = os.pathsep.join([str(ROOT / "java/target/classes"), library_cp])
    vm_flags = ["-Xverify:all", "-Dfile.encoding=UTF-8", "-Duser.language=en", "-Duser.country=US", "-Duser.timezone=UTC"]
    driver = ROOT / "java/corpus/Workloads.java"
    source_files = [CONFIG, driver, ROOT / "java/pom.xml", Path(__file__).resolve(),
                    *sorted((ROOT / "java/src/main").rglob("*.java"))]
    manifest = {"dataset_version": cfg["dataset_version"], "config": str(CONFIG.relative_to(ROOT)),
                "seed": cfg["seed"], "warmup_iterations": 0, "java_vendor": release["IMPLEMENTOR"].strip('"'),
                "java_runtime": release["JAVA_RUNTIME_VERSION"].strip('"'), "os": platform.system(),
                "os_release": platform.release(), "architecture": platform.machine(), "maven": maven,
                "java_vm_flags": vm_flags, "verify": "independent javap of original JAR and matched app output digests",
                "command": "python scripts/corpus.py OUTPUT", "sources": {str(p.relative_to(ROOT)): sha(p) for p in source_files},
                "projects": {}}
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        temp = Path(tmp)
        driver_classes = temp / "driver"
        driver_classes.mkdir()
        run([javac, "--release", "25", "-g:none", "-cp", os.pathsep.join([base, *map(str, jars.values())]),
             "-d", driver_classes, driver])
        staged = temp / "result"
        staged.mkdir()
        for p in cfg["projects"]:
            project = p["project"]
            print(f"Profiling {project}", flush=True)
            target_jar = jars[project]
            work, out = temp / project, staged / project
            work.mkdir()
            out.mkdir()
            cls = work / "input.class"
            with zipfile.ZipFile(target_jar) as archive:
                cls.write_bytes(archive.read(p["target_class"].replace(".", "/") + ".class"))
            runtime_cp = os.pathsep.join([str(driver_classes), str(target_jar), base])
            run([java, *vm_flags, "-cp", runtime_cp, "org.branchpilot.Corpus", cls,
                 ",".join(p["method_names"]), work, out])
            labels = {}
            checks = {}
            for name in ["normal", "shift"]:
                driver_args = ["org.branchpilot.Workloads", project, str(cfg["seed"]), str(cfg["examples"]),
                               str(cfg["family_period"]), str(cfg[name + "_family_a"]), str(work / "inventory.json")]
                reference = run([java, *vm_flags, "-cp", runtime_cp, *driver_args, "-", name])
                traced = run([java, *vm_flags, "-cp", os.pathsep.join([str(work / "patched"), runtime_cp]),
                              *driver_args, out / f"{name}.jsonl", name])
                if reference != traced or not re.fullmatch(r"[0-9a-f]{64}", traced):
                    raise ValueError(f"Reference and instrumented output mismatch for {project}/{name}")
                labels[name] = read_rows(out / f"{name}.jsonl")
                checks[name] = {"reference_sha256": reference, "instrumented_sha256": traced,
                                "observed_sites": sum(r["p_taken"] is not None for r in labels[name]),
                                "edge_executions": sum(r["taken_count"] + r["fallthrough_count"] for r in labels[name])}
                if checks[name]["edge_executions"] == 0:
                    raise ValueError(f"No probes executed for {project}/{name}")
            static, contexts = (read_rows(out / f"{name}.jsonl") for name in ["static", "context"])
            disassembly = run([javap, "-c", "-s", "-p", "-classpath", target_jar, p["target_class"]])
            verify(disassembly, static, contexts, labels["normal"], labels["shift"], p)
            manifest["projects"][project] = {"jar_sha256": sha(target_jar), "class_sha256": sha(cls),
                "classfile_major": int.from_bytes(cls.read_bytes()[6:8], "big"), "static_sites": len(static),
                "checks": checks, "files": {f.name: sha(f) for f in sorted(out.iterdir())}}
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        staged.rename(output)
    print(f"Wrote verified corpus to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/branch-study/jars")
    args = parser.parse_args()
    main(args.output, args.cache)
