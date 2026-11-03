#!/bin/bash
set -euo pipefail
if [ "${1:-}" = run ]; then
  shift
  exec docker run --memory=8g --memory-swap=8g --cpus=2 "$@"
fi
exec docker "$@"
