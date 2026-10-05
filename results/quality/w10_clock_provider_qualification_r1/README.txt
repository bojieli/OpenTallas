Fail-closed qualification companion; bf097 pinned originals remain unchanged

The historical bf097 eligibility helper could return physicalqualifiedTrue for
six caller QUALIFIED_CONNECTED_HARDWARE labels, model values1, readyTrue and a
synthetic_fixture waveform. Its committed source-bound build stayed false, but
the helper must not be used as a future physical qualification entry point.
Parent independently archives the counterexample; this companion contains the
exact regression fixture without duplicating or rewriting that failed evidence.

Use tools/w10_clock_provider_qualification.py eligibility/build instead.
candidate_metadata_complete reports required labels/fields present only.
All six events remain unqualified and all nine model fields remain unvalidated
without actual validators, even when every caller label/field is populated.
No provider or measured waveform evidence schema is currently supported.
Missing, malformed, schema-less and forged schema/hash/PASS metadata are rejected.
There is no implemented source-bound measured validator, so physical qualified
is alwaysFalse, credited root-stop cycles always0 and power reduction alwaysNull.
Host quiet/RT_SKIP or standalonePG PASS cannot override this result.

Original tools/w10_clock_provider_join.py, its tests, join evidence, original
provider requirements4ad, runtime76ffc and clockcontract850 stay byte-identical.
The companion loads immutable bf097 join and4ad requirement objects and binds
their hashes. No latency, waveform, hardware or new physical evidence invented.

Tests: exact parent all-labels-complete/synthetic-wave counterexample; forged
provider/wave schema/hash; current incomplete providers; missing model and
duplicate event records; malformed evidence; immutable join/no-hardware credit.

Reproduce:
  python3 tools/w10_clock_provider_qualification.py --out /home/ubuntu/w10-qualification.json
  cmp /home/ubuntu/w10-qualification.json results/quality/w10_clock_provider_qualification_r1/qualification.json
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_w10_clock_provider_qualification.py

Actual source/measured waveform validators, connected completion/prewake/state
retention, priced ports/fanout/CDC, contextual SS/FF, spatial PG/clock fit and
actual rail/RC/energy/IR are still required. No jobs or leases launched.
