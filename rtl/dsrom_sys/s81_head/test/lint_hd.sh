#!/usr/bin/env bash
# HD-CTL 10-21: Verilator 5.050 lint of the head-die controller-side masters.  cwd = repo root (or the synced src dir).
set -u; O=${1:?outdir}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
F=rtl/dsrom_sys/s81_head/test/hd_files.f; bad=0
for top in ot_s81hd_lane ot_s81hd_lep ot_s81hd_ctl; do
  $V --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-TIMESCALEMOD \
     -Wno-MULTIDRIVEN -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-GENUNNAMED -Wno-VARHIDDEN -Wno-BLKSEQ -Wno-SYNCASYNCNET \
     -DSYNTHESIS --top-module $top -f $F > $O/lint_$top.log 2>&1
  e=$(grep -c '^%Error' $O/lint_$top.log); w=$(grep -c '^%Warning' $O/lint_$top.log)
  echo "lint $top: errors $e warnings $w"; [ "$e" = 0 ] || { bad=1; grep -m8 '^%Error' $O/lint_$top.log; }
done
[ $bad = 0 ] && echo "HD_LINT PASS" || echo "HD_LINT FAIL"; exit $bad
