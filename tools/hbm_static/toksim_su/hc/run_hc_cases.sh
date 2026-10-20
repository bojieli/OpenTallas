#!/bin/bash
# TOKSIM-HBM-su fork B (10-19): measured HC record spans on the CURRENT d4g GEN2e3 HC masters (bundle = git archive of
# claude/hd4g-gen2e3-1019; run from the bundle root on a fleet host, Verilator 5.050).
#   ring_die   HC.HC_MIX P1 production (K 20,480, 24 rows, sigmoid + Sinkhorn 20) on root + 4 x qeng (qcen + 8 ring banks):
#              die config HC_CPR=1 (root QCHX 11, hub CHX 11), HC_DRLY=2 / HC_XRLY=0 (GEN2d closed ring, bankq0 DRLY 2,
#              root QDRLY 2) -> RAW0 178.  HC_MIX_CYCLES = last result edge - programme base TB.
#   ring_hh9   anchor HH-9: HC_CPR=1, DRLY 1 (RAW0 176).        ring_mut1  die config MUT 1 (must FAIL: golden check alive)
#   qclient    ot_hbm_hc_q_static (die hc_<q> LG client) with lg pair leaves + 18/15 bank term: residual read -> x_wave
#              edges and result store (iverilog, MUT 0 PASS / MUT 3 FAIL).
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
echo "$(date -Is) host=$(hostname) bundle=$(cat BUNDLE_COMMIT) stage=$ST verilator=$(verilator --version)" > $O/head_$ST.txt
case $ST in
 ring_die)  HC_CPR=1 HC_XDEF="+define+HC_DRLY=2 +define+HC_XRLY=0" bash rtl/test/run_hbm_hc_eng4_ring.sh $O/ring_die 0 > $O/ring_die.out 2>&1 ;;
 ring_mut1) HC_CPR=1 HC_XDEF="+define+HC_DRLY=2 +define+HC_XRLY=0" bash rtl/test/run_hbm_hc_eng4_ring.sh $O/ring_mut1 1 > $O/ring_mut1.out 2>&1 ;;
 ring_hh9)  HC_CPR=1 bash rtl/test/run_hbm_hc_eng4_ring.sh $O/ring_hh9 0 > $O/ring_hh9.out 2>&1 ;;
 qclient_t) H=rtl/hbm_accel/generic/peers/static_hc; V=rtl/hbm_accel/generic/vm/static
            SRC="tb_hbm_hc_q_static_t.sv $H/ot_hbm_hc_q_static.sv $H/ot_hgi_hc_residual_vm_static.sv $H/ot_hgi_hc_result_vm_static.sv
             $H/ot_hgi_hc_gathered_mix_reader_static.sv $V/ot_vms_calendar_static.sv $V/ot_static_program_target.sv
             $V/ot_hbm_vm_lg_static_split_term.sv $V/ot_hbm_vm_lg_static_bank_term.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv
             rtl/hdc/ot_hdc_delay.sv rtl/test/full_sm_service/sram_models.sv rtl/lib/ot_rst_relay.sv $H/ot_hbm_hc_xw_rx_static.sv"
            mkdir -p $O/qt; iverilog -g2012 -P tb_hbm_hc_q_static.MUT=0 -o $O/qt/tb0.vvp $SRC && vvp -n $O/qt/tb0.vvp > $O/qclient_t.log 2>&1 ;;
 qclient)   for m in 0 3; do OUT=$O/q MUTS=$m bash rtl/hbm_accel/generic/peers/static_hc/run_hc_q_static.sh > $O/qclient_m$m.out 2>&1
              (cd $O/q && vvp -n tb$m.vvp > $O/qclient_m$m.vvp.log 2>&1); done ;;
esac
echo "$(date -Is) done rc=$?" >> $O/head_$ST.txt
