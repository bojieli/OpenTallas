#!/bin/bash
# Safe replacement for the old in-place runner. Legacy positional calls fail closed.
# See: python3 tools/qwen_dietop_launch.py --help
set -euo pipefail
exec python3 "$(dirname "$(readlink -f "$0")")/qwen_dietop_launch.py" "$@"
