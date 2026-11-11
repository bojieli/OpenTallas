#!/bin/bash
# TLOAD-ROMSTAGE plan events (DIE-QC-97 11-11) on the fixed lineage head aace4c2668fc
# (cand23d_fh_hc0bins_stmdq_ra_gr.json, sidecar 499a1c76d58d).  As run on epyc7:
#   bash run_event.sh SRC BASE_PLAN SIDECAR ROWC ROWA STM_A14 KITB OUT
# SRC = repo tree (tools/die_plan, tools/autopilot); KITB/<type>/{pins.json,landing_contract.json,rtl/*_bound.sv,
# geom/geom.tsv} = read-only copies of the newest wave attempt with a geometry dump (rowC: sle_stm_v2__cl7b3062fa a14,
# STM_A14: sle_stm_v3 a14, ROWA: sle_ctl__cl67434795).
# Form B: STRUCT core form (qc_struct_core.py: bin / pad-chain relay sites + per_bit stations, reach 350, kit knee 403)
#   on 8 stm types with a geometry dump, then lane fixed_cycles (qc_struct_ctl_lanes.py, incremental), plus one
#   per_bit station on sle_ctl__cl67434795 x_su_c_p2_o.  -> s10l.json
# Form A plan side: tlcap_plan.py (verilog_defines OT_QC_TLCAP + ROM-pin relay sites, all 11 stm types) -> ab.json
# Checks: collector_reattach.py (reach 405, sidecar), eq_record.py (schema.validate + lane latency = fixed_cycles).
set -euo pipefail
SRC=$1; B=$2; SC=$3; ROWC=$4; ROWA=$5; A14=$6; KB=$7; O=$8; H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"; cd "$O"
TD=$SRC/tools/die_plan
python3 -I $TD/qc_struct_core.py $SRC $KB/sle_stm_v2__cl7b3062fa $ROWC/geom/geom.tsv $B sle_stm_v2__cl7b3062fa b1.json b1_rep.json
python3 -E -s $TD/qc_struct_ctl_lanes.py $SRC $B b1.json sle_stm_v2__cl7b3062fa b1l.json b1l_rep.json
python3 -I $H/p2o_probe.py $SRC $ROWA/geom/geom.tsv $ROWA/gen/sle_ctl__cl67434795/pins.json $B sle_ctl__cl67434795 \
  x_su_c_p2_o u_pd11_x_fw_i probe_x_su_c_p2_o.json
python3 -I $H/add_out_station.py $SRC b1l.json sle_ctl__cl67434795 x_su_c_p2_o $ROWA/gen/sle_ctl__cl67434795/pins.json \
  probe_x_su_c_p2_o.json b2.json b2_rep.json
python3 -E -s $TD/qc_struct_ctl_lanes.py $SRC b1l.json b2.json sle_ctl__cl67434795 b2l.json b2l_rep.json
python3 -I $TD/qc_struct_core.py $SRC $A14/gen/sle_stm_v3 $A14/geom/geom.tsv b2l.json sle_stm_v3 b3.json b3_rep.json
python3 -E -s $TD/qc_struct_ctl_lanes.py $SRC b2l.json b3.json sle_stm_v3 b3l.json b3l_rep.json
prev=b3l.json; i=5
for t in sle_stm_v2__cl55be2264 slw_stm_v1__cl05fc43f7__cl2086fa2c slw_stm_v2__cl1ca9c415 \
         slw_stm_v1__cl05fc43f7__cl389df4e9 slw_stm_v3 slw_stm_v1__cle34a73c3; do
  python3 -I $TD/qc_struct_core.py $SRC $KB/$t $KB/$t/geom/geom.tsv $prev $t s$i.json s${i}_rep.json
  python3 -E -s $TD/qc_struct_ctl_lanes.py $SRC $prev s$i.json $t s${i}l.json s${i}l_rep.json
  prev=s${i}l.json; i=$((i+1))
done
python3 -I $H/tlcap_plan.py s10l.json ab.json ab_rep.json $SRC/physical/die_plan/qwen_compute/plan_of_record/macro_pins/ot_rom_4096x266_m8.json
for c in s10l ab; do
  python3 -E -s $TD/collector_reattach.py $B $c.json ${c}_cr.json ${c}_cr_rep.json --reach-um 405 --sidecar $SC sc_$c.json
  cmp $c.json ${c}_cr.json; cmp sc_$c.json $SC
  python3 -E -s $H/eq_record.py $SRC $B $c.json eq_$c.json ${c}_cr_rep.json
done
sha256sum s10l.json ab.json
