#!/bin/bash
# QW-SYSFACE3 fleet matrix (isolated source copy via ot-run; not a gate):
#  1 SAFE3 functional graphs (cold3/legacy3) + plain graphs (cold/legacy, SAFE3=0 = the original source behaviour)
#  2 generic depth census (SAFE checklist 4, limit 20 generic levels)
#  3 useful-cone kept copies + explicit paid wrapper (per-KIND kept modules), graph proof, re-read/roundtrip proofs
#  4 benches: SAFE3 source vs candidate (miter) AND ORIGINAL source vs SAFE3 candidate (cold + legacy traces), reset
#  5 leaf equivalence proofs + causal mutants, emitted-netlist mutants (copy_d / reset_short / gate_input)
set -u
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
C=tools/qwen_split/sysface_control_safe
st(){ echo "STEP $* $(date +%T)"; }
fail(){ echo "SAFE3_MATRIX_FAIL $*"; exit 1; }
for p in cold3 legacy3 cold legacy; do
 st graph $p
 python3 $C/build_profile.py --profile $p --out $p || fail profile $p
 yosys -Q -s $p/synth.ys > $p/synth.log 2>&1 || fail synth $p
done
for p in cold3 legacy3; do
 python3 $C/depth_census.py $p/original.json --out $p/depth_census.json || fail depth $p
 st generate $p
 /usr/bin/time -v python3 -u $C/generate.py --graph $p/original.json --manifest $p/manifest.json --out $p/generated --useful-cones --physical-wrapper > $p/generate.log 2> $p/generate.time || fail generate $p
 python3 $C/check_graph.py $p/original.json $p/generated/graph.json $p/generated/receipt.json --out $p/proof.json || fail graph_proof $p
 python3 $C/audit_graph_transparent.py $p/generated/graph.json --out $p/abstract_transparent.json || fail abstract_fanout $p
 cat > $p/roundtrip.ys <<YS
read_verilog -sv $p/generated/parent.sv physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_bb.v
hierarchy -check -top qfd_sys_face_control_safe
synth -top qfd_sys_face_control_safe -flatten -noabc
write_json $p/roundtrip.json
stat
YS
 st roundtrip $p
 /usr/bin/time -v yosys -Q -s $p/roundtrip.ys > $p/roundtrip.log 2> $p/roundtrip.time || fail roundtrip $p
 python3 $C/check_emitted.py --top qfd_sys_face_control_safe__safe_core $p/generated/graph.json $p/roundtrip.json --source $p/generated/parent.sv --out $p/emitted_proof.json || fail emitted $p
 python3 $C/check_physical_wrapper.py $p/original.json $p/roundtrip.json $p/generated/receipt.json --out $p/wrapper_proof.json || fail wrapper $p
 python3 $C/build_miter.py --graph $p/original.json --manifest $p/manifest.json --receipt $p/generated/receipt.json --source rtl/qwen_split/qfd_sys_face.sv --out $p/miter || fail miter $p
 # ORIGINAL-source reference (SAFE3=0 graph names/params) against the SAFE3 candidate
 b=${p%3}; x=${p}x; mkdir -p $x; ln -sfn ../$p/generated $x/generated
 python3 - $p $b <<'PY' || fail oldref_receipt $p
import json,sys
p,b=sys.argv[1:3];r=json.load(open(p+'/generated/receipt.json'));r['manifest']=json.load(open(b+'/manifest.json'))
json.dump(r,open(p+'x/receipt_oldref.json','w'))
PY
 python3 $C/build_miter.py --graph $b/original.json --manifest $b/manifest.json --receipt $x/receipt_oldref.json --source rtl/qwen_split/qfd_sys_face.sv --out $x/miter || fail oldref_miter $p
done
st benches
SRAM_CAL=1 MUT=0 SAFE_DIR=cold3 bash rtl/test/qwen_split/run_sys_face_cold_safe.sh cold3/sim > cold3/sim_runner.log 2>&1 || fail bench_cold3
SRAM_CAL=1 MUT=0 SAFE_DIR=cold3x bash rtl/test/qwen_split/run_sys_face_cold_safe.sh cold3x/sim > cold3x/sim_runner.log 2>&1 || fail bench_cold3_oldref
SRAM_CAL=1 D2D_MU=1 SAFE_DIR=legacy3 bash rtl/test/qwen_split/run_sys_face_age_safe.sh legacy3/sim > legacy3/sim_runner.log 2>&1 || fail bench_legacy3
SRAM_CAL=1 D2D_MU=1 SAFE_DIR=legacy3x bash rtl/test/qwen_split/run_sys_face_age_safe.sh legacy3x/sim > legacy3x/sim_runner.log 2>&1 || fail bench_legacy3_oldref
P=cold3 bash $C/run_reset.sh > cold3/reset_runner.log 2>&1 || fail reset_cold3
grep -h "SYSFACE_SAFE_EQUIV checks\|SYS_FACE_COLD_PASS\|SYS_FACE_PASS\|SYSFACE_SAFE_RESET_PASS" cold3/sim/run.log cold3x/sim/run.log legacy3/sim/run.log legacy3x/sim/run.log cold3/reset_run.log
st leaf_equiv
bash $C/safe3_equiv.sh safe3_equiv > safe3_equiv.log 2>&1; cat safe3_equiv.log; grep -q SAFE3_EQUIV_ALL_PASS safe3_equiv.log || fail leaf_equiv
st mutants
for kind in copy_d reset_short gate_input; do
 python3 $C/make_mutant.py cold3 "$kind" || fail make_mutant $kind
 SRAM_CAL=1 MUT=0 SAFE_DIR="cold3_mut_$kind" bash rtl/test/qwen_split/run_sys_face_cold_safe.sh "cold3_mut_$kind/sim" > "cold3_mut_$kind/runner.log" 2>&1
 rc=$?
 test "$rc" != 0 || fail mutant_escaped $kind
 grep -E 'SYSFACE_SAFE_(EQUIV|RESET|COPY)_FAIL' "cold3_mut_$kind/sim/run.log" || fail mutant_no_witness $kind
done
echo SAFE3_MATRIX_PASS
