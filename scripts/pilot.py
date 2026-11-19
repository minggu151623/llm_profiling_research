"""Run the Decisions fixture and publish a complete result directory on success."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
from validate import load_examples


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{args[0]} exited {result.returncode}\n{result.stdout}")
    return result.stdout


def main(destination):
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Choose a new result directory: {destination}")
    config_file = ROOT / "experiments/configs/pilot.json"
    config = json.loads(config_file.read_text())
    if config["warmup_iterations"] != 0:
        raise ValueError("The pilot measures one invocation with no warmup")
    for key, values in config["workloads"].items():
        if not re.fullmatch("[a-z0-9-]+", key) or key == "static":
            raise ValueError(f"Invalid workload name: {key}")
        if not isinstance(values, list) or any(type(n) is not int or not -(2**31) <= n < 2**31 for n in values):
            raise ValueError(f"Each input in {key} must be a Java int")
    jdk = Path(os.environ["JAVA_HOME"]).resolve()
    java, javac, javap = (jdk / "bin" / name for name in ("java", "javac", "javap"))
    version = run([java, "-version"]).strip()
    compiler = run([javac, "-version"]).strip()
    if not compiler.startswith("javac 25."):
        raise RuntimeError(f"Set JAVA_HOME to JDK 25 (found {compiler})")
    build = run(["mvn", "-B", "-ntp", "-f", "java/pom.xml", "clean", "test",
                 "dependency:build-classpath", "-DincludeScope=runtime",
                 "-Dmdep.outputFile=target/runtime-classpath.txt"])
    print("\n".join(line for line in build.splitlines() if "Tests run:" in line or "BUILD SUCCESS" in line))
    target = ROOT / "java/target"
    classpath = os.pathsep.join([str(target / "classes"), (target / "runtime-classpath.txt").read_text().strip()])
    fixture = ROOT / "java/fixtures/Decisions.java"
    run([javac, "--release", "25", "-g:none", "-d", target, fixture])
    original = target / "fixture/Decisions.class"
    command = [java, *config["vm_flags"], "-cp", classpath, "org.branchpilot.Pilot"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        out = Path(tmp) / "result"
        out.mkdir()
        (out / "javap.txt").write_text(run([javap, "-c", "-s", original]))
        run([*command, "extract", original, out / "static.jsonl"])
        logs = []
        profiles = {}
        for workload in config["workloads"]:
            path = out / f"{workload}.jsonl"
            logs.append(run([*command, "profile", original, config_file, workload, path]).strip())
            profiles[workload] = path
        rows = load_examples(out / "static.jsonl", profiles)
        if not rows:
            raise ValueError("The Decisions pilot must contain conditional branches")
        observed = sum(label["p_taken"] is not None for _, _, _, label in rows)
        logs.append(f"{len(rows)} site/workload pairs, {observed} observed, {len(rows)-observed} unobserved")
        (out / "run.log").write_text("\n".join(logs) + "\n")
        sources = [fixture, config_file, ROOT / "java/pom.xml", ROOT / "data/validate.py",
                   ROOT / "data/requirements.txt", Path(__file__).resolve(),
                   *sorted((ROOT / "java/src").rglob("*.java")), *sorted((ROOT / "data/schema").glob("*.json"))]
        release = dict(line.split("=", 1) for line in (jdk / "release").read_text().splitlines() if "=" in line)
        manifest = {
            "dataset_version": config["dataset_version"], "project_id": config["project_id"],
            "artifact_sha256": digest(original), "classfile_major": int.from_bytes(original.read_bytes()[6:8], "big"),
            "jdk_vendor": release["IMPLEMENTOR"].strip('"'), "java_version_output": version,
            "javac": compiler, "maven": next(line for line in run(["mvn", "-v"]).splitlines() if "Apache Maven" in line),
            "os": platform.system(), "os_release": platform.release(), "arch": platform.machine(),
            "python": platform.python_version(), "jsonschema": importlib.metadata.version("jsonschema"),
            "seed": config["seed"], "vm_flags": config["vm_flags"], "warmup_iterations": config["warmup_iterations"],
            "command": "python scripts/pilot.py <new-output-directory>",
            "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
            "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir())},
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        out.rename(destination)
        print("\n".join(logs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
