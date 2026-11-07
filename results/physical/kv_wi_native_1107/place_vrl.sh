#!/bin/bash
set -eu
R=$(cd "$(dirname "$0")" && pwd)
exec bash "$R/run_kit.sh" "$R/kv3_hub_Wi" place 64 8
