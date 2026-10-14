#!/bin/bash
# q13 2026-10-13: the die tile ot_qfd_su_cbuf_g (pin registers on every face, far-ROM latency strap f_lat) as the die
# uses it: eight tiles side by side (grp strap 0..7) against the constant ROM's contract (tb_qfd_crom_lbuf TILE 1).
#   cbuf_g_tile_bench.sh pos OUT : f_lat = far latency 11 (r22k), 17, 5 and 30 -> CBUF_G_TILE_PASS (bit-exact, checks > 0)
#   cbuf_g_tile_bench.sh neg OUT : MUT 1 (OSC row off by one), MUT 2 (fill into the in-use bank), NOWAIT (SU ignores
#                                  st_rdy), LATERR (strap one edge off the far ROM's latency) must each FAIL
#                                  -> CBUF_G_TILE_NEG_DETECTED (rc 1)
set -u
m=$1; o=$2; mkdir -p "$o"
S=(-s tb_qfd_crom_lbuf rtl/test/redesign_qwen/tb_qfd_crom_lbuf.sv rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv rtl/hdc/ot_hdc_delay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
T=(-Ptb_qfd_crom_lbuf.SRAM=1 -Ptb_qfd_crom_lbuf.GRPS=1 -Ptb_qfd_crom_lbuf.TILE=1)
run() { local n=$1; shift; iverilog -g2012 -o "$o/$n.vvp" "${T[@]}" "$@" "${S[@]}" > "$o/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; return 2; }
        vvp -n "$o/$n.vvp" > "$o/$n.log" 2>&1; tail -1 "$o/$n.log"; grep -q '^PASS crom_lbuf .*TILE=1 ' "$o/$n.log"; }
if [[ $m == pos ]]; then
  ok=1
  run lat11 -Ptb_qfd_crom_lbuf.FLP=11 -Ptb_qfd_crom_lbuf.NTOK=2 || ok=0
  run lat17 -Ptb_qfd_crom_lbuf.FLP=17 -Ptb_qfd_crom_lbuf.NTOK=2 -Ptb_qfd_crom_lbuf.SEED=5 || ok=0
  run lat5  -Ptb_qfd_crom_lbuf.FLP=5  -Ptb_qfd_crom_lbuf.NTOK=2 -Ptb_qfd_crom_lbuf.SEED=7 || ok=0
  run lat30 -Ptb_qfd_crom_lbuf.FLP=30 -Ptb_qfd_crom_lbuf.NTOK=2 -Ptb_qfd_crom_lbuf.RPS=40 -Ptb_qfd_crom_lbuf.SEED=9 || ok=0
  [[ $ok == 1 ]] && { echo CBUF_G_TILE_PASS; exit 0; }; echo CBUF_G_TILE_FAIL; exit 1
fi
det=0
run mut1 -DOT_CBUF_G_MUT=1 -Ptb_qfd_crom_lbuf.NTOK=2 || det=$((det+1))
run mut2 -DOT_CBUF_G_MUT=2 -Ptb_qfd_crom_lbuf.NTOK=2 || det=$((det+1))
run nowait -Ptb_qfd_crom_lbuf.NOWAIT=1 -Ptb_qfd_crom_lbuf.NTOK=2 || det=$((det+1))
run laterr -Ptb_qfd_crom_lbuf.LATERR=1 -Ptb_qfd_crom_lbuf.NTOK=2 || det=$((det+1))
[[ $det == 4 ]] && { echo CBUF_G_TILE_NEG_DETECTED; exit 1; }; echo "CBUF_G_TILE_NEG_MISSED ($det of 4)"; exit 0
