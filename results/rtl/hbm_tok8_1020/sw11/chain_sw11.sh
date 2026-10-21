#!/usr/bin/env bash
# HBM-TOK8 10-20 23:35: TOK.HDS.VEH.1 / TOK.HQ.LAYER on the CURRENT GEN2e4 die: SW slice of r11 planA pb5b/die.v
# (cut_slice --with-relays: the die's relay stations on every input chain are inside the slice), bundle @922d803a2,
# Verilator 5.050 hierarchical build, then replays (v0 zero init): DS L0/L2/L14 re-emitted by main layer_images
# (rec23-repaired SU, native 10/7 returns = die params) + VM-sign mutant witness; Qwen L0/chain cqw replays.
R=/srv/opentallas-scratch/claude/hbm-tok8-1020/sw11; L=/home/ubuntu/scratch/hbm-tok8/log
/home/ubuntu/bin/ot-run --mem 480 --threads 48 --disk 300 --dir $R -- env SRC=$R OUT=$R/out JOBS=48 BUILD_ONLY=1 bash run_slice_vehicle.sh > $L/build.log 2>&1
echo "$(date) BUILD_RC=$?" >> $L/summary.log
H=$(grep -o 'RAN on [a-z0-9-]*' $L/build.log | tail -1 | awk '{print $3}')
echo "$(date) host=$H" >> $L/summary.log
[ -n "$H" ] && timeout 120 ssh $H "test -x $R/out/obj/Vtb_hbm_slice" || { echo "$(date) NO_BINARY" >> $L/summary.log; exit 3; }
for N in ds_l0_e4 ds_l0_e4_mut_vm ds_l2_e4 ds_l14_e4 qw_l0_r0_p0 qw_l0_r0_p1 qw_l0_r5_p0 qw_l0_r5_p1 qw_chain_r0_p1 qw_chain_r5_p1; do
  ( /home/ubuntu/bin/ot-run --mem 64 --threads 1 --dir $R/out/obj -- bash -c "cd $R && mkdir -p out_$N && /usr/bin/time -v -o out_$N/run.time out/obj/Vtb_hbm_slice +verilator+rand+reset+0 +REPLAY=slice/replay/$N > out_$N/run.log 2>&1; echo RUN_RC=\$?; python3 check_slice_run.py --replay slice/replay/$N --run-log out_$N/run.log --out out_$N/acceptance.json; grep -m1 -E '^SLICE_(PASS|FAIL)' out_$N/run.log; grep -c SLICE_CHECK_FAIL out_$N/run.log" > $L/rpl_$N.log 2>&1
    echo "$(date) $N rc=$? $(grep -E 'RUN_RC|^SLICE_' $L/rpl_$N.log | tr '\n' ' ') fails=$(tail -1 $L/rpl_$N.log)" >> $L/summary.log ) &
  sleep 5
done
wait; echo "$(date) ALL_DONE" >> $L/summary.log
