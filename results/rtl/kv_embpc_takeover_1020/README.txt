KV EMB/PC native qualification pickup, 2026-10-20. CANDIDATE NOT ADOPTED.

Current source: NATIVE32 and PIPE_JOIN default OFF. New component implementations are opt-in.
NATIVE32 cal: kept same-edge valid/counter/config groups, local bank reset, registered mux/scale controls via PIPE_JOIN.
NATIVE32 ctx: banked admission retirement with pending-owner forwarding; each state/data enable <=16 bits.
Steady throughput remains one beat per edge. CTX adds1 stream edge and join adds1: total2.
Regional reset cal and ctx release after6 edges in parallel, versus0 internal legacy; tile inherited pin capture
makes7 versus1. Exact candidate_calendar_costs.json specifies first/last word, header, all65slots and reset.
Flags are not enabled in a released kit. No new layout gate or submission has been launched.

Validation:
- cal reset/control + PIPE_JOIN delayed-golden miter PASS9963 comparisons (quiet reset warmup, boot, static starts,
  random returns, malformed/conflicting traffic and midrun reset).
- CTX delayed-golden miter PASS9798 comparisons; mutants1/2/7 caught with committed failure witnesses.
- Actual loaded-Lib authority: cal_native_authority/native_census.json PASS max32,8657roots,5Libs,no role errors.
- ctx_native_authority/native_census.json PASS max32,864roots,5Libs,no role errors.
- Tool/Lib/netlist SHA and immutable Docker image IDs are retained in authority packets; source archive manifests
  inputs_{miter,synth}_*.json pin exact source bytes and top-parameter transformations used on the fleet.
- Early raw/no-keep and intermediate failing census evidence retained. Production ot_keep_regs.tcl is required;
  plain keep-wire attributes do not preserve replicated flip-flop cells by themselves.

Blocking child:
CLOSED row_tx_ctx_c1b IO native audit passed historically but its independent every-driver census FAILS.
rowctx_c1b_native_authority_replayed.json: max1082,4489roots,6actualLibs,zero role errors.
emb_tx_slot pinFF1082; combinational549; fill_begin145; reset75; word_index36/66 and other violations.
The purged macro TT Liberty was replayed from source7ea686674, matching its immutable gate source SHA exactly
(6b00b7c554b89a7d24e02281ebef210c45b9de8b659130daeb852fd159c43d54). No child source/netlist changed.
Child needs structural slot/payload/control copies, reset and index decode successor before ANY parent gate.

Eight-item checklist for future critical review:
1 Pins: component input/output stages retained; parent must regenerate its existing full-face pin wrapper.
2 Reach: PENDING fresh placement and candidate child view. No reach waiver or new layout claim.
3 Fanout: cal and ctx PASS official truth-transparent32 census; child FAIL1082 blocks parent admission.
4 Depth: PENDING physical gate at existing clock/uncertainty. No timing relaxation.
5 Storage: component fixed payload/control pipelines, 192-bit calendar table and bounded identity state <2kb;
  existing row storage is real SRAM. Candidate child storage must remain SRAM.
6 Floorplan: PENDING child successor. Old x1 PNGs are historical failure evidence, not approval of new source.
7 Clock: PENDING new CTS. Candidate regional reset+6 is explicitly priced; old child native spread not fanout proof.
8 Schedule: STATIC, +1CTX+1join and +6reset warmup recorded; no credits/backpressure. Compiler adoption still owed.

Old gate pickup:
x1a WARN39.6/35.7,GRT0 is NOT source qualification (old reset316,max593).
x1b FAIL84.4/83.8,GRT0. Old e2a max530/valid298 is NOT source qualification.
PC_Hsr6 kept129family TSV<=32 missed functional comb802. PCsr7/b mapped effective census each231over32,
including one unused SETN tie root;230functional drivers violate, max806. Original PC GRT jobs preserved.
No REVIEW written, no failing source submitted, and no Claude worktree mutated.
