#!/bin/bash
# apply_D.sh STAGED_TREE [--mode dfi-core|hbm-lanes]: KV boot fix D (see apply_D.py; default dfi-core = owner decision 14)
set -eu
H=$(cd "$(dirname "$0")" && pwd)
exec python3 "$H/apply_D.py" "$@"
