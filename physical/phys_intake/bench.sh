#!/bin/bash
# phys-intake 2026-10-09: exact bench + negative mutant for the elements taken into physical work by stream phys-intake
# (owner: every "implementation recorded (no physical job)" element gets a closure-loop job; no closure counts without
# its exact bench + a mutant that FAILS, bound in the job).  Run from the source snapshot root (the loop's {SRC} cwd).
#   bench.sh <element> pos|neg <workdir>
# pos prints PHYSINTAKE_<element>_PASS (rc 0) only when the committed exact bench passes on THIS source;
# neg builds an RTL (or committed stimulus) mutant and prints PHYSINTAKE_<element>_NEG_FAIL (rc 1) when the bench
# rejects it.  Every case writes its own workdir (bench stages run in parallel).
set -u
E=$1; M=$2; W=$3; mkdir -p "$W"; W=$(cd "$W" && pwd); R=$(pwd)
ok()  { echo "PHYSINTAKE_${E}_PASS"; exit 0; }
bad() { echo "PHYSINTAKE_${E}_NEG_FAIL"; exit 1; }
nok() { echo "PHYSINTAKE_${E}_BENCH_ERROR: $*"; exit 2; }   # positive failed / mutant escaped: neither verdict regex
ivl() { local top=$1 out=$2; shift 2; iverilog -g2012 -I rtl/common -s $top -o "$out" "$@" > "$out.build.log" 2>&1 || { cat "$out.build.log"; nok "iverilog build $top"; }; }
mutate() { local src=$1 dst=$2 from=$3 to=$4; grep -qF -- "$from" "$src" || nok "mutant needle missing in $src"; python3 - "$src" "$dst" "$from" "$to" <<'PY'
import sys; s=open(sys.argv[1]).read(); open(sys.argv[2],'w').write(s.replace(sys.argv[3],sys.argv[4],1))
PY
}
case $E in
s81_host_dispatch)
  D=rtl/dsrom_sys/s81_ingest/ot_s81_host_dispatch.sv; T=rtl/test/s81_native_ingest/tb_s81_host_dispatch.sv
  if [ $M = pos ]; then ivl tb_s81_host_dispatch $W/p.vvp $D $T; vvp $W/p.vvp | tee $W/p.log; grep -q '^S81_HOST_DISPATCH PASS' $W/p.log && ok; nok positive
  else mutate $D $W/mut.sv "((i_d[65:64]==3)?3'b100:3'b010)" "((i_d[65:64]==3)?3'b010:3'b100)"   # marker class swapped
    ivl tb_s81_host_dispatch $W/n.vvp $W/mut.sv $T; vvp $W/n.vvp | tee $W/n.log; grep -q 'wrong branch/payload' $W/n.log && bad; nok "mutant escaped"; fi ;;
hc_seed_join)
  D=rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv
  S="rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
  T=rtl/test/dsrom_hc_capture_20261009/tb_hc_seed_join.sv
  python3 tools/dsrom_hc_mean_capture_vectors.py --out $W/vectors > $W/vectors.log 2>&1 || nok vectors
  if [ $M = pos ]; then ivl tb_hc_seed_join $W/p.vvp $S $D $T; vvp $W/p.vvp +vectors=$W/vectors | tee $W/p.log
    grep -q '^PASS join120frames' $W/p.log && ok; nok positive
  else mutate $D $W/mut.sv "rframe<=rframe+1'b1;state<=READ;" "rframe<=rframe+2'd2;state<=READ;"   # skips a joined frame
    ivl tb_hc_seed_join $W/n.vvp $S $W/mut.sv $T; vvp $W/n.vvp +vectors=$W/vectors | tee $W/n.log
    grep -qE 'mismatch|FATAL|fatal' $W/n.log && ! grep -q '^PASS join120frames' $W/n.log && bad; nok "mutant escaped"; fi ;;
hbm_coll_vm_pub)
  L=rtl/hbm_accel/tu/link_retry_sram_20261008
  S="rtl/common/ot_secded.sv $L/ot_hbm_replay_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $L/ot_hbm_collective_vm_publication.sv $L/tb_hbm_collective_vm_publication.sv"
  if [ $M = pos ]; then ivl tb_hbm_collective_vm_publication $W/p.vvp $S; vvp $W/p.vvp | tee $W/p.log; grep -q '^PASS_ALL' $W/p.log && ok; nok positive
  else ivl tb_hbm_collective_vm_publication $W/n.vvp -DOT_HBM_PUBLICATION_MUT_QID $S; vvp $W/n.vvp | tee $W/n.log   # committed wrong-QID mutant
    grep -q 'quarter read ownership lost' $W/n.log && bad; nok "mutant escaped"; fi ;;
hbm_tu_retry_phy)
  L=rtl/hbm_accel/tu/link_retry_sram_20261008
  S="rtl/common/ot_secded.sv $L/ot_hbm_replay_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $L/ot_hbm_link_retry_sram.sv $L/ot_hbm_retry_pop_cdc.sv $L/ot_hbm_retry_phy_ingress.sv $L/ot_hbm_tu_retry_port.sv $L/ot_hbm_tu_retry_phy_port.sv $L/tb_hbm_tu_retry_phy_port.sv"
  if [ $M = pos ]; then ivl tb_hbm_tu_retry_phy_port $W/p.vvp $S; vvp $W/p.vvp | tee $W/p.log; grep -q '^PASS_ALL' $W/p.log && ! grep -qi fatal $W/p.log && ok; nok positive
  else S2=${S/$L\/ot_hbm_retry_phy_ingress.sv/$W\/mut.sv}; mutate $L/ot_hbm_retry_phy_ingress.sv $W/mut.sv "assign out_data=head[hp];" "assign out_data=head[hp+1'b1];"   # wrong landing slot
    ivl tb_hbm_tu_retry_phy_port $W/n.vvp $S2; vvp $W/n.vvp | tee $W/n.log; grep -qE 'FATAL|mismatch|order' $W/n.log && bad; nok "mutant escaped"; fi ;;
ta15_prod_clock)
  C=rtl/hbm_accel/control; T=tests/rtl/tb_hbm_production_clock_control.sv
  S="$C/ot_hbm_reset_seq.sv $C/ot_hbm_clock_reset_boundary.sv"
  if [ $M = pos ]; then ivl tb $W/p.vvp $S $C/ot_hbm_production_clock_control.sv $T; vvp $W/p.vvp | tee $W/p.log; grep -q '^PASS production composition' $W/p.log && ok; nok positive
  else mutate $C/ot_hbm_production_clock_control.sv $W/mut.sv "assign ready=ready_sync && released;" "assign ready=sequence_ready;"   # readiness from the AON intent, not the actual release
    ivl tb $W/n.vvp $S $W/mut.sv $T; vvp $W/n.vvp | tee $W/n.log; grep -qE 'FATAL|fatal' $W/n.log && bad; nok "mutant escaped"; fi ;;
hbm_mtp_emit_queue)   # committed gate: positive + constant-ready mutant; neg re-runs the gate and requires the mutant case to FAIL
  python3 tools/hbm_native_mtp_emit_gate.py --work $W/g --out $W/g.json > $W/g.log 2>&1; rc=$?
  if [ $M = pos ]; then [ $rc = 0 ] && grep -q '"verdict": "PASS"' $W/g.json && ok; cat $W/g.log; nok positive
  else python3 -c "import json,sys;c=json.load(open('$W/g.json'))['cases'];sys.exit(0 if c[1]['mutant']==1 and c[1]['returncode']!=0 else 1)" && bad; nok "mutant escaped"; fi ;;
hbm_ar_token_join)
  python3 tools/hbm_native_ar_token_join_gate.py --work $W/g --out $W/g.json > $W/g.log 2>&1; rc=$?
  if [ $M = pos ]; then [ $rc = 0 ] && grep -q '"verdict": "PASS"' $W/g.json && ok; tail -20 $W/g.log; nok positive
  else python3 -c "import json,sys;c=json.load(open('$W/g.json'))['cases'];m=[x for x in c if x['mutant']];sys.exit(0 if m and all(x['returncode']!=0 for x in m) else 1)" && bad; nok "mutant escaped"; fi ;;
hbm_token_loop)
  python3 tools/hbm_token_loop_bench.py --work $W/g --out $W/g.json > $W/g.log 2>&1; rc=$?
  if [ $M = pos ]; then [ $rc = 0 ] && grep -q '^PASS' $W/g.log && ok; tail -20 $W/g.log; nok positive
  else python3 -c "import json,sys;r=json.load(open('$W/g.json'));sys.exit(0 if r['negative_mut1_no_eos']['verdict']=='FAIL' else 1)" && bad; nok "mutant escaped"; fi ;;
*) nok "unknown element $E" ;;
esac
