#!/bin/bash
# redesign-hbm 2026-10-09: bench of the multi-ck hub quarter wrapper with LOCKUP crossings
# (tools/hbm_hub_quarter_gen.py --xroot lockup).  Run in the source root:  bench_xroot.sh <quarter> <outdir>
#  1. the generator reproduces the committed rtl_xl/<master>.sv (and the default build still reproduces rtl/);
#  2. Verilator lint with the REAL lane RTL;
#  3. tied clocks: 0 mismatches, settle == the baseline wrapper's settle (0 added cycles);
#  4. SKEWED roots (two patterns: even roots +SK ns, then odd roots +SK ns; zero-delay flops): 0 mismatches AND the
#     same settle (cycle-exact under inter-root skew);
#  5. MUTANT A: the baseline wrapper (no lockups) under the same skew must LOSE cycles (hold races shoot data through
#     a crossing): proves the skew bench sees the failure class;  MUTANT B: the lane negative control must mismatch.
set -u; q=$1; O=$2; SK=${SK:-0.30}; m=hfd_$q; [ $q = hcp ] && m=hfd_hc; mkdir -p $O
V=physical/hbm_accel_die_views/$q
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} ports --master $m --out $O/ports > /dev/null
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/base > /dev/null 2>&1
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/xl --xroot lockup > /dev/null 2>&1
fail(){ echo "XROOT_BENCH FAIL: $*"; exit 1; }
cmp -s $O/xl/$m.sv $V/rtl_xl/$m.sv || fail "committed $V/rtl_xl/$m.sv not reproduced"
cmp -s $O/xl/macro_place.tcl $V/rtl_xl/macro_place.tcl || fail "rtl_xl/macro_place.tcl not reproduced"
if [ $q = hcp ]; then LS="rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv"
elif [ $q = hc ]; then LS="rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv"
else LS="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"; fi
if verilator --version | grep -q '^Verilator [5-9]'; then
verilator --lint-only -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSED -Wno-PINCONNECTEMPTY -Wno-VARHIDDEN -Wno-WIDTH -Wno-UNOPTFLAT -Wno-CASEINCOMPLETE -Wno-BLKSEQ -Wno-MULTIDRIVEN --top-module $m $O/xl/$m.sv $LS > $O/lint.log 2>&1
grep -q '%Error' $O/lint.log && fail "verilator lint errors (see $O/lint.log)"
grep -E '%Warning-(UNDRIVEN|PINMISSING|IMPLICIT)' $O/lint.log | grep -q . && fail "verilator: undriven / missing pins (see $O/lint.log)"
echo "lint: verilator clean"; else echo "lint: SKIPPED (Verilator < 5 on this host)"; fi
# skewed testbench: ck<i> through a transport delay (+SK on the roots of parity P), stimulus / sampling after every root edge
skew(){ python3 - "$1" "$2" "$SK" <<'PY'
import re, sys
src, par, sk = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
t = open(src).read()
m = re.search(r'\.(ck\d+)\(clk\)', t)
cks = sorted(set(re.findall(r'\.(ck(\d+))\(clk\)', t)), key=lambda x: int(x[1]))
decl = ''.join(f'    wire {"#%.3f " % sk if int(n) % 2 == par else ""}k_{c} = clk;\n' for c, n in cks)
t = re.sub(r'\.(ck\d+)\(clk\)', lambda mm: f'.{mm.group(1)}(k_{mm.group(1)})', t)
t = t.replace('    initial begin', decl + '    initial begin', 1)
t = t.replace('@(posedge clk); #0.1;', '@(posedge clk); #%.3f;' % (sk + 0.05))
t = t.replace('repeat (6) @(posedge clk); rst = 0;', 'repeat (6) @(posedge clk); #%.3f rst = 0;' % (sk + 0.05))
open(src.replace('tb_', 'tbskew%d_' % par), 'w').write(t)
PY
}
run(){ ( cd $O/$1 && iverilog -g2012 -o $2.vvp $3 $4 *_simstub.sv > $2.comp 2>&1 && vvp -n $2.vvp > $2.log 2>&1; echo "rc=$?"; grep -h OT_RESULT $2.log ) ; }
for d in base xl; do skew $O/$d/tb_$m.sv 0; skew $O/$d/tb_$m.sv 1; done
st(){ sed -n 's/.*mismatches=\([0-9]*\) settle_cycles=\([0-9]*\).*/\1 \2/p'; }
read BM BS < <(run base tied tb_$m.sv $m.sv | st)
echo "baseline tied: mismatches $BM settle $BS"; [ "$BM" = 0 ] || fail "baseline does not pass its own bench"
for t in tied:tb_$m.sv skew0:tbskew0_$m.sv skew1:tbskew1_$m.sv; do
  n=${t%%:*}; tb=${t#*:}; read XM XS < <(run xl $n $tb $m.sv | st)
  echo "lockup $n: mismatches $XM settle $XS"; [ "$XM" = 0 ] && [ "$XS" = "$BS" ] || fail "lockup $n: mismatches $XM settle $XS (want 0 / $BS)"
done
lost=0; for p in 0 1; do read MM MS < <(run base mskew$p tbskew${p}_$m.sv $m.sv | st); echo "MUTANT A baseline skew$p: mismatches $MM settle $MS"; [ "$MS" != "$BS" ] && lost=1; done
[ $lost = 1 ] || fail "MUTANT A: the baseline survived the skew bench cycle-exact (bench cannot see the hold race)"
read NM NS < <(run xl neg tb_$m.sv ${m}_neg.sv | st); echo "MUTANT B lane negative: mismatches $NM"; [ "${NM:-0}" != 0 ] || fail "MUTANT B passed"
echo "XROOT_BENCH PASS ($q: settle $BS cycles, +0; $(grep -o 'xroot: .*' $O/xl/$m.sv))"
