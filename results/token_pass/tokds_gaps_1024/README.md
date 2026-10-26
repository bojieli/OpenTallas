# TOK-DS gaps 10-24: what blocks arithmetic exactness on an S81 data cut

Branch `claude/tok-ds-gaps-1024` (from `claude/tok-ds-1024`). Die fc31 (35ba1ef7). Scope table: `gap_scope.json`
(17 items, ordered by how soon each one makes a data cut check arithmetic).

## Scope summary

| class | ops | kind | first data-cut check it adds |
|---|---|---|---|
| CUT-CLOCKS | (bench) | tool, **fixed here** | makes every slice region of the 0S / 0N / 7 / 3S_ctl cuts run at all |
| NORM-ISSUE | every norm (NORMR k0..k4) | **HARDWARE CONTRACT (new)**: xr needs the 5 leaf partials on one edge, but one CTL a cycle + per-leaf a1 (= XQ idx) staggers them | clears the endpoint fault on every reclocked cut |
| NX-SMOKE | attn.norm.sumsq, smoke slice | compiler only, **implemented here** | cut_0S: the xfin NX flit (5 FP32 partials) on 2 lanes |
| NORM16 | attn.norm.* (16 slices), attn.quant, ffn.norm.* | compiler only, **NX part implemented here**; rstd / XQ not yet | NX snake words on 0S / 0N / 7 (15 per cut) |
| Q-NORM4 | attn.q_norm / q_quant | compiler only, L | needs a_proj frame placement |
| RD-ALLGATHER | a/rows/router all-gather | compiler + replay tool, L | lt_lk payload order (elastic link: not a fixed-cycle word) |
| OUT-ALLREDUCE / COMBINE | attn.out_allreduce, ffn.combine_allreduce | compiler only, M-L | folded rows on the AG beats |
| PV-L0-EVIDENCE | attn.pv L0 | evidence only, S | svc cut |
| NORMALIZE-SO | attn.normalize L0 | compiler (PVSO entry bound on fc31), M | svc cut |
| SVC-COMPRESSED | scores/pv/normalize L2/L14/L20 | compiler + RTL (compressed rows) | svc cut |
| IDX-SCORE | attn.idx.score | compiler only: the scorer **is** bound on fc31 (7x dsdv_idx_rg3 + rg3_nq, iqf, slice_iq, bk_sel_vmtx); the lowering gap text is stale | bk cut |
| IDX-GATHER | attn.gather | **HARDWARE MISSING: runtime-index row read** (svc row read by a runtime index + bk_col frames) | svc / bk cut |
| IDX-MERGE-PATH | attn.idx.topk_merge | **HARDWARE MISSING: index-word path to the end slice** (bk_sel IDX words have no route to the end slice) | bk -> end slice |
| IDX-NEWKEY | attn.idx.newkey | **HARDWARE MISSING: index-key row write job** (svc s_j) | svc cut |
| ENG-GATE | eng.gate L14 | compiler only (op14 encoder lives in a tb), M | L14 data cuts (ENG flits) |
| ENG-WKV | eng.wkv L14 | compiler only, L | frame cuts |

Counts (17 items): 10 compiler-only, 3 hardware missing (IDX-GATHER, IDX-MERGE-PATH, IDX-NEWKEY), 1 hardware contract
conflict (NORM-ISSUE), 1 compiler + RTL
(SVC-COMPRESSED), 1 compiler + replay tool (RD-ALLGATHER), 1 bench tool (CUT-CLOCKS, fixed).  G-COMPILER-ROWS = 10 op
rows, G-NORMALIZE-SO = 4 (L0 PARTIAL, L2/L14/L20 GAP); the norm rows are PARTIAL on all four layers.  Only CUT-CLOCKS,
NX-SMOKE, NORM16 and ENG-GATE put arithmetic words on the 0S / 0N / 7 cuts; everything else checks on svc, bk or frame
cuts.

## What was implemented

`tools/s81_dv/layer_prog/norm_nx.py`, behind `dv_layer_compile.py --entry-norm-check` (default output unchanged):
the smoke slice's NX flit is no longer a plan-only event. The compiler

* writes the layer-entry state (H rows 0..31, gains 64..79, delayed pre at row 1008: 245 native XR target-5 row writes
  from `entry_inputs.py`, two edges apart, ending 40 edges before HLOAD) as CTL events at negative layer cycles;
* computes the expected flit from the fixture **inputs** (`io/h_in`, `io/pre_in`) with the repo reference model
  (`hdc_golden_v41`, chunk8): x = BF16(sum pre[j] h[j]), partial k = csum of x^2 over beat 5 sid + k. It asserts the model
  gives back the fixture `hc_pre` and the fixture `norm.sumsq` (padded tree of all 80 partials). Nothing is copied from a
  simulation;
* emits one 276-bit out word on each flit port (the ot_s81sl_rstop nxb ABI: header kind 3, hops, sid, base, 160-bit
  data). The edge is the last NORMR + 138, measured on the reclocked fc31 RTL (136 came from the frozen-clock bench).

`--entry-norm-check all` (`norm_nx.emit_all`) extends this to all 16 slices: every slice's NORMR k4 is placed so that
its arrival lands on the same edge G = 226 (k0..k3, GAIN and HLOAD allocated backwards from it on free issue edges of
the tier, fail closed), so all 16 xstops inject at E0 = 364. The 3920 entry writes go round-robin per tier and end
before the first busy edge (first issue -1996 / -1922 on S / N). The snake (S line W->E, up column 7, N line E->W,
down column 0) gives 240 out words: each own flit, plus every forward with land = edge + lane age and the next edge
= land + NX_FWD. NX_FWD = 6 was measured from the unscheduled forwards of run r3all, whose forwards were all exact
6 edges after they landed. The run has 120 norm commands.

L0 / sid 0 expected partials: `3f010292 3ee54c4a 3eebe45c 3ee29fb0 3f0057fa`. The output edge is 362, with words on
`vo` (hops 7, lane tvN_s_0S) and `ro_e` (hops 8, lane xrE_0S_l0).

`dv_cut_replay.py` drives `payload186` CTL events as seq_host line beats and honours an event `width` (one lane of a
4-lane port). Tests: `layer_prog/test_norm_nx.py` (new), `test_dv_cut_replay.py` ALL PASS, `test_dv_layer_compile.py`
PASS.

## Finding: the fc31 data-cut benches never clocked 10-22 slice regions

The first run (`r1`, existing fc31 cut_0S binary) landed both flits on the exact cycle, but **the data was all zero**.
The cause is that `dv_slice_cut.CLOCK_PORT_RE` does not match slice region clock pins `ck_<REGION>`. The MU72 / c1x /
c3x slices take ck_K, ck_ML, ck_L0, ck_L1, ck_L3, ck_L4 and ck_CAP_CE/CW/RN/RS/RT on such pins. The cut classed those
nets as `die_input`, and the bench held them at 0, so leaves 0, 1, 3 and 4, the lep K / ML regions and the CAP regions
never clocked. (ck_S / ck_N<k> were caught only because a relay also takes them on `ck`. This is the same class of bug
as RTLGAP-G9 ck_r<k>.)

Affected: all four fc31 cuts.

| cut | frozen region clocks |
|---|---|
| cut_0S | 11 |
| cut_0N | 10 |
| cut_7 | 22 |
| cut_3S_ctl | 9 (`ck_sl_s_4S_*`) |

Every earlier fault-free replay of these cuts was vacuous for those regions.

Fix: the regex now matches `ck_[A-Z][A-Z0-9_]*`. `tools/s81_dv/tokfunc/fc31/reclock_cut.py` re-benches an existing cut:
`slice_top.sv` stays byte-identical, only those port kinds change, the port indices are unchanged, and the tb diff is
exactly 11 `reg = 0` → `wire = ck` lines plus the 11 dropped input-case lines.

## Results (fc31 die 35ba1ef7, L0, reclocked cuts; epyc3 `/srv/opentallas-scratch/claude/tok-ds/gaps/`)

Every run uses `gaps_nx.sh` (commit on this branch): compile into a new dir, gen + sim + check `base`, then the two
negative controls. `mut_in` = `corrupt:<input lane>:91[:<sid>]`, which flips data bit 30 of the first entry write that
enters the cut and is addressed to one of the cut's slices. The `:<sid>` selector is new on this branch. cut_7's lanes
carry every slice's entry writes past the cut, so the plain first word there was 0N's. That run, uncaught as
expected, was deleted. `mut_ex` = `expect-shift:NX:1`, which checks every NX word one cycle late on the same trace.

| run | cut | NX words checked | base: NX mismatches | mut_in | mut_ex | cut verdict |
|---|---|---|---|---|---|---|
| r4 (smoke) | cut_0S | 2 (tvN_s_0S, xrE_0S_l0) | **0** | 2 / 2 caught | 2 / 2 caught | FAIL: endpoint fault (NORM-ISSUE) |
| r4all (16 slices) | cut_0S | 15 (7 + 8) | **0** | 2 caught | 15 / 15 caught | FAIL: endpoint fault (NORM-ISSUE) |
| r4all | cut_0N | 15 | **0** | 2 caught | 15 / 15 caught | FAIL: endpoint fault + strict lanes carry unencoded traffic |
| r4all | cut_7 | 15 | **0** | 2 caught (7S entry, sid 14) / 2 caught (7N, sid 15) | 15 / 15 caught | FAIL: endpoint fault + strict lanes carry unencoded traffic |

All NX words are FP32 partials of the layer-entry hc_pre RMS sum of squares. The compiler derives them from the
fixture inputs through the reference model, and the RTL reproduces them bit for bit on the cycle the compiler
predicted, including the forwarded words of the other 15 slices that pass through each cut. Both controls are CAUGHT
on every cut. Real cycles: the first NX word leaves the 0S output register on layer edge 364. The checked words land on the 0S
output lanes at layer 368..479 (bench t0 1986). The cut_0S 16-slice sim ran 13475 cycles in 395 s on one thread.

**No cut run PASSES.** The arithmetic matches, but two independent reasons fail every cut:

1. **NORM-ISSUE (new, hardware contract).** The sticky `o__endpoint_fault` is set from layer edge 358 in every
   reclocked run, and also in the pre-existing zero-data fc31 L0 replay once its clocks run (`gaps/zero_reclock`,
   first_fault 458 at t0 100). A debug bench (`gaps/dbg_fault`, `gaps/dbg_fault2`) traced it: u_sl.u_xr fault at
   bench 816, slice fault 822, endpoint 824. The cause is the `fb` term `(|pv) && pv != 5'b11111`, because the 5 leaf
   partials arrive one per edge (p_v = 00001 .. 10000 on 813..817). They do so because the compiler must issue
   NORMR k0..k4 on 5 edges: two CTLs per cycle is an xr fault, and each leaf needs its own a1, since vq's XQ / XB
   header idx is `a1`. The RTL wants one same-edge issue that the command path cannot deliver. Fix options (owner
   decision): vp/vq take idx = a1 + k (leaf strap) so that one leaf-mask-0x1F NORMR serves all 5 leaves; or xr
   accepts the 1-edge stagger. Under the frozen-clock benches the fault flop never clocked, so earlier runs were
   silent.
2. **Strict lanes with unencoded traffic (cut_0N, cut_7; NORM16 / RD-ALLGATHER).** The die-link lanes lt_lk_WN0..3
   / lt_lk_EN, ES (elastic link framing words from the entry phase on) and the line lanes l1..l3 (xrE_0N, xrW_6N,
   xrW_6S) carry words from layer edge ~709 onward
   (other ops' ring beats: XQ and later attention stages) that the compiler does not encode yet.

Also run: `r1` (frozen-clock fc31 cut_0S, the evidence for CUT-CLOCKS: the flits landed on the exact edge with zero
data), and `r2` / `r3all` (calibration runs: base data 0, 1-2 edges late -> NX_AFTER_LAST_NORMR 136 -> 138 and
NX_FWD 4 -> 6, both measured from the trace; their mutant dirs were pruned).

NOT RUN: XQ / rstd words (not encoded), cut_3S_ctl (no NX words on it), L2 / L14 / L20 (smoke only on L0), any svc /
bk / frame cut.

## Next steps

1. Owner / RTL decision on NORM-ISSUE (S). After it, cut_0S is expected to PASS outright, since its lanes are loose
   (an unencoded XQ event sits on u_s_0S) and its data is already exact. 0N / 7 also need item 2.
2. NORM16 rest (M): encode rstd return and the XQ all-gather beats. This makes the 0N strict lanes clean except
   lt_lk (RD-ALLGATHER tool work).
3. Re-run every earlier fc31 data-cut verdict on the reclocked cuts. The frozen-clock benches made them vacuous for
   the K / ML / L0 / L1 / L3 / L4 / CAP regions.
