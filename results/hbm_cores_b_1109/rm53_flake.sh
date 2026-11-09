R=/srv/opentallas-scratch3/claude/rm48
for t in tools/autopilot/test_kit_wave_source.py::RetryOutput::test_second_attempt_keeps_first_output_and_identity tools/die_plan/test_lec_async.py::test_physical_receipt_before_wait_and_later_scope_reuses_owner; do
 for side in repo base; do cd $R/$side; p=0; f=0; for i in 1 2 3 4 5; do if timeout 300 python3 -m pytest -q -p no:cacheprovider --no-header --tb=line -o addopts="" "$t" > /tmp/rm53_fl.$side.$i 2>&1; then p=$((p+1)); else f=$((f+1)); cp /tmp/rm53_fl.$side.$i /tmp/rm53_fl.last.$side; fi; done; echo "$side $(git rev-parse --short=11 HEAD) pass=$p fail=$f ${t##*::}"; [ -f /tmp/rm53_fl.last.$side ] && grep -vE "warnings|^$" /tmp/rm53_fl.last.$side | tail -4 | cut -c1-260; rm -f /tmp/rm53_fl.last.$side; done
done
