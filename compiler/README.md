# OpenTallas compiler and executable fixture

This directory starts the `COMP-01` executable model-mapping path defined in
[`docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md`](../docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md).
It is deliberately separate from the analytical simulator in `src/opentallas`.

The first committed vertical slice is small but unbroken:

```text
strict semantic IR
  -> deterministic ROM image and tensor manifest
  -> fixed-width, CRC-protected microcode
  -> independent ROM-image reconstruction
  -> artifact-only software service engine
  -> independent reference and known-answer comparison
  -> exact semantic counter reconciliation
```

Its `int_exact_fixture_v1` numeric profile and tiny linear projection are unit-
test evidence. They are not a DeepSeek layer, an operator-complete accelerator,
an RTL implementation, hardware-cycle evidence, or performance validation. The
compiler fails on any other numeric profile or unsupported operation so this
fixture cannot be mistaken for model closure.

Compile and execute the fixture with:

```bash
python3 -m compiler.cli compile \
  --model testdata/compiler/linear_fixture/model.ir.json \
  --output /tmp/opentallas-linear-deployment

python3 -m runtime.service_engine \
  --deployment /tmp/opentallas-linear-deployment \
  --inputs testdata/compiler/linear_fixture/execution_input.json \
  --output /tmp/opentallas-linear-result.json
```

The service engine verifies every manifest hash before execution and never reads
the known-answer file. The independent reference evaluator consumes the source
IR and request, not compiler artifacts. Tests compare both paths with the
committed known answer.

Planned expansion follows the recovery plan: source/checkpoint locks, the full
semantic operator ledger, target numeric formats, complete payload ingestion,
physical placement, certified schedules, real full-dimension checkpoint slices,
and only then generated-artifact-driven RTL integration.
