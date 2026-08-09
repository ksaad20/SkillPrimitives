#!/bin/bash
set -euo pipefail
if grep -rn '<<<<<<< HEAD' --include='*.py' --include='*.js' --include='*.ts' --include='*.yaml' --include='*.yml' --include='*.md' --exclude-dir=.git --exclude-dir=.github .; then
  echo "Error: Found merge conflict markers in source files"
  exit 1
fi
