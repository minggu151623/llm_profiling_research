"""Check that paper/main.tex stays in step with paper/manuscript.md and that every link resolves.

1. The multiset of numbers in the two texts must match, ignoring link targets, table and figure labels
   and LaTeX layout arguments.
2. Every relative link in the Markdown must point to a file or directory in this checkout.
3. Every \\repo{path} in the LaTeX must exist at the commit named by \\repocommit.
Uses only the standard library and git.
"""
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
NUMBER = re.compile(r"(?<![\w.])[0-9]+(?:[.,][0-9]+)*")


def markdown_numbers(text):
    text = text.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    text = re.sub(r"`[0-9a-f]{40}`", "", text)
    text = re.sub(r"\*\*(Table|Figure) \d+\.\*\*", "", text)
    text = re.sub(r"\b(Table|Figure) \d+\b", "", text)
    text = re.sub(r"§\d+(\.\d+)*", "", text)
    return Counter(NUMBER.findall(text))


def latex_numbers(text):
    text = text[text.index(r"\begin{abstract}"):]
    for pattern in (r"\\repo\{[^}]*\}", r"\\href\{[^}]*\}", r"\\citep(\[[^\]]*\])?\{[^}]*\}",
                    r"\\texttt\{ea3f[0-9a-f]+\}", r"\\cmidrule\([^)]*\)\{[^}]*\}", r"\\setlength\{[^}]*\}\{[^}]*\}",
                    r"\\multicolumn\{\d+\}", r"\\frac\{[^{}]*(\{[^{}]*\}[^{}]*)*\}\{2\}", r"\\(label|ref)\{[^}]*\}"):
        text = re.sub(pattern, "", text)
    return Counter(NUMBER.findall(text))


def main():
    markdown = (PAPER / "manuscript.md").read_text()
    latex = (PAPER / "main.tex").read_text()
    problems = []

    md, tex = markdown_numbers(markdown), latex_numbers(latex)
    if md != tex:
        problems.append(f"numbers only in manuscript.md: {dict(md - tex)}; only in main.tex: {dict(tex - md)}")

    for target in re.findall(r"\]\((\.\.?/[^)#\s]+)", markdown):
        if not (PAPER / target).exists():
            problems.append(f"manuscript.md links to missing {target}")

    commit = re.search(r"\\newcommand\{\\repocommit\}\{([0-9a-f]{40})\}", latex).group(1)
    for path in sorted(set(re.findall(r"\\repo\{([^}]+)\}", latex))):
        found = subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
        if found.returncode:
            problems.append(f"main.tex links to {path}, which is absent at {commit[:7]}")

    if problems:
        sys.exit("\n".join(problems))
    print(f"Paper check passed: {sum(md.values())} numbers match, links resolve at {commit[:7]}.")


if __name__ == "__main__":
    main()
