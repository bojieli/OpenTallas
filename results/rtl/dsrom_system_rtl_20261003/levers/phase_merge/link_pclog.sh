#!/bin/bash
# Link the ORIGINAL w17 L0 die runtime host driver (source 4e38326d6, rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp)
# against the ORIGINAL r4 compiled Verilator archives (no RTL recompile): same command as the r4 run's link minus -DL0DIAG.
set -e
E=/srv/opentallas-scratch/claude/dsrom-system/levers/pm
B=$E/r4build; V=$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include; S=$E/src
g++ -std=c++20 -O2 -pthread -DROM_PHW=6 -DCL_PW_BITS=547 -I$V -I$V/vltstd -I$B/attn -I$B/attn/Vot_hdc_qadd -I$B/attn/Vot_hdc_v41x_attn_merge_6 -I$B/attn/Vot_hdc_v41x_attn_staging_3 -I$B/attn/Vot_hdc_v41x_attn_tile_e -I$B/die0 -I$B/die1 -I$B/die2 -I$B/die3 -I$B/pb -I$B/pq -I$B/retn -I$B/root -I$S/qwen_runtime -I$S/v41_runtime -DPM_PCLOG=1 $E/pm_die_rt.cpp -Wl,--start-group $B/die0/Vdie0__ALL.a $B/die1/Vdie1__ALL.a $B/die2/Vdie2__ALL.a $B/die3/Vdie3__ALL.a $B/pq/Vpq__ALL.a $B/pb/Vpb__ALL.a $B/retn/Vretn__ALL.a $B/root/Vroot__ALL.a $B/attn/Vattn__ALL.a $B/attn/Vot_hdc_qadd/libot_hdc_qadd.a $B/attn/Vot_hdc_v41x_attn_merge_6/libot_hdc_v41x_attn_merge_6.a $B/attn/Vot_hdc_v41x_attn_staging_3/libot_hdc_v41x_attn_staging_3.a $B/attn/Vot_hdc_v41x_attn_tile_e/libot_hdc_v41x_attn_tile_e.a -Wl,--end-group $V/verilated.cpp $V/verilated_threads.cpp $V/verilated_dpi.cpp -o $E/v41_die_rt_pclog
sha256sum $E/v41_die_rt -DPM_PCLOG=1 $E/pm_die_rt.cpp
