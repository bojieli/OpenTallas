#!/usr/bin/env bash
# PG-ACTIVITY-KVHBM HBM collect (run on intel2 after hbm/sim finished with HGI_SM_E2E PASS):
#  1) per-bit toggle rates of the real SM g_sm[0].u_sm  2) copy act to intel1  3) measured report_power on both
#  hnx_rp3lp3h halves (3_place.odb) + BDC 4_cts  4) print totals.  Then fill hbm_power_meas.json / make_hbm_map.py.
set -eu
H=/srv/opentallas-scratch2/claude/pg-act-kvhbm-1027/hbm; T=/srv/opentallas-scratch2/claude/wt/pg-act-kvhbm-1027/tools/pg_activity
grep -a -E "HGI_SM_E2E (PASS|FAIL)" $H/sim/run.log
mkdir -p $H/act
python3 $T/vcd_activity.py $H/sim/sm.vcd $H/act --clk 'tb_hgi_sm_e2e.g_sm[0].u_sm.clk' --root 'SM=tb_hgi_sm_e2e.g_sm[0].u_sm' | tee $H/act/act.log
I=/srv/opentallas-scratch2/claude/pg-act-kvhbm-1027-hbm
scp -q -o ControlPath=none $H/act/act_SM.txt intel1:$I/act_SM.txt
ssh -o ControlPath=none intel1 "cd $I && \
 for h in s_33365650555c n_1938f3904f84; do t=\${h%%_*}; K=/srv/opentallas-scratch2/claude/codex-hbm/sm_r1/hnx_rp3lp3h_\${h}-tc; B=run/results/asap7/hbc_hnx_rp3lp3h_\${t}/base; \
   ./pg_activity/run_core_power.sh \$K \$B/3_place.odb \$B/3_place.sdc act_SM.txt out rp3_\${t}_meas 1 40 & done; \
 K=/srv/opentallas-scratch2/claude/path-hbm-sm/kits/ot_hbm_accel_smh_bdc_34c62882e5f9; B=run/results/asap7/hbc_ot_hbm_accel_smh_bdc/base; \
 ./pg_activity/run_core_power.sh \$K \$B/4_cts.odb \$B/4_cts.sdc act_SM.txt out bdc_cts_meas 1 16 & wait"
