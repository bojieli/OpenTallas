#!/bin/bash
set -euo pipefail
B=$(cd "$(dirname "$0")" && pwd)
cd "$B"
sha256sum -c INPUTS.sha256
bash project_reset.sh "$B" diag1340
