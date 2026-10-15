#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
VM_READ_PIPE=4 VM_CAP_PIPE=2 bash static_master_gate.sh "$PWD/src" "$PWD/result" all
