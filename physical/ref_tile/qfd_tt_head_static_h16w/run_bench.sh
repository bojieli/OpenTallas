#!/bin/bash
# usage: run_bench.sh WORK IMG [BMUT]   (Verilator 5.050 = closure daemon pin)
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 physical/ref_tile/qfd_tt_head_static_h16w/prepare_bench.py || exit 2
extra=(); [ -n "${3:-}" ] && extra=(--bmut "$3")
python3 rtl/test/qwen_dv/tt_ctlm_prog_native32_1r_bench.py --decode 3 --hard 1 --segcal 1 "${extra[@]}" --work "$1" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/$2
