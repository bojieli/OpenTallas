#!/usr/bin/env bash
# HBM-TOK8: after chain_sw11.sh reports the build host, run the Qwen replays re-emitted on main (qwen_layer_images,
# resident_edges 7111 = the R6 fix) against the r11 SW slice (+CYCLES from split_replay parts).
R=/srv/opentallas-scratch/claude/hbm-tok8-1020/sw11; L=/home/ubuntu/scratch/hbm-tok8/log
until grep -q -E "host=|NO_BINARY" $L/summary.log 2>/dev/null; do sleep 300; done
grep -q NO_BINARY $L/summary.log && exit 3
for x in qw_l0_r0_e4:34112 qw_l0_r5_e4:34112 qw_chain_r0_e4_p0:45218 qw_chain_r0_e4_p1:67087 qw_chain_r5_e4_p0:45218 qw_chain_r5_e4_p1:67087; do N=${x%%:*}; C=${x##*:}
  ( /home/ubuntu/bin/ot-run --mem 64 --threads 1 --dir $R/out/obj -- bash -c "cd $R && mkdir -p out_$N && /usr/bin/time -v -o out_$N/run.time out/obj/Vtb_hbm_slice +verilator+rand+reset+0 +REPLAY=slice/replay/$N +CYCLES=$C > out_$N/run.log 2>&1; echo RUN_RC=\$?; python3 check_slice_run.py --replay slice/replay/$N --run-log out_$N/run.log --out out_$N/acceptance.json; grep -m1 -E '^SLICE_(PASS|FAIL)' out_$N/run.log; grep -c SLICE_CHECK_FAIL out_$N/run.log" > $L/rpl_$N.log 2>&1
    echo "$(date) $N rc=$? $(grep -E 'RUN_RC|^SLICE_' $L/rpl_$N.log | tr '\n' ' ') fails=$(tail -1 $L/rpl_$N.log)" >> $L/summary.log ) &
  sleep 5
done
wait; echo "$(date) QE4_DONE" >> $L/summary.log
