#!/bin/bash
set -euo pipefail
stage=$(cd "$(dirname "$0")" && pwd)
exec bash "$stage/run_case.sh" "$stage/discovery_fixed_extended" "$stage/vectors/full8192" 8192 steady 13891388138805aa07bc076c06af032705aa03200352
