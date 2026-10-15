#!/usr/bin/env bash
set -euo pipefail
B=${1:?output directory required};mkdir -p "$B"
for m in 0 7 5; do
    iverilog -g2012 -s tb_svc_payload_done -Ptb_svc_payload_done.MUT=$m -o "$B/d$m" \
        rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svcio_job.sv \
        rtl/dsrom_sys/s81_ph/svc/test/tb_svc_payload_done.sv
    rc=0;vvp "$B/d$m" > "$B/d$m.log" 2>&1 || rc=$?
    if [ "$m" = 0 ]; then [ "$rc" = 0 ];grep -q 'verdict=PASS' "$B/d$m.log";else [ "$rc" != 0 ];grep -q 'EARLY_OR_LATE_DONE' "$B/d$m.log";fi
    cat "$B/d$m.log"
done
