#!/bin/bash
set -eu
R=$(cd -- "$(dirname -- "$0")" && pwd)
exec "$R/ld-linux-x86-64.so.2" --library-path "$R" "$@"
