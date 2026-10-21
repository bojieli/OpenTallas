#!/usr/bin/env bash
# Existing original STA/DCC/classification programs over the fresh saved-case GRT output.
set -uo pipefail
: "${BASELINE_CASE:?immutable original case}" "${TAIL_OUT:?completed fresh physical tail}"
if ! grep -q '^HEAD_PHYSICAL_TAIL_PASS_DIAGNOSTIC' "$TAIL_OUT/resume_tail.log"; then
 echo 'Refuse STA: restored physical tail has not passed unchanged post-GRT checks' >&2; exit 2
fi
if test -d "$TAIL_OUT/sta"; then echo 'Refuse existing STA output' >&2;exit 2;fi
mkdir -p "$TAIL_OUT/sta"
sha256sum "$BASELINE_CASE/sta.sh" "$BASELINE_CASE/sta_tt.tcl" "$BASELINE_CASE/sta_ff.tcl" \
 "$BASELINE_CASE/sta_ss.tcl" "$BASELINE_CASE/landing.sdc" "$BASELINE_CASE/pairs.json" \
 "$BASELINE_CASE/case.json" "$BASELINE_CASE/classify.py" "$BASELINE_CASE/dcc/tools/die_clock_check.py" \
 "$BASELINE_CASE/dcc/tools/die_clock_check.tcl" "$TAIL_OUT/out/grt.odb" > "$TAIL_OUT/sta/inputs.sha256" || exit 2
cp "$BASELINE_CASE/case.json" "$TAIL_OUT/case.json"
rc=0
for c in tt ff ss; do
 docker run --rm --cpus="${CPUS:-8}" --memory="${MEMG:-64}g" --memory-swap="${MEMG:-64}g" \
  -v "$BASELINE_CASE:/work:ro" -v "$TAIL_OUT/out:/work/out:ro" -v "$TAIL_OUT/sta:/work/sta" \
  openroad/orfs:asap7lock bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads ${CPUS:-8} -no_init -exit /work/sta_$c.tcl > /work/sta/sta_$c.log 2>&1; s=\$?; chmod -R a+rwX /work/sta; exit \$s"
 s=$?;echo "$s" > "$TAIL_OUT/sta/sta_$c.exit"
 if test "$s" -ne 0 || ! grep -q '^OT_STA_DONE' "$TAIL_OUT/sta/sta_$c.log"; then rc=1;continue;fi
 python3 "$BASELINE_CASE/dcc/tools/die_clock_check.py" report "$TAIL_OUT/sta/die_clock_dump_$c.tsv" \
  --out "$TAIL_OUT/sta/die_clock_check_$c.json" --pairs "$BASELINE_CASE/pairs.json" \
  > "$TAIL_OUT/sta/die_clock_check_$c.log" 2>&1
 s=$?;echo "$s" > "$TAIL_OUT/sta/die_clock_check_$c.exit";test "$s" -eq 0 || rc=1
done
python3 "$BASELINE_CASE/classify.py" "$TAIL_OUT" tt ff ss > "$TAIL_OUT/sta/classes.txt" 2>&1 || rc=1
echo "$rc" > "$TAIL_OUT/sta/run.exit"
echo "HEAD_EXISTING_STA_EXECUTION rc=$rc scope=diagnostic_original_source_views_not_release_qualification"
exit "$rc"
