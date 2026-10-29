#!/bin/bash
# HBM-CORES-KITS-4: ot_hdc_fp32_add_n32 err[1] fix check, LAT 3..6 x DRST 0/1, old (main) vs new (fix):
#  equiv_* (state matched by name, equiv_induct) and a miter whose outputs must agree at every cycle >= 8 from an
#  undefined power-up state (BMC 30 cycles, -set-init-undef) + temporal induction (unbounded).
cd /n32
for lat in 3 4 5 6; do for drst in 0 1; do
  for v in old new bad; do
    cat > s_${v}_${lat}_${drst}.ys <<YS
read_verilog -sv /n32/$v/ot_hdc_fp32_add_n32.sv /n32/ot_hdc_prefix.sv
chparam -set LAT $lat -set DRST $drst ot_hdc_fp32_add_n32
hierarchy -top ot_hdc_fp32_add_n32
setattr -mod -unset keep_hierarchy *
proc; flatten; opt -full; memory; opt -full; clean -purge
rename -top g_$v
write_verilog -noattr /n32/out/${v}_${lat}_${drst}.v
YS
    yosys -q -s s_${v}_${lat}_${drst}.ys > out/${v}_${lat}_${drst}.log 2>&1 || echo "SYNTH FAIL $v $lat $drst"
  done
  cat > e_${lat}_${drst}.ys <<YS
read_verilog /n32/out/old_${lat}_${drst}.v /n32/out/new_${lat}_${drst}.v
proc; async2sync; opt_clean
equiv_make g_old g_new eq
hierarchy -top eq
equiv_simple -seq 8
equiv_induct -seq 8
equiv_status -assert
YS
  if yosys -q -s e_${lat}_${drst}.ys > out/e_${lat}_${drst}.log 2>&1; then echo "LAT $lat DRST $drst: equiv_induct (by-name state) PASS"; else echo "LAT $lat DRST $drst: equiv_induct FAIL ($(grep -c Unproven out/e_${lat}_${drst}.log) unproven lines)"; fi
  if cmp -s <(sed s/g_old/g_X/ out/old_${lat}_${drst}.v) <(sed s/g_new/g_X/ out/new_${lat}_${drst}.v); then echo "LAT $lat DRST $drst: synth netlists byte-IDENTICAL"; else echo "LAT $lat DRST $drst: synth netlists differ (text)"; fi
  cat > i_${lat}_${drst}.ys <<YS
read_verilog /n32/out/old_${lat}_${drst}.v /n32/out/new_${lat}_${drst}.v
proc; async2sync; opt_clean
miter -equiv -flatten -make_outputs g_old g_new miter
hierarchy -top miter
sat -verify -tempinduct -prove trigger 0 -seq 8 -maxsteps 24 -set-def-inputs miter
YS
  if yosys -q -s i_${lat}_${drst}.ys > out/i_${lat}_${drst}.log 2>&1; then echo "LAT $lat DRST $drst: miter tempinduct PASS"; else echo "LAT $lat DRST $drst: miter tempinduct FAIL"; fi
done; done
# negative control: 'bad' feeds {s2_err[0], s2_err[0]} (err bit 1 wrong on non-finite bypass) -> every check must FAIL
for lat in 6; do for drst in 0 1; do
  sed "s#old_${lat}_${drst}.v#bad_${lat}_${drst}.v#; s#g_old#g_bad#g" i_${lat}_${drst}.ys > mb.ys
  if yosys -q -s mb.ys > out/mb_${lat}_${drst}.log 2>&1; then echo "NEG LAT $lat DRST $drst: miter tempinduct PASSED (control BROKEN)"; else echo "NEG LAT $lat DRST $drst: miter tempinduct FAIL as expected"; fi
done; done
echo EQ_DONE
