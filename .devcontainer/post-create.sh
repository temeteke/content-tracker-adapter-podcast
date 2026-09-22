#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m pip install   "git+https://github.com/temeteke/content-tracker.git#subdirectory=backend"
python -m pip install -e "${repo_root}[dev]"
