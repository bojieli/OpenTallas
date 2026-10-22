# S81-RATE3 10-20: S81 DS ROM MTP >= 3,000 on the REAL p4l-MU die, compiled

Owner 03:06 set the targets: AR about 950-990, MTP about 3,000 or more. The levers are compiler fixes, top-k and the
router tag. A ROM layout change is allowed only if it is contents-only.

Branch claude/s81-rate3-1020. It is based on codex/s81-stage-admission-1020@c347cea9b, which sits on
codex/s81-calendar-capacity-1020@b82da5c37. That base already contains CALPIPE (claude/s81-calpipe-1020) and ROMCAP.
The compiler options are QPAIRS12, GU_MERGE and CAL_SEGMENT. All options are off by default, and no RTL or physical view
changes.

## 1. Finding: the compiler dropped rows on 4 of 16 slices (release blocker, fixed)
- The p4l-MU die has 122 physical frames. 12 slices have 8 frames, sid 4 and 10 (u_s_2S, u_s_5S) have 7, and sid 6 and 8
  (u_s_3S, u_s_4S) have 6. Measured from the bind9 die (die sha d0222e67): `xs_topo.describe()`.
- `xs_place.op_groups` and `xs_bf._bf_groups` dealt every slice's rows over 8 owners. The rows of the phantom owners 6/7
  were never compiled (Codex census: wq_b 384 rank rows, plus 54 GU and 60 down rows per expert). So every earlier
  "8-frame" calendar, including the 965.0 / 2,998.8 projection, compiled a die that does not exist.
- **Fix (opt-in `OT_XS_TOPO=1`, new tools/s81_dv/layer_prog/xs_topo.py):**
  - `dv_layer_compile.Die` records the physical frames per slice.
  - Every op deals its rows over the real frames.
  - The die-wide phase list takes the slowest slice's phase count.
  - Every frame spreads its rows evenly over all die-wide chunks (`xs_topo.chunk`, <= R rows each, so no empty FP
    phase).
  - Consumers updated: xs_place, xs_bf, xs_calendar (CAP cfg_d), xs_wqb_die.
- **Cost with the heads and ownership unchanged (topo):**
  - wq_b 8 -> 11 phases (+378).
  - wo_b 4 -> 5 phases (+127).
  - down 21 -> 28 phases (+910).
  - wo_a 12 -> 16 BF phases (+924).
  - Total: 897.5 AR / 2,820.5 MTP.
- **Fix of the cost (opt-in `OT_XS_PROP=1`, contents-only):** ops whose slice ownership is free deal their rows in
  proportion to the physical frames.
  - wo_b and ffn.down: row-sharded outputs, addressed by the compiler's per-slice CAP rbase / rcnt.
  - wo_a: inside each head group (even sids = group 0, odd = group 1). The S81-SMWIRE o gather is unchanged.
  - Result: wo_b 4, down 21 and wo_a 12 phases again. Only wq_b (head h stays on slice h) keeps 11 phases, and so does
    idx.q (6 phases, not on the DAG path).

## 2. Compiled die field calendars (xs_field_calendar die)
Run on ep9 with the release flags QPAIRS12 + GU_MERGE + CAL_SEGMENT. Inputs: CALPIPE fixtures, dieref, and the MU cal1
calendars. Results are in compile/<case>/.

| case | wq_b | wo_b | down | wo_a | router | gu | layer rows L0/L2 (<= 4096) | MU 46 AR / 10+1 MTP |
|---|---|---|---|---|---|---|---|---|
| legacy_s0 (8 owners, old) | 8 / 1189 | 4 / 701 | 21 / 2889 | 12 / 2893 | 5 / 1269 | 18 / 2810 | 1868 / 2006 | 0 collisions |
| topo_s0 / topo_s3 | 11 / 1567 | 5 / 828 | 28 / 3799 | 16 / 3817 | 5 / 1269 | 18 / 2810 | 1868 / 2006 | (L0 PASS) |
| **prop2_s0 / prop2_s3 (release config)** | **11 / 1567** | **4 / 701** | **21 / 2896** | **12 / 2893** | **5 / 1269** | **18 / 2811** | **1868 / 2006** | **0 collisions** |

Each cell is phases / compiled span. In prop2 the down and gu tails are the tails measured on the new row splits
(section 3), 296 and 346. Every op is static PASS on L0, L2, L14 and L20. The calendar selftest is 23/23 in both the
default and the release mode (selftest/). Both slice 0 (8 frames) and
slice u_s_3S (6 frames) compile with 0 faults and the same die-wide phase list.

## 3. RTL benches on the release frame exes (Verilator 5.050, FSEQ tb_toksim_fgu_seq +RETIRE, `fseq3.py`)
The compiled TOPO+PROP phases (compile_frame with the release flags) were run on a frame of an 8-frame slice and on a
frame of a 6-frame slice. The positive run is at the floor P; the negative run is at P-1 and must FAIL. Results are in
fseq3/<frame>/<op>/summary.json.

| op | phases | u_f_0L00 (8-frame slice, v_h9nx_e5) | u_f_3L01 (6-frame slice, v_h10_e2) |
|---|---|---|---|
| attn.wq_b | 11 | P126 PASS / P125 FAIL | P126 PASS / P125 FAIL |
| attn.wo_b (PROP) | 4 | P127 PASS / P126 FAIL | P127 PASS / P126 FAIL |
| ffn.experts_gu | 18 | (ROM12: P145 PASS) | P145 PASS / P144 FAIL |
| ffn.down (PROP, +PHASE_VM) | 21 | P130 PASS 2895, P129 PASS, P125 / P120 FAIL | P130 PASS 2896, P129 PASS, P125 / P120 FAIL |

## 4. Composed rate (compose_rate3.py)
The composer is tools/toksim_s81_compose.py on the CALPIPE scenario. Each op takes its compiled span plus the record's
unchanged wire / CAP adder. Results are in compose/summary.json.

| scenario | AR tok/s | MTP tok/s | qualification |
|---|---:|---:|---|
| CALPIPE (existing) | 915.9 | 2,869.4 | proposed scenario |
| legacy 8-owner compile | 965.0 | 2,998.8 | = Codex projection; **invalid: drops rows on 4 slices** |
| topo (real frames, fixed ownership) | 897.5 | 2,820.5 | compiled, correct rows |
| **prop (real frames, proportional)** | **953.2** | **2,967.9** | compiled, contents-only |
| **prop + F8 window prefetch** | **966.2** | **2,998.2** | compiled, contents-only (see F8) |
| prop + F8 + top-k INDEXED13/HQ t276 | 970.9 | 3,064.8 | RTL: TOPK quarter must close and bind |
| prop + F8 + RTAG (BF P130) | 1,015.8 | 3,126.2 | RTL: BF front re-closure |
| prop + F8 + RTAG + top-k | 1,021.0 | 3,198.7 | both RTL items |

F8 (window_load):
- The lower_svc compiled job order is already CFG, OWN_ROW, WIN_LOAD, ATTN_Q.., then GO = max(q, WIN_LOAD + W_SLACK 560).
  The window load therefore starts when the own row is ready, not after q_rope. The composer DAG had the edge
  q_rope -> window_load, a sequential price.
- F8 removes that edge on the dense layers (144 window_load nodes) and charges the compiled W_SLACK 560 (measured 532,
  GATH).
- Sparse layers keep their wait on idx.topk_final.
- Not yet checked: the SVC MU-slot occupancy when the job starts at CFG. That job then starts about wq_b earlier, inside
  the same user's slot window.

## 5. Verdict
- **Contents-only (compiler) on the real die: 966.2 AR / 2,998.2 MTP.** AR is in the owner's 950-990 band. MTP sits at
  the ~3,000 floor (-0.06 %), not above it. The MU aggregates are 44,447 AR and 29,982 MTP.
- **MTP comfortably above 3,000 needs one RTL item.** The top-k quarter (3,065) is already in physical closure under
  S81-TOPK7 (HQ3 gate). The router tag (3,127) is a BF-front re-closure and needs a COORD decision.
- Still owed before headline adoption (same as CALPIPE / ROM12):
  - CAP cfg_d descriptors for the PROP shares on the die shapes.
  - A real consumer bench.
  - Stage expert map / ROM admission. Codex found 8378 > 8192 words per q pair before dense weights; OT_XS_COMPACT_TAILS
    is untested.
  - The MU SVC occupancy check for F8.

## 6. ffn.down bench note
The down summary.json VERDICT says FAIL. That is only because the automatic P-1 negative (P129) also PASSes: the
compile floor 130 has 5 edges of margin, as in FDOWN/FSDN. The required negatives are P125 and P120, which FAIL on both
frames (fseq3_neg.sh, fseq3/fseq3_down_neg.otrun.log). The compiler still refuses any period below 130 (CalendarFault).
