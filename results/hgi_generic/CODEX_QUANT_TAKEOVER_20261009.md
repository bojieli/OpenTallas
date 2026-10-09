# Codex quant takeover for Claude

Owner instruction: stop extensions/new builds/new routes; preserve live jobs. No proposed structural successor has been built.

## Exact source and worktree

- Worktree: `/home/ubuntu/wt/codex-hgi-quant`
- Branch: `codex/hgi-quant-decode-20261009`
- Exact completed implementation/evidence HEAD: `2a4b8e706305de2019a08510da1d3385de6d7fbe` (pushed, clean before this handoff-only commit).
- Functional core source: `b827340df`; actual route snapshot `7202d4ec4` has identical qualified RTL.
- Main merges and daemon deployment were not performed by this owner.

## Completed exact gates

`rtl/hbm_accel/generic/ot_hgi_quant_decode.sv` exposes normative unit4/op4 FP8 UE8M0, op5 FP4 UE8M0 and op6 FP4 E4M3. Existing DS margin core MR1/MLAT6 is unchanged, actual latency23, II1. E4 native8 plus15alignment edges equals23. Illegal report is registered1edge. Generic enable low uses legacy_fp4 unchanged.

Original DS `ot_hdc_fp4qdq` remains byte-identical. Opt-in `ot_hgi_fp4qdq` fixes the released SATFINITE scale clamp to448 for amax>=2688. All184 released golden beats pass, including zeros/subnormal/maxfinite/2592tie and2688clamp boundary +/-ulp, two independent block16 halves. Compiled scale-off-one-power mutant fails atoutput7. Original saturation and mixed-mode collision failures are preserved.

Binding review-0637 resolves E4M3 legal set to{16}, no selector. Exhaustive256parameter gate accepts16 and rejects255others; finalnative/default/nonfinite campaign5410outputs/300decodefaults passes. Compiled wrong-block-accept mutant fails DECODE mismatch and format mutant fails atoutput910, bothrc134.

Evidence: `results/hgi_generic/quant_decode_20261009/`, `quant_v1_blockset_20261009/`, and immutable golden sets `cf_qdq_d61ca29fc/` (148beats), `cf_qdq_891b4b555/` (184beats). Remote compiled hashes match owner source. Golden helper `tools/hgi_qdq_vectors.py` pins released DS golden functions. No complete record execution claim follows from the header/core bench.

## Physical jobs preserved

- `hgi_quant_pd50-7202d4ec4-tc-cx`: EPYC2, `/srv/opentallas-data/claude/closure-loop/hgi_quant_pd50-7202d4ec4-tc-cx`; **EARLY_FAIL_HOLD terminal at07:02:34PT**, olddriver4104924 absent; no matching run-path processes and no liveE2container mounts for thisjob. Physicalchild preserved early_fail.json/fullCTSlog/hash/canonicalstate. Actual FFhold-386.108ps persistedthrough7800iterations/10381buffers; no reroute scheduled.
- `hgi_quant_pd55-7202d4ec4-tc-cx`: EPYC4, `/srv/opentallas-scratch2/scratch/claude/closure-loop/hgi_quant_pd55-7202d4ec4-tc-cx`; fullroute driver2124280 freshly verified live at14:08UTC; actualcontainer11aea74832cd6d75e2420adb6d2a25cb5a9aba0ad6cacd0445e0be372fdcd569 `/competent_zhukovsky`, containerPID2159155. Same-386.108ps inputhold endpoint observed at~540iterations, still progressing; no finalverdict.
- All four daemon exact/mutant entries accepted for each job.
- These are real HM10/HM20 repair variants. Declared densities .50/.55 were ignored by PLACE_DENSITY_LB_ADDON (actual.079, same calibration placement); do not claim distinct density variants. PD55 pending-only fullroute HM20 was changed before launch under fleetlock; actualemitted HOLD_SLACK_MARGIN20 verified. No progressing job was restarted.
- Runtime770ps, signoff833.333ps, setup60/hold25 unchanged. WC/BC names preserved, WC reads TT library data, BC reads FF. Actual configuration receipts prove this.
- Calibration memory estimate10 was replaced12 after actualcgroup9.98GiB; route48 is conservative sibling-derived estimate (actual old quant DRT17.78GiB, newcells/outline growth), bench2 based on observed wholePG0.956GiB. None are hard caps.
- Submit pin lint passes; actualpeak10.24b/um<12gate (above6target). Remote boundary passes input->reg10/reg->out2/no combin input->output. Source-bound cache imported to prevent local admission synthesis.
- FF synthesis sizing18541um2/122121cells/1672IO/0macros; provisional1800x600slot is not optimized/adopted die area.

## Current failures and next steps for Claude

PD50 CTS setup repair was observed stalled near-565.340ps on internal E4 `bq.s5_c[15][2]/D`, 2771setupendpoints. Later FF hold repair was near-386.108ps on input `aq.s0_x[28]/D`, with4000+buffers. These are intermediate measurements, not final routed verdicts. FF measured boundary reference valid_pipe[0]/CLK max815.626/min787.549ps; don't assume wrong IO reference without auditing terminal objects.

The structural idea is an exact balanced population count of seven parallel threshold predicates, replacing the actual serial `cc=cc+1` chain at E4 S5. Earlier priority-encoder suggestion was withdrawn. Additional real E4 pipeline stages could consume1-3 of the15existing alignment pads, preserving common23edge latency and nativeDS default. This is a prepared idea only, no successor RTL/build/route.

GH-b: Claude hbm-sim checks whether missing SATFINITE is reachable on the shipped DS token path; if reachable Claude coordinates a shared-core fix. Preserve current qualified opt-in fork/routes as evidence.

Adoption still requires real finite VM producer/count/drain/writeACK consumer proof and selected generic VM endpoint. Integration worker `/root/generic_die_integration/quant_vm_transport` owns separate adapter (`ot_hgi_quant_vm_transport`, branch `codex/hgi-quant-vm-transport-20261010`); this owner supplied exact block/port/23edge/credit constraints and golden fixtures. VM publishes each BF16 as FP32 word `{bf16,16'b0}` (four8word result sectors); native y is512bits, not a packed-halfword VM store. Header validity must be checked before counted beat issue to avoid waiting for a nonexistent vo on invalid operations.

## Children

- Physical owner `/root/generic_quant_decode/quant_physical_pair`, WT `/home/ubuntu/wt/codex-hgi-quant-physical`, branch `codex/hgi-quant-physical-20261009`: collecting final clean pushed takeover receipts, preserves livejobs.
- Golden owner `/root/generic_quant_decode/qdq_conformance_vectors`, WT `/home/ubuntu/wt/codex-hgi-qdq-vectors`, branch `codex/hgi-qdq-vectors-20261009`, last pushedHEAD `736174ce8`: completed, no continuing golden jobs; final clean confirmation requested.

All source/evidence and READY/review coordination is already posted in `/home/ubuntu/claude-takeover-20261007/`.
