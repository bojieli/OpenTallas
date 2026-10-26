#!/bin/bash
# TOK-DS 10-26: hierarchical Verilator build of a bound_carve_build.py WORK dir (run inside WORK via ot-run --dir WORK).
#   run_carve_build.sh MODE J       MODE = binary (carve.f top = the bench, --binary --timing) | cc (carve as top, --cc)
# hier.vlt makes every kept partition type (per strap-parameter set) and ot_s81c_attn_hcore its own library, so no
# single Verilator / cc1plus run sees more than one partition; flags follow tools/s81_dv/layer_prog/svc/run_svc_bench.sh
# (-O0 slow / -O1, output-split) to bound cc1plus memory.  J = parallel make jobs (= parallel hier blocks).
set -u
MODE=${1:-binary}; J=${2:-16}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version > build.verilator.version
FLAGS=(--hierarchical -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN
       --output-split 20000 --output-split-cfuncs 2000 --unroll-count 16 --unroll-limit 131072
       -MAKEFLAGS "OPT_SLOW=-O0 OPT_FAST=-O1" -CFLAGS -O1 -j "$J" --build-jobs "$J")
case "$MODE" in
  binary) ARGS=(--binary --timing -Mdir obj_bin);;
  cc) ARGS=(--cc --build -Mdir obj_cc)   # carve module as top (replace the bench line in carve.f first)
      sed '/^carve\/tb_/d' carve.f > carve_cc.f
      CAR=$(python3 -c 'import json;print(json.load(open("build_sources.json"))["carve"].rsplit("/",1)[1][:-5])')
      sed -i "0,/^--top-module$/{n;s/.*/$CAR/}" carve_cc.f;;
  *) echo "mode binary|cc" >&2; exit 2;;
esac
F=carve.f; [ "$MODE" = cc ] && F=carve_cc.f
echo "build $MODE start $(date) J=$J"
/usr/bin/time -v -o build_$MODE.time "$VL" "${ARGS[@]}" "${FLAGS[@]}" -f "$F" > build_$MODE.log 2>&1
rc=$?
echo "$rc" > build_$MODE.rc
echo "build $MODE done $(date) rc=$rc peak_kb=$(grep -o 'Maximum resident set size (kbytes): [0-9]*' build_$MODE.time | grep -o '[0-9]*$')"
grep '^%Error' build_$MODE.log | head -20
exit $rc
