"""Check the eight unmodified DaCapo workloads on the preparation JDK."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from corpus import sha
from external_corpus import APPS


def check(suite, java):
    digest = sha(suite)
    if digest != "be3db084adcb2867760e1197b3ccf541c3213d918daa19386d8e236648d24be8":
        raise ValueError("Unexpected DaCapo release")
    version = subprocess.check_output([java,"-version"], stderr=subprocess.STDOUT, text=True)
    if not re.search(r'version "25[."]', version):
        raise ValueError("Use a Java 25 runtime")
    results = []
    for app in APPS:
        for size in ("small", "default"):
            with tempfile.TemporaryDirectory() as scratch:
                result = subprocess.run([java, "-Xmx1500m", "-Xverify:all", "-Djava.awt.headless=true",
                    "-Duser.language=en", "-Duser.country=US", "-Duser.timezone=UTC", "-Dfile.encoding=UTF-8",
                    "-jar",suite,"-n","1","-t","1","-s",size,app], cwd=scratch, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
                log = result.stdout
                passed = result.returncode == 0 and bool(re.search(rf"^===== DaCapo .* {app} PASSED in ", log, re.M))
                causes = [line.strip() for line in log.splitlines()
                          if "Exception" in line or "Error" in line or "FAILED" in line]
                results.append(dict(application=app, size=size, passed=passed, exit_code=result.returncode,
                                    diagnostic="" if passed else "\n".join(causes[:12]) or log[-600:]))
    return dict(suite_sha256=digest, java=version, results=results)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("suite","java","output"):
        p.add_argument(key, type=Path)
    args = p.parse_args()
    data = check(args.suite.resolve(),args.java.resolve())
    with args.output.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
