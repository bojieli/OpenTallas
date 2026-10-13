#!/bin/bash
# el1013-idx-tiles gate (c): Verilator 5.050 lint, job flags of physical/ref_tile/idxw_b2/job.json (each leaf and the
# wrapper as top through an empty-port lint top), then a stricter pass (width / unused-style lint kept on) per top.
# usage: lint.sh ROOT > lint.log
R=$1; V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; D=$R/rtl/hbm_accel/generic/idx
T=$(mktemp -d); rc=0
SRC="$D/ot_hgi_idx_index_wt.sv $D/ot_hgi_idxw_lane.sv $D/ot_hgi_idxw_qcore.sv $D/ot_hgi_idxw_keep.sv $D/ot_hgi_idxw_beat.sv $D/ot_hgi_idxw_wr.sv"
$V --version
for top in ot_hgi_idxw_lane ot_hgi_idxw_qcore ot_hgi_idxw_keep ot_hgi_idxw_beat ot_hgi_idxw_wr ot_hgi_idx_index_wt; do
  printf '%s\n' "module ot_lint_top; $top u_top (); endmodule" > $T/ot_lint_top.sv
  $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top $T/ot_lint_top.sv $SRC > $T/a.log 2>&1; a=$?
  $V --lint-only -Wall -Wno-fatal -Wno-style -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-UNUSEDGENVAR -Wno-TIMESCALEMOD -DSYNTHESIS --top-module $top $SRC > $T/b.log 2>&1; b=$?
  echo "$top job_flags rc=$a errors=$(grep -c '^%Error' $T/a.log) warnings=$(grep -c '^%Warning' $T/a.log) | strict rc=$b errors=$(grep -c '^%Error' $T/b.log) warnings=$(grep -c '^%Warning' $T/b.log)"
  grep -hE '^%(Error|Warning)' $T/a.log $T/b.log | sed "s#$R/##" | cut -c1-200 | sort | uniq -c | head -20
  [ $a = 0 ] && [ $b = 0 ] && ! grep -q '^%Error' $T/a.log $T/b.log || rc=1
done
printf '%s\n' 'module ot_lint_top; ot_hgi_idx_unit #(.IXW(2)) u_top (); endmodule' > $T/ot_lint_top.sv
echo "unit IXW=2 elaboration (job flags): $($V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -Wno-PINMISSING -DSYNTHESIS -I$R/rtl/hbm_accel/generic --top-module ot_lint_top $T/ot_lint_top.sv $D/ot_hgi_idx_unit.sv $D/ot_hgi_idx_index_w.sv $D/ot_hgi_idx_index.sv $D/ot_hgi_idx_merge.sv $D/ot_hgi_idx_owned.sv $D/ot_hgi_idx_iks_issue.sv $SRC 2>&1 | grep -c '^%Error') errors"
rm -rf $T; [ $rc = 0 ] && echo lint-ok || echo lint-FAIL
