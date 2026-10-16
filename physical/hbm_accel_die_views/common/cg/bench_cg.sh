#!/bin/bash
# redesign-hbm 2026-10-09: bench of a hub quarter with COARSE PER-GROUP CLOCK GATING (tools/hbm_hub_quarter_gen.py --cg,
# with --xroot lockup), run in the source root:   bench_cg.sh <quarter> <outdir> <rtl dir name, e.g. rtl_xlcg>
#  1. the generator reproduces the committed <q>/<rtldir>/<master>.sv;
#  2. the gated quarter, with a 200-cycle fully gated gap (wake low, inputs held) before every vector and the wake raised
#     3 edges before the data: 0 mismatches and the SAME settle as the ungated build (cycle-exact after every wake);
#  3. the gates really close (ICG enable low on a group near the band and the farthest group);
#  4. MUTANT A: the wake reaches the gates 4 edges late -> the settle changes;  MUTANT B: the lane negative mismatches.
set -u; q=$1; O=$2; RD=$3; m=hfd_$q; [ $q = hcp ] && m=hfd_hc; mkdir -p $O; V=physical/hbm_accel_die_views/$q
fail(){ echo "HUB_CG_BENCH FAIL: $*"; exit 1; }
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} ports --master $m --out $O/ports > /dev/null
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/base --xroot lockup > /dev/null 2>&1
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/cg --xroot lockup --cg > /dev/null 2>&1
cmp -s $O/cg/$m.sv $V/$RD/$m.sv || fail "committed $V/$RD/$m.sv not reproduced"
C="rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv"
st(){ sed -n 's/.*mismatches=\([0-9]*\) settle_cycles=\([0-9]*\).*/\1 \2/p'; }
( cd $O/base && iverilog -g2012 -o b tb_$m.sv $m.sv *_simstub.sv && vvp -n b > b.log ); read BM BS < <(st < $O/base/b.log)
G=$(grep -o 'u_cg_[0-9]*_[0-9]*' $O/cg/$m.sv | sort -t_ -k4 -n | sed -n '1p;$p' | tr '\n' ' '); set -- $G
printf 'module mon; integer a=0, b=0;\n always @(posedge tb.clk) begin if (!tb.dut.%s.en) a=a+1; if (!tb.dut.%s.en) b=b+1; end\n final $display("CG_GATED %s %%0d %s %%0d", a, b);\nendmodule\n' $1 $2 $1 $2 > $O/cg/mon.sv
( cd $O/cg && iverilog -g2012 -o p tb_$m.sv mon.sv $m.sv *_simstub.sv $(for f in $C; do echo $OLDPWD/$f; done) && vvp -n p > p.log ) || fail "gated build"
read PM PS < <(st < $O/cg/p.log); echo "ungated settle $BS; gated: mismatches $PM settle $PS; $(grep CG_GATED $O/cg/p.log)"
[ "$PM" = 0 ] && [ "$PS" = "$BS" ] || fail "gated quarter: mismatches $PM settle $PS (want 0 / $BS)"
ga=$(sed -n 's/CG_GATED [^ ]* \([0-9]*\) .*/\1/p' $O/cg/p.log); gb=$(sed -n 's/CG_GATED .* \([0-9]*\)$/\1/p' $O/cg/p.log)
[ "${ga:-0}" -gt 0 ] && [ "${gb:-0}" -gt 0 ] || fail "the gates never closed ($ga / $gb)"
( cd $O/cg && iverilog -g2012 -DOT_HUB_CG_MUT_LATE -o l tb_$m.sv $m.sv *_simstub.sv $(for f in $C; do echo $OLDPWD/$f; done) && vvp -n l > l.log ); read LM LS < <(st < $O/cg/l.log)
echo "MUTANT A late wake: mismatches $LM settle $LS"; [ "$LS" != "$BS" ] || [ "$LM" != 0 ] || fail "MUTANT A (late wake) survived"
( cd $O/cg && iverilog -g2012 -o n tb_$m.sv ${m}_neg.sv *_simstub.sv $(for f in $C; do echo $OLDPWD/$f; done) && vvp -n n > n.log ); read NM NS < <(st < $O/cg/n.log)
echo "MUTANT B lane negative: mismatches $NM"; [ "${NM:-0}" != 0 ] || fail "MUTANT B survived"
echo "HUB_CG_BENCH PASS ($q: settle $BS, +0 cycles; gated cycles $ga / $gb)"
