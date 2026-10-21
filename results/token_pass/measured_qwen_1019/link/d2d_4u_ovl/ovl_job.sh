#!/bin/bash
# TOKSIM-QW/LINK 10-19: 4u OVL D2D pair fullframe re-measure (real ot_qwen_d2d_static_end x2 OVL=1 + ot_qwen_d2d_ovl_seq x2 + LAT5 PHY model).
# RTL = qw-gen3 release link files (crc/slot link/llr/SRAM/PHY/cal_seq) + OVL overlay (ot_qwen_d2d_static.sv OVL form, ot_qwen_d2d_ovl_seq.sv, tb):
# OVL is NOT in the release RTL -> NEWEST.  Calendars compiled here by tools_S (gen3 tools + codex/sysface-ovl-1019 compiler deps; gen3's
# d2d_link_calendar.producer_txd lacks kv_codec, so the gen3 tools cannot compile any OVL frame).  usage: ovl_job.sh CODECS...
set -u
cd "$(dirname "$0")"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VERILATOR --version
for c in "$@"; do
  for m in pass collide slot user; do
    mut=""; [ $m != pass ] && mut="--mut $m"
    ( cd tools_S && python3 -m qwen_static_schedule.mu_d2d_ovl --out ../cal_c$c/cal_$m --kv-codec $c --kv-prog $mut ) > cal_c${c}_$m.log 2>&1; echo "cal codec$c $m rc=$?"
  done
  ( JOBS=4 bash rtl/test/qwen_split/run_d2d_ovl_mu.sh out_c$c cal_c$c > run_c$c.out 2>&1; echo "rc=$?" >> run_c$c.out ) &
done
wait
for c in "$@"; do echo "==== codec$c"; cat run_c$c.out; done; echo OVL_JOB_DONE
