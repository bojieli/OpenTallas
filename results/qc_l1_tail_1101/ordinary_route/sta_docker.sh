#!/bin/bash
set -euo pipefail
if [ "${1:-}" = run ]; then
 shift
 exec docker run --cpus 2 --memory 16g --memory-swap 16g "$@"
fi
exec docker "$@"
