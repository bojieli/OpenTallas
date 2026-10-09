#!/bin/bash
# cont-takeover 2026-10-09: exact benches + negative mutants for the distributed-HC structural successors
# (MACRO_CAP registered SRAM boundaries on ot_dsrom_hc_seed_join / ot_dsrom_hc_mean_capture, PLAIN_ROWS reader).
# Run from the source root (the closure loop's {SRC}).   hc_bench.sh <case> pos|neg <workdir>
#   pos prints HCB_<case>_PASS (rc 0) only if every positive run passes; neg prints HCB_<case>_NEG_FAIL (rc 1) only if the
#   mutant is rejected by the same bench.  Anything else prints HCB_<case>_BENCH_ERROR (rc 2).
set -u
E=$1; M=$2; W=$3; mkdir -p "$W"; W=$(cd "$W" && pwd)
ok()  { echo "HCB_${E}_PASS"; exit 0; }
bad() { echo "HCB_${E}_NEG_FAIL"; exit 1; }
nok() { echo "HCB_${E}_BENCH_ERROR: $*"; exit 2; }
D=rtl/experimental/dsrom_hc_capture_20261009; T=rtl/test/dsrom_hc_capture_20261009
SRAM=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
COMMON="$D/ot_dsrom_hc_secded_pipe.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $SRAM"
FP="rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv"
ivl() { local top=$1 out=$2; shift 2; iverilog -g2012 -s $top -o "$out" "$@" > "$out.build.log" 2>&1 || { cat "$out.build.log"; nok "iverilog $top"; }; }
mutate() { grep -qF -- "$3" "$1" || nok "mutant needle missing in $1"; python3 - "$1" "$2" "$3" "$4" <<'PY'
import sys; s=open(sys.argv[1]).read(); open(sys.argv[2],'w').write(s.replace(sys.argv[3],sys.argv[4],1))
PY
}
python3 tools/dsrom_hc_mean_capture_vectors.py --out $W/vectors > $W/vectors.log 2>&1 || nok vectors
V=+vectors=$W/vectors
case $E in
join_mc)
  J=$D/ot_dsrom_hc_seed_join.sv; DEF="-DHC_ECC_PIPE -DHC_MACRO_CAP"
  if [ $M = pos ]; then
    ivl tb_hc_seed_join $W/p.vvp $DEF $COMMON $J $T/tb_hc_seed_join.sv
    vvp $W/p.vvp $V > $W/p.log 2>&1; grep -q '^PASS join120frames' $W/p.log || { tail $W/p.log; nok positive; }
    vvp $W/p.vvp $V +reset=1 > $W/r.log 2>&1; grep -q '^PASS join120frames' $W/r.log || { tail $W/r.log; nok reset; }
    for bb in 1 2 3 4 5 6 7; do vvp $W/p.vvp $V +bad=$bb > $W/b$bb.log 2>&1; grep -q "^PASS join negative $bb" $W/b$bb.log || { tail $W/b$bb.log; nok "negative $bb"; }; done
    for inj in CE UE; do ivl tb_hc_seed_join $W/$inj.vvp $DEF -DHC_INJECT_$inj $COMMON $J $T/tb_hc_seed_join.sv
      vvp $W/$inj.vvp $V > $W/$inj.log 2>&1; grep -q '^PASS join' $W/$inj.log || { tail $W/$inj.log; nok $inj; }; done
    cat $W/p.log | grep PASS; ok
  else mutate $J $W/mut.sv "rframe<=rframe+1'b1;state<=READ;" "rframe<=rframe+2'd2;state<=READ;"
    ivl tb_hc_seed_join $W/n.vvp $DEF $COMMON $W/mut.sv $T/tb_hc_seed_join.sv; vvp $W/n.vvp $V > $W/n.log 2>&1
    grep -qE 'mismatch|FATAL|fatal' $W/n.log && ! grep -q '^PASS join120frames' $W/n.log && bad; tail $W/n.log; nok "mutant escaped"; fi ;;
mean_mc)
  MC=$D/ot_dsrom_hc_mean_capture.sv; J=$D/ot_dsrom_hc_seed_join.sv; R=$D/ot_dsrom_hc_input_reader.sv; DEF="-DHC_ECC_PIPE -DHC_MACRO_CAP"
  SRC="$COMMON $FP $MC $R $J $T/tb_hc_mean_capture.sv"
  if [ $M = pos ]; then
    ivl tb_hc_mean_capture $W/p.vvp $DEF $SRC; vvp $W/p.vvp $V > $W/p.log 2>&1; grep -q '^PASS full shape' $W/p.log || { tail $W/p.log; nok positive; }
    ivl tb_hc_mean_capture $W/d.vvp $DEF -DHC_DISTRIBUTED $SRC; vvp $W/d.vvp $V > $W/d.log 2>&1; grep -q '^PASS full shape' $W/d.log || { tail $W/d.log; nok distributed; }
    for bb in 1 2 3 4 5 10; do vvp $W/p.vvp $V +bad=$bb > $W/b$bb.log 2>&1; grep -q '^PASS negative' $W/b$bb.log || { tail $W/b$bb.log; nok "negative $bb"; }; done
    for inj in CE UE; do ivl tb_hc_mean_capture $W/$inj.vvp $DEF -DHC_INJECT_$inj $SRC; vvp $W/$inj.vvp $V > $W/$inj.log 2>&1
      grep -q '^PASS' $W/$inj.log || { tail $W/$inj.log; nok $inj; }; done
    grep -h PASS $W/p.log $W/d.log; ok
  else ivl tb_hc_mean_capture $W/n.vvp $DEF -DHC_MUT_TREE $SRC; vvp $W/n.vvp $V > $W/n.log 2>&1
    grep -q 'mean/identity/order mismatch' $W/n.log && ! grep -q '^PASS full shape' $W/n.log && bad; tail $W/n.log; nok "mutant escaped"; fi ;;
reader_plain|reader_ecc)
  MC=$D/ot_dsrom_hc_mean_capture.sv; R=$D/ot_dsrom_hc_input_reader.sv; DEF="-DHC_ECC_PIPE -DHC_MACRO_CAP -DHC_VM_READER"
  [ $E = reader_plain ] && DEF="$DEF -DHC_PLAIN_ROWS"
  if [ $M = pos ]; then
    ivl tb_hc_mean_capture $W/p.vvp $DEF $COMMON $FP $MC $R $T/tb_hc_mean_capture.sv
    vvp $W/p.vvp $V > $W/p.log 2>&1; grep -q '^PASS full shape' $W/p.log || { tail $W/p.log; nok positive; }
    for rk in 1 2 3; do vvp $W/p.vvp $V +rank=$rk > $W/rk$rk.log 2>&1; grep -q '^PASS full shape' $W/rk$rk.log || { tail $W/rk$rk.log; nok "rank $rk"; }; done
    grep -h PASS $W/p.log; ok
  else mutate $R $W/mut.sv "decoded[c][256*half_q+32*l+16+:16]" "decoded[c][256*half_q+32*l+:16]"   # wrong BF16 half of each word
    ivl tb_hc_mean_capture $W/n.vvp $DEF $COMMON $FP $MC $W/mut.sv $T/tb_hc_mean_capture.sv; vvp $W/n.vvp $V > $W/n.log 2>&1
    grep -qE 'mismatch|fault|fatal|FATAL' $W/n.log && ! grep -q '^PASS full shape' $W/n.log && bad; tail $W/n.log; nok "mutant escaped"; fi ;;
*) nok "unknown case $E" ;;
esac
