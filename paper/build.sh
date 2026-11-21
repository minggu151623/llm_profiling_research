#!/bin/sh
# Build paper/build/main.pdf with Tectonic and pack the arXiv upload (main.tex, main.bbl, figure).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out="$here/build"
rm -rf "$out"
mkdir -p "$out"
cp "$here/main.tex" "$here/project-results.png" "$out/"
cp "$here/../research/literature/papers.bib" "$out/references.bib"
cd "$out"
tectonic -X compile main.tex --keep-intermediates --keep-logs
echo "PDF: $out/main.pdf"
if grep -q "COAUTHOR NAME" main.tex; then
  echo "Not packing the arXiv upload: replace the co-author placeholder in paper/main.tex first." >&2
  exit 1
fi
tar -czf arxiv.tar.gz main.tex main.bbl project-results.png
echo "arXiv upload: $out/arxiv.tar.gz"
