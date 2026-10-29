#!/bin/bash
# DIE-QC-34 v2: same as build_run.sh with the drain bound fixed (63) -> native_<tile>_v2, then run_controls.sh
set -uo pipefail
tile=$1; M=/srv/opentallas-scratch2/claude/die-qc34-a0/proof; P=/srv/opentallas-scratch2/claude/codex-qc-proof-0831
d=$M/native_${tile}_v2; mkdir -p $d; cp $P/native_$tile/files.txt $d/
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mapfile -t src < $d/files.txt
defs=(+define+TB_ICG=2 +define+TB_REGROOT=3 +define+OT_ROM_CONST0_KV +define+TB_CONTRACT)
[[ $tile == nl ]] && defs+=(+define+TB_NL)
verilator --version > $d/verilator.version
sha256sum $M/tb_a0_icg.sv "${src[@]}" > $d/sources.sha256
verilator --binary --timing -j 16 -O2 -Wno-fatal -Wno-PINMISSING -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  "${defs[@]}" --top-module tb_a0_icg -Mdir $d/obj $M/tb_a0_icg.sv "${src[@]}" > $d/build.log 2>&1 || exit 1
bash $M/run_controls.sh $tile $d
