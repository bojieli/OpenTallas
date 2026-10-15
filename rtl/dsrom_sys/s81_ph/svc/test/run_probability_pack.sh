#!/usr/bin/env bash
# Run on a fleet host through ot-run; from repository root.
set -euo pipefail
B=${1:?output directory required}
mkdir -p "$B"
S=rtl/dsrom_sys/s81_ph/svc
for top in probability_pack probability_frame; do
for m in 0 1 2; do
    iverilog -g2012 -s tb_svc_${top} -Ptb_svc_${top}.MUT=$m -o "$B/${top}_m$m" \
        "$S/ot_s81_svc_probability_pack.sv" "$S/ot_s81_svc_probability_frame.sv" "$S/test/tb_svc_${top}.sv"
    rc=0
    vvp "$B/${top}_m$m" > "$B/${top}_m$m.log" 2>&1 || rc=$?
    if [ "$m" = 0 ]; then
        [ "$rc" = 0 ]; grep -q 'verdict=PASS' "$B/${top}_m$m.log"
    else
        [ "$rc" != 0 ]; grep -q 'verdict=FAIL' "$B/${top}_m$m.log"
    fi
    cat "$B/${top}_m$m.log"
done
done
