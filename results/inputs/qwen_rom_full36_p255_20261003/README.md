# Existing P255 full-36 inputs for the combined Qwen ROM model

This software handoff reuses Claude's completed local-GPU golden and existing
checkpoint images. It writes no image/history bytes and launches no model,
compiler or simulator. All baseline/source caches and live jobs remain unchanged.

The prepared EPYC directory is:

`/srv/opentallas-scratch/codex/qwen-full36-inputs-20261003/P255`

- `stages_E_L0_L35_head.txt`: 38 actual six-field stage lines, in order.
- `kv_history/L<n>_die<r>.bin`: 144 links to existing raw histories. The hook
  checked each source with `FrozenHistory.source()` and compared every existing
  raw file to its little-endian bitwords: 2,415,919,104 history bytes in total.
- `x_preload.hex`: link to `realmem-fulltoken/gold/P255/x_preload.hex`.
- `embedding_row.bin`: link to `realmem-fulltoken/runs/P255/E/w/embedding_row.bin`;
  exactly 4,102 bytes, token 6280, original BF16 scale and INT8 codes.
- `inputs.json`: current oracle/prep pins, image paths, expected image hashes,
  actual history hashes, compiled extent provenance, and per-stage references.

Decoder/head images are the existing `layer-parallel-sim/img256/L<n>-d<r>` and
`head-d<r>`. Their weight/CROM links must resolve to the same paths pinned by the
GPU oracle's prep manifest; program/descriptor files are separately hashed.
Weight hashes are inherited from that frozen manifest, rather than re-reading
all weight payloads. The runtime owner must retain its final payload hash check.
Embedding uses the existing `realmem/stages/E` on all four ranks.

The current full-36 oracle SHA256 is
`cb0d25ab3d441ba5551987ff3f5dcce857ea6dad4ea625db9201fa786ef1053e`.
`history_from_inputs(inputs)` binds this explicit oracle through the existing
`FrozenHistory` constructor. It does not extend `from_baseline()` coverage or
substitute the old three-layer oracle. The existing raw files are reused by link;
no export is required for this cache.

The compiled capacity binding is the owner's existing
`/tmp/dewey-qwen-combined-compiled-params-actual-r1-20261004.json`, including its
verified `Vdie__verFiles.dat` pin: TP4/G6144/SW64/NW18, HBM_LAYERS=36 and
MEM_WORDS=4,718,592 per stack, with real write ACK. This is the existing model's
extent, not a new compiled executable or runtime verdict. The input hook makes
no change to the first-three-layer combined runtime or its selected sources.

## Concrete gaps for the owning integrators

- E's frozen passing record pins oracle
  `8909da94ac64ce0e9a44bcd18654823e7e3e9c3dd0ca6a5c02576761542e0367`,
  which differs from the current full-36 manifest. Its source pins are retained
  as a source reference only; it is not accepted as a current-cache baseline.
- At inspection, L3/L5/L6/L9/L12/L26/L28 have stable source and simulator exit 0,
  but wrapper FAIL and 16,384 X-word mismatches each. Their original records are
  referenced by path/hash in `baseline_refusals.json`; Claude owns numerics and
  any source correction. Other per-stage results were pending in this snapshot.
- Parent has now integrated explicit head hooks (`d4ec0e89d`) and the first-run
  cached-input callable (`a8c42cda8`). The sole owner must use
  `qwen_rom_combined_head_launch.prepare_from_inputs()` rather than the legacy
  launcher main, which intentionally retains its prior-PASS guard.
- The remaining executable binding is Dewey's explicit future head link and
  selection book. An existing three-layer executable fails the head ABI/link
  identity check. Preserve that live flow. The initializer composition is also
  assigned to Dewey/Russell; this handoff does not relink or modify it.
- Parent's existing `tools/qwen_rom_combined_head_readback.py` checks all X/KV
  and four actual head result/xnorm outputs against this explicit GPU oracle,
  without requiring an earlier RTL PASS. The numerical failures above remain
  diagnostic history; they do not prevent preparation of the FIRST combined
  measurement and are never relabeled as passing baselines.

`launch_ready` and `fulltoken_rtl_pass` remain false. Existing caches contain all
requested images/history/head outputs; no missing image was replaced or created.
No combined rate, physical, SS/FF, speculation or optional-engine claim is made.

The reusable input-only command (always with a new output directory) is:

```sh
python3 tools/qwen_rom_full36_inputs.py \
  --cache /srv/opentallas-scratch/claude/realmem-fulltoken \
  --oracle-sha256 cb0d25ab3d441ba5551987ff3f5dcce857ea6dad4ea625db9201fa786ef1053e \
  --compiled-params /tmp/dewey-qwen-combined-compiled-params-actual-r1-20261004.json \
  --output NEW_HANDOFF_DIRECTORY
```

Five focused file-transport tests pass. The actual cache hook completed exit 0;
its earlier strict baseline-pin refusal is preserved without changing that pin.

## First-run consumer for Dewey

The new additive `tools/qwen_rom_combined_first_prepare.py` calls the existing
owner's `prepare_from_inputs()` directly and provides the existing checker
command. It never executes the runtime, links a host, generates inputs, or calls
legacy baseline preparation. With the actual future head selection and source
root available, the sole owner uses:

```sh
python3 tools/qwen_rom_combined_first_prepare.py \
  --selection ACTUAL_FUTURE_HEAD_SELECTION_JSON \
  --inputs /srv/opentallas-scratch/codex/qwen-full36-inputs-20261003/P255/inputs.json \
  --output FRESH_FULLTOKEN_OUTPUT \
  --source-root ACTUAL_SELECTED_SOURCE_ROOT
```

The returned command and `owner_commands.json` belong to the sole runtime owner.
After actual admitted execution, preserve `launch.json` layers 0..35, token,
position and command; write `terminal.json` with the real returncode and status
`runtime_exit_zero` only on exit 0 (`runtime_failed` otherwise). Run the returned
existing checker command against `command[3]`, the actual output directory. Do
not synthesize a passing baseline or golden head output.

The cached receipt's `launch_ready=false` and diagnostic gaps describe the
input-only inspection, not a prior-PASS requirement. The new owner callable
checks actual images/history/extent/linked-head identity to authorize the FIRST
measurement. Two new focused caller tests pass; no repeated head/source proof
or baseline campaign was run. Actual prepare awaits the genuine head selection.
