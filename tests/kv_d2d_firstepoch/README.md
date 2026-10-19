# Reproduce the private FIRST epoch component

From the repository root, stage the committed frozen original dependencies and current three private source files without running any simulation locally:

```bash
python3 tests/kv_d2d_firstepoch/prepare_component.py /tmp/firstepoch-input
```

The destination must be new. `staging_manifest.json` records every staged source SHA256. This staging includes the original SF calendar and STATUS receiver from `current_safe_fo.sv`; no installed/generated parent source is substituted.

Measure fleet headroom with `/home/ubuntu/bin/ot-run --status`, copy the small input directory to a new fleet scratch directory, then execute the runner through unpinned admission. For example, after choosing an available scratch location and copying the staged files there:

```bash
/home/ubuntu/bin/ot-run --mem 8 --threads 2 --disk 2 \
  --dir /srv/opentallas-scratch/claude/YOUR_FRESH_LANE/input \
  -- bash run_component.sh
```

Do not pipe a tar archive into ot-run: its SSH/admission probes consume stdin. Stage files separately with scp/rsync first. Use the actual selected host's scratch path; the example is not a host pin. Do not overwrite a historical run directory.

The runner compiles Icarus and Verilator binaries, records tool versions and SHA256, and checks each application's return status. Four-state mode 12 runs in Icarus only. Extended binary mode 16 reaches all 36 layer starts and the next ordinary token. Mode 17 drives a second real epoch request during a running calendar and checks the resulting actual BC generation poison halts both calendars. Final expected counts are 16 Icarus cases and 16 Verilator cases, each `COMPONENT_RESULT ... errors=0` and rc=0. Preserve every failure and source identity.

For causal scratch controls, copy the staged input into separate fresh directories, copy `mutate_controls.py` or `mutate_output_mask.py` there, and run the corresponding mutation script before compiling with the same source list in `run_component.sh`. Run only the targeted Icarus case:

| Mutation script | Argument | Mode | Required application failure |
|---|---|---:|---|
| mutate_controls.py | epoch | 5 | negative sticky veto |
| mutate_controls.py | metadata | 0 | healthy pair receipt |
| mutate_controls.py | status | 14 | malformed receiver sticky fault |
| mutate_output_mask.py | none | 13 | both counter branches unchanged |

These mutated cases must return nonzero for the named causal reason. An infrastructure compile error is not a caught mutation. Mutations affect only scratch verification copies. Preserve patches, complete logs, SHA256 and actual application statuses as in the committed `harness/mutants` and `harness/output_mask_mutant` records.

This fixture does not certify the actual endpoint payload producer or parent pipeline, native timing/reset/clock/PG/fanout, SRAM write integrity, or whole-token SU/MU performance. Those remain HOLD.
