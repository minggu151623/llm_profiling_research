"""Run the automated checks in java/TESTING.md and print the report block with those fields filled in.

The manual checks M1 to M7 stay blank: they are meant to be done by hand, as java/MANUAL_TESTING.md describes.
Needs the Temurin 25 JDK and Maven 3.9.11 on PATH. Uses only the standard library.
"""
from pathlib import Path
import filecmp
import platform
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def first_line(text):
    return text.strip().splitlines()[0] if text.strip() else "not found"


def main():
    commit = run("git", "rev-parse", "--short", "HEAD").stdout.strip()
    if run("git", "status", "--porcelain").stdout.strip():
        commit += " (with uncommitted local changes)"
    java = first_line(run("java", "-version").stderr)
    maven = first_line(run("mvn", "-v").stdout)

    print("Running mvn clean test ...", file=sys.stderr)
    tests = run("mvn", "-B", "-ntp", "-f", "java/pom.xml", "clean", "test")
    counts = [tuple(map(int, m)) for m in re.findall(
        r"Tests run: (\d+), Failures: (\d+), Errors: (\d+)",
        "".join(p.read_text() for p in (ROOT / "java/target/surefire-reports").glob("*.txt")))]
    total, failures = sum(c[0] for c in counts), sum(c[1] + c[2] for c in counts)
    junit = f"{total} tests, {failures} failures" + ("" if tests.returncode == 0 else " (mvn exited with an error)")

    with tempfile.TemporaryDirectory() as scratch:
        print("Rebuilding the corpus ...", file=sys.stderr)
        corpus = run(sys.executable, "scripts/corpus.py", f"{scratch}/corpus")
        expected = sorted((ROOT / "experiments/study/corpus").glob("*/*.jsonl"))
        same = [p for p in expected if corpus.returncode == 0 and
                filecmp.cmp(p, Path(scratch) / "corpus" / p.relative_to(ROOT / "experiments/study/corpus"), shallow=False)]
        differing = [str(p.relative_to(ROOT)) for p in expected if p not in same]

    verify = run(sys.executable, "scripts/verify_study.py", "experiments/study/corpus", "experiments/study/slm",
                 "experiments/study/evaluation")

    print(f"""Commit tested: {commit}
OS and architecture: {platform.system()} {platform.release()} {platform.machine()}
java -version: {java}
mvn -v (first line): {maven}
JUnit: {junit}
cmp: {len(same)} of {len(expected)} files identical
verify_study.py: {"pass" if verify.returncode == 0 else "fail"}
Manual checks (MANUAL_TESTING.md): M1 __ M2 __ M3 __ M4 __ M5 __ M6 __ M7 __
Notes:""")
    if corpus.returncode:
        print(f"  corpus.py failed: {first_line(corpus.stderr[-2000:])}")
    if differing:
        print(f"  differing files: {', '.join(differing)}")
    if verify.returncode:
        print(f"  verify_study.py: {first_line(verify.stderr.strip().splitlines()[-1] if verify.stderr.strip() else '')}")


if __name__ == "__main__":
    main()
