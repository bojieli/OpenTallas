#!/bin/bash
# TOK-DS-2 (11-01): whole-die S81 Verilator 5.050 --hierarchical build of a die_tok_tb.py bench + the strict-bind RTL.
# A flat build of s81_bound_top does not fit (earlyoom at 192 GiB in the frontend); --hierarchical with one hier_block
# per partition master (397 blocks, ~4-6 GB / ~2 min each) does.  Partitions whose internals the bench forces or reads
# (s_7N_LP lep f_host, seqhost t_host) must NOT be hier blocks (leave them out of HIER).
#   env: TB=bench.sv SIMF=filelist (mkflist.py + resolve.py) HIER=hier.vlt O=outdir J=jobs DEFS="A B ..." (asbuilt defines)
# Status lines go to $O/status.  Re-running resumes: Verilator skips identical hier blocks.
set -u
: "${TB:?}" "${SIMF:?}" "${HIER:?}" "${O:?}"; J=${J:-16}; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=""; for d in ${DEFS:-}; do D="$D +define+$d"; done
echo "BUILD_START $(date -Is) J=$J TB=$TB" >> "$O/status"
/usr/bin/time -v "$VL" --binary --timing --hierarchical -O1 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style \
  -Wno-TIMESCALEMOD -Wno-MULTITOP --output-split 20000 --output-split-cfuncs 2000 -j "$J" --build-jobs "$J" \
  -CFLAGS "-O1 -fno-var-tracking" --top-module tb_s81_die $D "$HIER" "$TB" -f "$SIMF" -Mdir "$O/obj" > "$O/build.log" 2> "$O/build.err"
rc=$?; echo "BUILD_RC $rc $(date -Is)" >> "$O/status"; grep -E "Maximum resident|Elapsed" "$O/build.err" >> "$O/status"; exit $rc
