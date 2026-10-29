#!/bin/bash
# Build the explicit native source emitted by prepare_native.py, under ot-run.
# Usage: build_native.sh nl|nk PROOF_DIR BENCH_SV GEN_ROM_PY [JOBS]
set -euo pipefail
tile=$1; proof=$(realpath "$2"); bench=$(realpath "$3"); gen_rom=$(realpath "$4"); jobs=${5:-16}
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mapfile -t src < "$proof/files.txt"
defs=(+define+TB_ICG=2 +define+TB_REGROOT=3 +define+OT_ROM_CONST0_KV)
[[ $tile == nl ]] && defs+=(+define+TB_NL)
python3 "$gen_rom" "$proof/rom" 48
verilator --version > "$proof/verilator.version"
sha256sum "$bench" "${src[@]}" > "$proof/sources.sha256"
verilator --binary --timing -j "$jobs" -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style \
  -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "${defs[@]}" --top-module tb_a0_icg \
  -Mdir "$proof/obj" "$bench" "${src[@]}" > "$proof/build.log" 2>&1
echo "NATIVE_BUILD_OK $tile REGROOT=3 ICG=2 no_FP1"
