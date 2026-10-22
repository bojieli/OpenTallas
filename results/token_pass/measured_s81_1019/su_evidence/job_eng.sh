#!/usr/bin/env bash
# TOKSIM-S81/SU: slice_eng bench on release 19bf4121e; bench source list adapted (env SLICE_SRCS += cap_tr/cap_rt + ot_hdc_delay_rf, split leaves of ot_s81sl_cap)
S=/srv/opentallas-scratch/claude/toksim-s81-su; W=$S/src_eng; rm -rf $W; mkdir -p $W && tar xf $S/src_slice.tar -C $W || exit 1
O=$S/out_eng; rm -rf $O; mkdir -p $O; cd $W || exit 1
export J=8 SLICE_SRCS="rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv rtl/hdc/ot_hdc_delay_rf.sv"
echo "HOST $(hostname) start $(date)"
bash tools/s81_slice/slice_eng_bench.sh $O/slice_eng 0 3 > $O/slice_eng.txt 2>&1; echo "EXIT $?" >> $O/slice_eng.txt
cat $O/slice_eng.txt; grep -h -E "cyc|ENG|PASS|FAIL" $O/slice_eng/*.log 2>/dev/null | head -40
