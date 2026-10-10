#!/bin/bash
# redesign-qwen 2026-10-09: ot_qfd_crom_lbuf (SU-local constant buffer) against the constant ROM's contract.
#   crom_lbuf_bench.sh pos OUT : FLP 11 (r22k: crom 5 + 3 + 3 relays) and FLP 17, 3 tokens x 37 stages -> CROM_LBUF_PASS
#   crom_lbuf_bench.sh neg OUT : MUT 1 (OSC row off by one), MUT 2 (fill into the in-use bank), NOWAIT (SU ignores st_rdy)
#                                must each FAIL -> CROM_LBUF_NEG_DETECTED (rc 1)
set -u
m=$1; o=$2; mkdir -p "$o"
S=(rtl/test/redesign_qwen/tb_qfd_crom_lbuf.sv rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv rtl/hdc/ot_hdc_delay.sv)
run() { local n=$1; shift; iverilog -g2012 -o "$o/$n.vvp" "$@" "${S[@]}" > "$o/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; return 2; }
        vvp -n "$o/$n.vvp" > "$o/$n.log" 2>&1; tail -1 "$o/$n.log"; grep -q '^PASS crom_lbuf' "$o/$n.log"; }
if [[ $m == pos ]]; then
  ok=1; run flp11 -Ptb_qfd_crom_lbuf.FLP=11 || ok=0; run flp17 -Ptb_qfd_crom_lbuf.FLP=17 -Ptb_qfd_crom_lbuf.SEED=5 || ok=0
  [[ $ok == 1 ]] && { echo CROM_LBUF_PASS; exit 0; }; echo CROM_LBUF_FAIL; exit 1
fi
det=0
run mut1 -Ptb_qfd_crom_lbuf.MUT=1 || det=$((det+1))
run mut2 -Ptb_qfd_crom_lbuf.MUT=2 || det=$((det+1))
run nowait -Ptb_qfd_crom_lbuf.NOWAIT=1 || det=$((det+1))
[[ $det == 3 ]] && { echo CROM_LBUF_NEG_DETECTED; exit 1; }; echo "CROM_LBUF_NEG_MISSED ($det of 3)"; exit 0
