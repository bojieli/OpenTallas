# DS HBM accelerator: the ROM's exact levers, HBM side (design record, 2026-10-05)

**Owner directive:** give the DS HBM accelerator the same exact improvements the ROM gets, optimised as far as area, routing and timing allow.
- This record holds the architectural designs for five items.
- Item (1) is prototyped and **measured exact**; the other four are design notes.
- Codex implements and closes them. The handoffs are `/tmp/claude-review-20261003/handoff_to_codex_20261004/hbm_opt_<n>_*.md`.

**Basis.** The matched DS HBM reference `results/rtl/dshbm_matched_reference_20261005/composition.json`:
- gate AR 474.808 µs (row corrected+wg+fused_su0.9);
- gate MTP step 1,050.638 µs (row corrected+wg+su12); 3,958.5 tok/s at the adopted τ 4.159.

Both gate rows already credit the expert workgroup (L1). `tools/dshbm_hbm_opt_compose.py` re-walks them exactly (asserted) and writes `composition.json` here.

## Summary

| # | Lever | Status | AR µs | MTP step µs | Area / timing | Codex owner |
|---|---|---|---:|---:|---|---|
| 1 | Pipelined issue (accept op N+1 while op N drains) | **prototype measured exact** | **−34.923 (7.36 %)** | **−50.123 (4.77 %)** | ≈ 0.4 kb of state, no arithmetic; SM route OPEN | EUCLID |
| 2 | Partial-wave packing (tail injection of a whole small op) | design; estimate | ≈ −7.2 (est.) | ≈ 0 | bulk-copy PAIR request mode; TAGW + 1 | ERDOS |
| 3 | Activation delivery: static format-masked x map | design; composed from the measured load law | −9.747 | −70.014 | **zero logic** | PAULI |
| 3B | + 4,096-bit x port (optional) | design | −9.747 (A+B) | −101.974 (A+B) | ≈ 1 mm² a die, HIGH routing risk | PAULI (optional) |
| 4 | Expert workgroup layout + router-id steering | design (makes the credited L1 real) | 0 new (L1 −42.77 already credited); skew ≈ +1.8 est. | same | small; `stream_pc_la` keep-open on a closing block | HUBBLE (+ AMPERE) |
| 5 | Head / argmax | **REJECT**: neither ROM problem exists on HBM | −0.11..−0.16 | ≈ −0.12 | none | KANT (record only) |

- **Not additive.** (1) hides the x loads of independent ops, so (1) and (3) overlap. (2) is measured on top of (1). Each lever is recomposed on the PQ bench before it is credited jointly.
- **Composition rule:** only measured compositions are published as credits. (2) and (4) carry estimates; they are labelled and not credited.

## (1) Pipelined issue: prototype, measured exact

**Problem (C2 + part of C3 of the matched reference).** `ot_hbm_accel_issue` accepts `start` only when not busy, so every op pays its own drain: 65–100 cycles from its last line to its last row. Its x load is serial in front of it.

**Design.**
- `rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv`: issue successor; its body is ot_hbm_accel_issue ENABLE=1 line for line except where marked PQ.
- `rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv`: SM successor; it is ot_hbm_accel_sm_v ENABLE=1's body plus the marked PQ lines.

The PQ changes:
1. **Op queue.** start/op become a credit channel (2·PIO+3 posted ops, like the descriptor port). The new pin `start_ready` is a registered credit decode.
2. **Launch.** The issue launches the head as soon as no op is in setup or issuing, fewer than NOUT = 4 ops are outstanding, and the retire-order guard is clear.
   - The launch latches the op's format and x base. That edge is ≥ 1 after the previous op's last line entered s1, so that line's unpack still sees its own format.
3. **Op table.** `rem` becomes an in-order table of outstanding ops (`rdone` retires the oldest).
   - `arrive` toggles once per completed op, in op order.
   - `busy` = setup, issuing or outstanding.
4. **x ring.** New op field `op_xb`: the op's x-store base, with read address (op_xb + xa) mod 128.
   - The hub gives each loading op the next free ring range and starts its beats once that range is disjoint from every op not yet completed. So op N+1's load overlaps op N without a WAR hazard.
   - An op that reuses x takes the resident base.
5. **Leaf G1 select by the producing column** (`ot_hbm_accel_smpq_leaf`: `bov ? by : fy`, which is ot_gpu_sm_v's original select).
   - The as-built leaf selects by `ibf`, the format of the line now *entering* the column macros. That is correct only while one op occupies the leaf.
   - Under PQ, the next op's format arrives while the previous op's results leave. Rows were mis-tagged and lost, and the first prototype stalled (`+TRACE` diagnosis).
   - **Negative control:** `--g1asb 1` restores the as-built select. Result: FAIL, as required: 13 of 13 ops wrong (results mis-tagged, 2 rows lost, the bench watchdog stops the run), `pq/stress_g1asb_negative.json`.
6. **Retire-order guard.** Rows of two ops must not retire from the streaming stack in one cycle (ot_gpu_stack faults) and must leave in op order.
   - A row of an op with G groups leaves D = COLLAT(fmt) + 7·ceil(log2 G) after its final issue. COLLAT is 58 (block-dot) or 72 (BF16); these are the measured drains 58 + 7L and 72 + 7L.
   - The guard holds op N+1 until `since(last issue of N) > max(0, 14·[BF16 → block-dot], D(N) − D(N+1))`.
   - **It never binds on DS.** Every DS op is chunk8 (c = 8), so its first column output is ≥ 7 × 8 = 56 cycles after its first issue, and the largest ΔD is 42. The HAZ = 0 stress run is exact too (`pq/stress_f1h0.json`), as the bound predicts.
   - It is kept, at ≈ 20 flops, for configurations with c < 7 or LEV > 4.
7. **Exactness.** The per-op line order, x addresses relative to the base, column arithmetic, golden tree and stack pairing are all unchanged.
   - **Hazards covered:** x WAR (ring), stack retire order (guard, bound), leaf gather select (fix 5), format/x-base switch timing (launch ≥ 1 edge after s1), result attribution (in-order table, `arrive` per op).
   - **Dependent ops:** the first matvec after a collective or local op waits for every earlier op to complete before its x load. That is enforced by the hub; the bench models it with the `dep` flag.

**Measured** (Verilator 5.050, ot-epyc2, one SM element NC 8, warm stream as the matched bench, bit-exact on every result of every op; records `pq/`):

| Record | What | Status | Cycles |
|---|---|---|---:|
| `pq/stress_f1.json` | P1 stress: 12 independent ops covering every falling-D and BF16 -> block-dot transition, x reuse and ring wrap | PASS (0 mismatching ops) | 2746 |
| `pq/ar_l20_f1.json` | P1 layer 20 with dependency flags, PQ | PASS (0 mismatching ops) | 4352 |
| `pq/ar_l20_f1s.json` | P1 layer 20, serial protocol (every op dependent) | PASS (0 mismatching ops) | 6360 |
| `pq/wg_f1.json` | P1 workgroup run (WG R12 + shared w1, w3), PQ | PASS (0 mismatching ops) | 1006 |
| `pq/wg_f1s.json` | P1 workgroup run, serial | PASS (0 mismatching ops) | 1238 |
| `pq/other_f1.json` | P1 other shapes (engram K6144 R9, ratio-2 wq_b, head R43) | PASS (0 mismatching ops) | 4932 |
| `pq/p6_stress_f6.json` | P6 stress | PASS (0 mismatching ops) | 5778 |
| `pq/p6_l20_f6.json` | P6 layer 20, PQ | PASS (0 mismatching ops) | 8240 |
| `pq/p6_l20_f6s.json` | P6 layer 20, serial | PASS (0 mismatching ops) | 10776 |
| `pq/p6_wg_f6.json` | P6 workgroup run, PQ | PASS (0 mismatching ops) | 1910 |
| `pq/p6_wg_f6s.json` | P6 workgroup run, serial | PASS (0 mismatching ops) | 2390 |
| `pq/p6_other_f6.json` | P6 other shapes | PASS (0 mismatching ops) | 6724 |
| `pq/stress_f1h0.json` | P1 stress with the guard OFF (HAZ = 0): exact, as the c = 8 bound predicts | PASS (0 mismatching ops) | 2634 |
| `pq/stress_g1asb_negative.json` | NEGATIVE: P1 stress with the as-built leaf G1 select | FAIL as required (13 of 13 ops wrong; 2 rows lost, watchdog stall) | stall |

**Composed** (`composition.json` `item1_pipelined_issue`):
- Every independent run of the token's matvecs has its walk charge replaced by the measured PQ group, with + 1 handshake and one barrier of 66.
- The walk charge is its xload + sm + barrier rows.
- Single-op groups are unchanged.

Runs: W2 = the 7 expert w2 matvecs; GU = the routed gate/up workgroup + shared-expert w1, w3; ATTN2/3/4 = wq_a, wkv (+ compressor.wkv) (+ indexer.weights_proj).

| Run | Layers | PQ group cycles P1 / P6 | AR saved µs | MTP saved µs |
|---|---:|---:|---:|---:|
| W2 | 40 | 609 / 1361 | 19.9 | 26.832 |
| GU | 40 | 597 / 861 | 7.7 | 15.968 |
| ATTN2 | 32 | 301 / 621 | 3.92 | 3.92 |
| ATTN3 | 4 | 479 / 1439 | 1.43 | 1.43 |
| ATTN4 | 4 | 615 / 1575 | 1.973 | 1.973 |
| **total** | | | **34.923** → AR 439.885 µs | **50.123** → step 1000.515 µs, 4,156.9 tok/s at τ 4.159 |

- **Cross-check.** The same PQ element in the serial protocol (`--serial`) reproduces the walk's charge for these groups: W2 1.0567 vs walk 1.0608 µs, GU 0.7467 vs 0.7458 µs at P1; W2 1.8567 vs 1.8608, GU 1.1733 vs 1.1725 µs at P6. So the saving is the protocol change, not a bench difference.
- **Attention runs.** The walk prices wq_a / wkv / compressor.wkv / indexer.weights_proj as separate flush groups, one barrier each. They are independent and all feed `x_projections_gather`, so PQ runs them as one group with one barrier. That accounts for 7.323 µs of the AR saving.
- **Area / timing.**
  - Added state: op table 4 × 13 b, guard ≈ 20 flops, start FIFO 7 × 44 b, x base 7 b. No arithmetic.
  - The prototype's s1 x-base add is to be folded into the issue cursors (reset `cxb = xb`), which puts no adder on s1. The handoff specifies this.
  - The SM element route itself is still OPEN (GOODALL), and PQ adds nothing to that.

## (2) Partial-wave packing: tail injection of a whole small op (design; ERDOS)

**What it fixes.** In group-slot mode an op's last wave carries `items mod 8` real items. The other slots are bubbles for all 8 chunk steps. Packing puts the *next independent op's* items into those bubble slots. Item (1) must land first. Packing extends the PQ issue: the next op is already in the queue, its x is already resident at its ring base, and the retire-order rule is the same.

**Legal packing domain (v1, the only one worth building).** Op B packs into op A's last wave only if every condition holds:

| # | Condition | Why |
|---|---|---|
| P1 | B is independent of A, i.e. in the same PQ run (`dep = 0`) and already posted (its x loaded) | x residency; there is no dependency inside a run |
| P2 | `c_B == c_A` (8 in every token op) | one chunk-step loop per wave |
| P3 | same column type: A and B both block-dot (FP4/FP8 may mix), or both BF16 | the BF16 column is 14 cycles longer, so mixing collides at the leaf gather G1 (`gf = bov & fov`) |
| P4 | `D(B) >= D(A)` (`D = COLLAT + 7 * ceil(log2 G)`) | in-order retire with no gap, as in the PQ rule |
| P5 | `items_B <= 8 - k_A`, where `k_A = items_A mod 8`, so B fits entirely in A's last-wave holes | B's own stored line order (one partial wave, t-major, `items_B` lines per t) then needs **no re-layout**: the packed wave's line stream is, per t, A's `k_A` lines followed by B's `items_B` lines |

- **Chains.** If A+B still leave holes, a third op C may pack under the same rule against B.
- **Rejected as v2:** a general shift-packing, where B straddles waves. It needs a gather-address generator over B's wave-blocked layout. Measured shapes show it adds only GU (WG 36 + 5 + 5 items: 6 waves vs 7, about 2.1 µs AR) and the BF16 pair in 4 layers (about 0.2 µs). That is below the 1 % bar for its complexity, so REJECT.

**Where it applies in the token (busiest SM, measured shapes).**
- **w2 run:** 6 FP4 K2304 R2 ops of 4 items each. They pack pairwise into 3 waves instead of 6. Slot-6 w2 is FP8 with 6 items and gets no partner.
- **Nowhere else:** wq_a/wkv are 5+5 (P5 fails), cw/wp are 10+10 (P5 fails), WG/s6 is 36(4 left)+5 (P5 fails).

**Issue changes (on `ot_hbm_accel_issue_pq`).**
1. **Packed launch.** At launch the queue head may be a *pair* (A, B), marked by a new op field `op_pack` that the static program sets (it knows the shapes). `items_q = items_A + items_B`. The compiler passes the item counts, so no multiplier is added. `lw_q` and the masks follow the combined count. The wave count equals A's.
2. **Cursor hand-over.** When the gs cursor assigns A's last item (`cg_last && cr == rows_A - 1`), it continues with B: `cr <= 0`, `cg <= 0`, `cxb <= xb_B`, `g_end <= g_B - 1`, `fp4 <= fmt_B`.
   - The x base moves from the s1 add (prototype) into the slot record `s_xb`, which already exists per slot. The slot then reads its own op's x.
   - Two new per-slot record bits: `s_seg` (A/B) and `s_fp4`.
3. **Per-line format.** The s1 unpack select uses the line's `s_fp4`, not `fmt_q`. This is a 2:1 select that already exists, so only its select source changes.
4. **Two table entries at launch.** A, then B, each with its own row count. `rdone` retires in order. That is guaranteed by P4 because, at each t, B's items issue after A's.
5. **Results.** A's rows, then B's. The row tag stays op-local.
   - Add a 1-bit op parity to the stack tag and the result port (`rop`) so the hub demultiplexes by tag, not by timing.
   - This is a tag-width change (TAGW + 1) through the gather, tree and stack meta pipes. It is not on any arithmetic path.

**Bulk copy changes (`ot_hbm_accel_bulk_copy`, request side only).**
- New descriptor flavour, PAIR = (`base_A_tail, k_A, base_B, items_B`): for t = 0..7 it requests `k_A` lines from A then `items_B` lines from B.
- A's head (its full waves) stays an ordinary descriptor.
- The ring still receives lines in request order, so the consumer stays one in-order FIFO and nothing in the ring, credit or consume loop changes.
- The router-dependent w2 bases come from the expert-fetch descriptors that already exist (Hubble owns the expert stream; packing only pairs two of them).

**Expected saving.** Only an estimate until it is measured on the PQ bench:
- **AR, w2 run:** 3 waves × 64 cycles + 3 PQ boundaries × ~8 cycles ≈ 216 cycles a MoE layer, less any x-load exposure.
  - Each w2 x load is 33 cycles at P1. A packed pair issues in ~72 cycles, so the loads stay hidden.
  - × 40 layers ≈ 8,640 cycles ≈ **−7.2 µs AR (≈ 1.5 %)**.
- **MTP:** ≈ 0. At P6 the w2 run is x-load bound: 161 cycles a load as built, 129 with (3)'s static masked layout, against ~36 cycles of packed issue an op. Packing helps MTP only once loads drop below the issue time.
- **Acceptance:** keep the lever only if the measured PQ+pack w2 run saves ≥ 1 % of AR after (1) is composed. Otherwise REJECT with the numbers.

**Area / timing.**
- Per-slot record +2 bits.
- A second item-count register pair, plus the PAIR request sequencer in the bulk copy: two address counters and a t loop.
- TAGW + 1 through the meta pipes, about 10 flops a column.
- Risk: the bulk copy is routed-closed at 0.833 ns, and the PAIR sequencer sits on its request-address path. The gs cursor hand-over adds one more select level in the cursor update, which is registered: low risk.

**Exactness test plan.** On the PQ bench (`tb_hbm_accel_sm_pq_seq`, `tools/dshbm_sm_pq_seq.py`) add `op_pack` and the PAIR descriptor:
1. The w2 run packed (3 pairs + slot 6).
2. A stress run with every legal pair kind: FP4+FP4, FP4+FP8 (mixed fp4 bit), BF16+BF16 (K512 R32 is 32 items = full waves, so use R1 K512: 1 item), and chains of 3.
3. Each golden bit for bit.
4. **Negative tests (must FAIL):** a pair violating P3 (BF16+FP8) and one violating P4 (D falling) with the guard disabled.
5. The bench exits nonzero on any mismatch.

**RTL files.** `rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv` and `ot_hbm_accel_sm_pq.sv` (from (1)), plus `rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv` as a new successor file or a default-off parameter. Pinned files stay byte-identical.

## (3) Activation delivery for 6 positions (design; PAULI)

**What it fixes.** Every x address carries the full 3,152-bit column fragment: block-dot 8 × 266 b plus BF16 64 × 16 b. P6 has 6 columns, so 6 × 3,152 = 18,912 b, which is 10 beats of the 2,048-bit port per address. An op only ever reads one format's fields, and FP8 only blocks 0–3.

**Design A (recommended): STATIC format-masked leaf map, zero logic.** Change only the constant bit map in the leaf (`ot_hbm_accel_smv_leaf` `g_wb`, the localparam `F`) so that each format's used fields of the active columns are packed from bit 0:

```verilog
// as built: F = COL*XC + (SP*LBS + b/266)*266 + b%266            (block-dot bits)
//           F = COL*XC + LB*266 + SP*LSB*16 + (b - LBS*266)       (BF16 bits)
// static masked map (J = SP*LBS + b/266 = block index):
localparam integer F = (b < LBS*266) ? (J/4)*NC*1064 + COL*1064 + (J%4)*266 + b%266
                                     : COL*1024 + SP*LSB*16 + (b - LBS*266);
```

- Block-dot and BF16 regions overlap in beat space. That is legal:
  - A beat written for one format also writes the other format's bits at that address with garbage.
  - Every op reads only its own format's fields.
  - The x ring (1) gives each op its own addresses.
- **Beats per address:**

  | | FP4 | FP8 | BF16 |
  |---|---:|---:|---:|
  | P1 (as-built 2) | 2 | 1 | 1 |
  | P6 (as-built 10) | 8 | 4 | 3 |

- **Writer.** The x-broadcast root (fragment packer) writes beat groups by format. FP4 at P1 uses groups {0, 4}, at P6 {0..7}. `xw_grp` already selects the beat group.
- **Why FP4 is 8, not 7.** The split at `NC*1064` keeps every column's block half collision-free for any active count ≤ 8. A tighter map (second half at `act*1064`) would give 7 but collide when P > 6.

**Design B: a 4,096-bit x port** (as-built layout 5 beats at P6), or combined with A (P6 FP4 4 / FP8 2 / BF16 2).
- It doubles the x-write distribution: pin register + DW 4 stages × SUB 4 + L2 copies 8 ≈ 25 × 2,048 = 51,200 more flops an SM.
- At 0.2916 µm² (DFFHQNx1) that is 0.0149 mm² of flop cell area. About 0.03 mm² with buffering and CTS, so ≈ 1 mm² a die over 32 SMs (the SM element is 2.20 × 2.07 mm).
- It adds 2,048 more wires across each SM and through the root→32-SM broadcast tree.
- The SM element route is still OPEN (−4.0 ns at the die-budget IO, sm/closure.json), so routing risk is HIGH.

**Composed saving.** Measured load law: one beat a cycle + 1, `sm_seq` records; walk re-run, `composition.json` `item3_activation_delivery`.

| Variant | AR saved µs | MTP step saved µs | MTP tok/s | Logic |
|---|---:|---:|---:|---|
| A static masked map | 9.747 | 70.014 | 4,241.2 | none (rewired constant map) |
| ideal masked (needs a runtime map) | 9.747 | 74.014 | 4,258.5 | 3:1 mux a written bit |
| B 4,096-bit port | 13.747 | 68.734 | 4,235.6 | +51 k flops/SM, ≈ 1 mm²/die |
| A + B | 9.747 | 101.974 | 4,384.1 | as B |

- Basis: gate AR 474.808 µs, gate MTP step 1,050.638 µs (τ 4.159: 3,958.5 tok/s).
- **Recommendation.** Build A: AR −2.05 %, MTP −6.66 %, at zero area and no timing path. Take B (+31.96 µs MTP, −3.0 %) only after the SM element closes, as an optional lever priced at ≈ 1 mm² a die.
- **Interaction with (1).** PQ hides the loads of independent ops (they overlap the previous op's issue). (1) and (3) are therefore **not additive**. Re-measure the combined effect on the PQ bench with `XB` per format; the table above is (3) alone on the gate basis.

**Exactness test plan.**
- Run the PQ bench and the sm_v seq bench with the new map, a per-format writer and per-format beat counts, on `ar_l20`, `p6_l20`, `wg`, `p6_wg` and `other`. All results must match the golden bit for bit.
- Negative test: write FP4 with the FP8 beat count, so blocks 4–7 come from stale data. It must FAIL.
- Unit check: the leaf map is a bijection on each format's used bits for `act` 1..8 (Python, from the localparam formula).

**RTL files.** The leaf map lives in `ot_hbm_accel_sm_v.sv` (`ot_hbm_accel_smv_leaf`), which is pinned.
- Put the new map in the PQ successor (`ot_hbm_accel_sm_pq.sv`) with its own leaf copy (`ot_hbm_accel_smpq_leaf`, a parameter `XMAP = 1`).
- Add the x-broadcast root packer (die level, `rtl/hbm_accel/sm/ot_hbm_accel_stack.sv` or the hub that writes `xw_*`), plus the tools `gen_op` x packer.

## (4) Expert workgroup layout and router-id steering (design; HUBBLE, already running)

Hubble already owns the WG source (codex_notes 09:12, branch `codex/hubble-expert-workgroup-20261005`). Ampere owns the descriptor compiler (`tools/dshbm_expert_workgroup_descriptor.py`). This note is the architecture they build against. Full note: handoff `hbm_opt_4_expert_workgroup.md`.

- **Topology** (RTL facts):
  - 32 SMs over 4 stacks, 8 SMs a stack. SM j sits on stack `j[1:0]` (`w19_expert_fetch.json` `layout.stack_sms`).
  - Each expert is striped over all 32 PCs of every stack (`ot_hbm_accel_expert_fetch_stream.sv:11-15`). A 32-PC × 8-SM landing crossbar uses a `cfg_lut` (`…_la.sv:214-227`).
  - So any 6 of the experts load every PC equally, by construction.
- **Layout.** Workgroup task (slot k = rank of the id in ascending order, stack q) → SM j = 4k + q. SMs 24..31 do no workgroup work.
  - Recommended rows: stack q holds die-local rows 6q..6q+5 of both w1 and w3, interleaved, as SM rows (2r, 2r+1) = (w1, w3)[6q + r].
  - That is the same R12 op as measured (396 cycles, exact), with g and u of one index on one SM. SwiGLU pairs stay local.
  - The brief's one-matrix-per-SM variant is equally exact but pairs across stacks.
- **Addresses.** Inside an expert's slot: bit concatenation. The slot itself keeps the measured mapping `set = e mod 7`, `row = ROW_BASE + e div 7`.
  - A pure power-of-two expert stride would put 6 experts in 6 distinct bank sets only 7.7 % of the time, and it loses the refresh-parking set.
- **Steering.** The router id never reaches the SMs. The 24 SM descriptors are static constants. Steering lives where the ids already are:
  - the per-PC stream descriptors (row, set);
  - the landing SM select = k.

  Zero added cycles on the id path.
- **The one real change.** Today a PC streams whole experts back to back. Under the workgroup that funnels one expert into one SM, which the LAND = 4 sectors/cycle (≈ 154 GB/s) cap cannot absorb: slot 5 would start ≈ 1 µs late.
  - The dispatcher must instead interleave 8-sector chunks across experts, keeping same-bank-set experts back to back.
  - New `stream_pc_la` ports: `desc_j0`, `desc_keep`. Both default to 0, which is as built.
- **Unpriced cost** (ESTIMATE, Python policy model; to be replaced by the fetch-bench measurement): the start skew of the last slot is 84 ns mean / 164 ns worst. That is ≈ +1.8 µs AR net of the 49-cycle GU x load it hides (worst +4.9 µs).
  - **Do not also credit "GU x load under routing".**
- **Optional L1b** (not credited): the 8 idle SMs run the shared FP8 expert (fp8 K5120 R6) beside the workgroup. ≈ −11 µs AR (ESTIMATE); needs one SM measurement.

## (5) Head / argmax (analysis; KANT): the HBM head has neither ROM problem. REJECT the fusion.

- **Multiply-bound: no.**
  - The ROM head element had 2 BF16 multipliers a macro: 65,536 MAC-bound cycles against 7,360 ROM-read cycles. Fixed in 1c4e785ee: lm_head 73.6 → 6.99 µs.
  - The HBM SM has 64 BF16 multipliers per column, consuming one 128-B line a cycle, and the 8 columns *are* the verify positions sharing the weights (`ot_hbm_accel_sm_v.sv` leaves).
  - Head: 43 rows × 80 lines = 3,440 lines, s2d 3,563 cycles. **P6 = P1 = 3,563** (composition `sm_shapes`). The only P6 delta is the x load (801 vs 161 cycles), which (3) fixes.
- **In-order drain: no.**
  - The ROM terminal took 32,320 rows strictly in order at 1 row/cycle: +35.5 µs.
  - The HBM SM emits a row every 80 cycles with its tag (1.25 % port duty). `argmax_local` is a 1,024-lane SU reduce over 1,347 logits: 149 cycles P1, 174 P6.
- **Residual lever.** Fuse the existing exact `ot_dshbm_argmax` (draft path, 18 + 16 cycles) on the SM result port. It saves 0.11–0.16 µs AR (0.02–0.03 %) and ≈ 0.12 µs per MTP step. **REJECT** (< 1 %).
- **Guard to keep.** The head pulls 13.78 MB in 2.94 µs = 4.69 TB/s a die, above the 3.85 TB/s sustained rate. It stalls 0 only because the 15.7 MB prefetch window holds the whole head. If that window drops below ≈ 13.8 MB, the head turns HBM-bound (+0.61 µs).

## Replay
```
# heavy (remote, admit.sh, Verilator 5.050 on PATH):
python3 tools/dshbm_sm_pq_seq.py run --seq <stress|ar_l20|wg|other> --nc 8 --active 1 [--serial] --out pq/<seq>_f1[s].json
python3 tools/dshbm_sm_pq_seq.py run --seq <p6_stress|p6_l20|p6_wg|p6_other> --nc 8 --active 6 [--serial] --out pq/<seq>_f6[s].json
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 1 --haz 0 --out pq/stress_f1h0.json
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 1 --g1asb 1 --expect-fail --out pq/stress_g1asb_negative.json
# light (composes from the committed records, asserts the gate rows):
python3 tools/dshbm_hbm_opt_compose.py
```
- `tools/dshbm_sm_pq_seq.py` gained TIMEOUT-as-recorded-failure handling after the f1/f6 runs. The pass path is unchanged; the negative record was produced with the final driver.
- **Unvalidated here:**
  - The figures for (2) and (4) are estimates.
  - (3) composes the measured one-beat-a-cycle load law, not a run with the new map.
  - The x-broadcast network depth (root → 32 SMs) is unpriced, as in the matched reference.
