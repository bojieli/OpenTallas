#!/bin/bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
# Verilator5.044+ provides this documented containment for excessive eager
# function inlining. Existing hierarchy children remain their actual RTL libs.
exec "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" "$@" \
 -fno-inline-funcs-eager "$here/native_endpoint_noinline.vlt"
