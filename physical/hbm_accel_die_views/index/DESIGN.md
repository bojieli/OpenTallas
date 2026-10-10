# hbm-indexer: the real DS-V4.1 indexer on the HBM die (r25), for review

Stream hbm-indexer. Branch `claude/hbm-indexer-20261008`. Written 2026-10-08 ~22:50 PT. **STATUS: PENDING REVIEW. No route is queued.** The route specs are drafts in `physical/hbm_accel_die_views/index/specs/` and are marked `_PENDING_REVIEW`.

## 1. Gap (coverage T3 #1)

- The six `hfd_index_q_b*` bands are a pipe shell with a placeholder `t_vm = key[511:0]^key[1023:512]`. They have no scoring, no top-k and no selector.
- `hfd_index_q_b0/b1/b3/b5` are now in `superseded_elements.json` with the reason "placeholder: not the indexer".
- b2 is the same shell. It has live safe-hbm routes; a note is in `safe-hbm.log`.

### A second, hidden gap

The r25 svc reads index keys through one pseudo-channel: kind 2 returns 4 sectors on `IK_PC`. That is about 1/32 of the stack's bandwidth.

- A real scorer behind it would run at about 0.4 keys/cycle per stack: roughly 7k cycles a layer, or about 50k a token.
- The token path charges the scan at full stack rate (the 32-PC `hbm_streams` bench).
- **Whatever the indexer looks like, the svc must stripe index-key reads over all 32 PCs.** This needs the svc owner.

## 2. Top-down budget (29.3k AR cycles over 8 index layers)

Of the 29.3k, the die-local indexer owns about 6.4k cycles over 8 layers (token path `hbm_ds.json`). The collectives `q_gather` and `96x512 merge`, plus `select:96x512`, are the TU / coll scope.

| per layer | index_q | scores | cand_local | topk_local | sum |
|---|---:|---:|---:|---:|---:|
| L2, L8, L14 (5,464 keys a die) | 278 | 253 | – | 158 | 689 |
| L20 (10,928) | 278 | 364 | 434 | 142 | 1,218 |
| L24–36 (cand mask inside the scores) | 278 | 364 | – | 142 | 784 |

### Binding resource: the HBM key stream

- One stack holds 342 blocks, which is 2,736 keys × 68 B = 186 KB a layer.
- At 1.0 TB/s that takes about 223 cycles (233 cycles at the measured 95 %).
- The owner's ≥ 90 % rule needs at least 6 lines (1,088 b each) per cycle per stack, which is 12 keys/cycle.

### Sizing

- The scorer width is the smallest multiple of the 8-key block that covers the stack rate. The selector and candidate units need block-aligned 16-lane beats, and 12 keys/cycle breaks that.
- So each stack gets **16 keys/cycle = 4 × NK4 `ot_hdc_v41x_idx_score_slice_l` slices** (FPL 7 / FML 5 / QL 5).
- That is 171 cycles of ingest against the 223-cycle HBM bound. The scan stays HBM-bound, so the scorer adds **0 cycles** to the charged scores node.
- This is the same 64 keys/cycle per die as the qualified `ot_hbm_accel_index_path`, regrouped as 16 per stack.

### Added cycles, priced

| Term | Cycles |
|---|---:|
| q-bus die leg before scoring | +~22 a layer |
| score-stream leg (fill) | +~22 a layer |
| VM output | +2 |
| **Total** | **~+46 a layer = ~+370 a token (+0.05 %)** |

- The bench in §5 measures these terms at LEG = 24.
- Not counted: the MTP verify. It runs 6 index frames a layer per step, so 6 scans. A multi-query slice that streams the keys once is listed as future work, not built.

## 3. Microarchitecture (RTL in `physical/hbm_accel_die_views/index/rtl/`)

### `hfd_idx_score`: one per stack, `L = 16`

**Inputs**
- 8 key-line ports (`{data1088 = 2 keys, tag10, v}`). Port p carries lines p, p+8, … in order. Each port has a 16-deep landing FIFO and returns a credit to the svc.
- `FWD = 1` gives forwarded-clock capture on the falling edge plus `ot_hbm_accel_cdc_fifo`.

**Beat assembly**
- One line from each port makes a 16-key beat.
- The block checks the tags.
- It generates the global IDs itself: `8·(96·ord + rank) + off`, with quarter = stack = ordinals 342q….
- It computes the refusal (any scale byte ≥ 253).
- It sets keep from the stack's 342-bit keep bitmap (the cand mask of layers 24–36).

**Datapath and outputs**
- The scorer is `ot_hdc_v41x_idx_array_l` (NS 4, NK 4) with its arithmetic unchanged.
- The query is loaded from the q bus: config, keep and 32 head beats. Keys are held until all heads are loaded plus 4 settle edges.
- Score beats are 610 b and flow on credits (CRED = the selector's landing depth).
- `qx` re-registers the q bus for chaining column taps.
- With `L = 4` and `LANE0 = 4c`, the same module is one column tap (plan B).

### `hfd_idx_sel`: one per die, in a spine slot beside the VM

This is **`ot_hbm_accel_index_path` cut at its scorer**. The exact connected bench `PASS_HBM_NATIVE_CONNECTED_INDEX` covers it, and its children are unchanged:

- `ot_hbm_accel_index_query`: FP32 blocks from the VM, then actquant FP4.
- `ot_hdc_v41x_sel`: Q 4 × W 16, K 512, ties to the lower ID.
- `ot_hbm_accel_index_candidate`: K 2048, newest-block pin.

**What changes**
- Four stack score streams, or 4·T tap streams, land in credit FIFOs. A quarter's beat issues when all its taps hold it, which is the atomic beat of the array carried across the die.
- The top-k and candidate outputs are serialised in quarter order to the VM, with credits.
- Line memories are behavioural for the bench (`MEMV = 0`). For P&R they are 12 × `ot_sram_1r1w_256x256` plus 4 × `ot_sram_1r1w_1024x256` (`MEMV = 1`).
- Refusals, replay and overflow raise a fault, as in the parent.
- Every die input lands in a flop and every output leaves a flop.

**Contract kept from the parent: contiguous quarters**
- Stack q must hold die block ordinals 342q…342q+341. The KV / index-key write path (`dskv_wb`, T3-D20) must place keys that way.
- `hbm_streams` assumed block interleaving instead.
- At context below 1M the scan time stays at the 1M value, because the early stacks fill first. The 1M headline is unaffected.

## 4. Area and fit (re-split, no die growth)

### Cell area

| Unit | Area | Source |
|---|---:|---|
| `ot_hdc_v41x_sel` Q4 | 98,876 µm² | yosys/abc ASAP7 RVT TT |
| `ot_hdc_v41x_sel` Q1 | 26,886 µm² | yosys/abc ASAP7 RVT TT |
| candidate Q4 | 51,833 µm² | yosys/abc ASAP7 RVT TT |
| actquant | 6,318 µm² | yosys/abc ASAP7 RVT TT |
| Slice NK4, bottom-up | ~0.74 mm² | routed element cells: q4dot QL5 830, fadd7 517, bmul ML5 216, tail 1,712, plus delay lines and q registers |

- The slice synthesis is re-running with `-noshare`; see COLLECT.
- The bottom-up slice figure means the model's 5.9 mm² a quarter (`blockdot_um2` 2,511, a die area) is about 2× high.

### Block sizes

- `hfd_idx_score` (L16): ~3.05 mm² of cells, about 5.6 mm² at 55 % utilisation. That is about 2.0 × 2.8 mm.
- `hfd_idx_sel`: ~0.40 mm² including the macros (134k µm² of SRAM), about 0.75 mm². That is a 1,399 × ~560 µm spine slot.

### Plan C (recommended, sent to mtp-die)

- Each `hfd_idx_score` sits in the **empty side-band centre region** next to its svc's inner end. The SW region is x 10.6–13.4 mm, y 1.6–5.9 mm, which is 2.85 × 4.4 mm free; today it holds only relays at its edges.
- `hfd_idx_sel` takes a spine slot (for example above `hb_su_full`, where y 16.95–18.0 is free).
- Die W and H are unchanged. H stays 25.73 mm under r25s.

**Remove**
- `ik_{st}` (1,026 b) and `iv_{st}` (512 b).

**Add, per stack**
- 8 × 1,099 b key lines: svc to score.
- 571 b q bus: sel to score.
- 610 b score beats: score to sel.
- 1 b credits.

**Corridor for the key lines (GRT decides)**
- 5 ports through the SM inter-row channel (518 µm; about 59 % of usable tracks with the existing 2 kb x-multicast).
- 2 ports through SVC_GAP.
- 1 port through HCH.

**What stays in the old `index_q` slot**
- Only the attention-row merge `a0..a3 → t_su`, which is a real function.
- It needs a successor view without k / t_vm. Owner: die-views.

### Plan B (fallback if the key corridor fails GRT): column taps

- One L4 tap goes in each SM column channel: 4 per stack, 16 per die. A tap is about 0.76 mm² of cells, about 1.4 mm² placed, about 0.33 mm wide.
- Each SM group widens by about 1.33 mm and `mid_ch` shrinks by 2.66 mm. W, H and the hub are unchanged.
- Keys travel at most about 1 mm from their PCs. The legs carry 154-b score beats, and the q bus chains through the taps.
- The RTL is the same: `hfd_idx_score #(.L(4), .LANE0(4c))` and `hfd_idx_sel #(.T(4))`. Both plans are benched.

## 5. Exact bench: `tools/hbm_idx_die_bench.py` + `index/tb/tb_hfd_idx_die.sv` + `index/run_bench.sh`

The bench runs 4 scorer blocks (or 16 taps) plus `hfd_idx_sel`. The blocks are joined by 24-stage relay chains. An svc model supplies 8 ports per stack with random gaps and credits. A VM model supplies the FP32 query, with credits.

**Golden**
- `hdc_golden_v41` score lines (`rtl_hdc_v41x_idx_campaign.golden`, chunk8).
- `qdq_fp4_e8m0`.
- `topk_lowest_index`.
- The `candidate_blocks` block-max / newest-pin rule.

**What is checked**
- Every score of every key, bit-exact.
- The ordered top-512 list.
- The candidate list.

**Frames**

| Frame | What it covers |
|---|---|
| F0 | The **retained real rank-0 keys at 1M**: 10,928 keys from `connected_29a9_r1/input/keys.mem`; L20 mode; candidates on (1,366 expected, which matches the parent bench). |
| F1 | The same keys, keep bitmap on (L24 mode). |
| F2 | Partial die: rank 37, 4,100 keys; stack 1 has a partial last beat; stacks 2 and 3 are empty; newest-block pin. |
| F3 | One refused key; the frame must fault. |

**Mutants (each must FAIL)**
- `MUT_LANE`: key lanes swapped.
- `MUT_GID`: rank stride wrong.
- `MUT_KEEP`: mask ignored.
- `MUT_SVAL`: score LSB flipped at the landing.
- `MUT_QORD`: quarter output order wrong.

**Status:** detached on EPYC1 for T = 1 and T = 4. Results go to COLLECT in `hbm-indexer.log`.

## 6. Route specs (drafts, NOT queued)

`index/specs/`:

| Spec | Purpose |
|---|---|
| `hbm_idx_score_c1` | Plan C, common clock. Recommended. |
| `hbm_idx_score_c2` | Plan C with forwarded-clock line ports. |
| `hbm_idx_score_t1` | Plan B tap. |
| `hbm_idx_sel_s1` | Selector with SRAM macros. |

All of them:
- route at 770 ps, sign off at TT 833, hold at FF with HM 25;
- are gated by the exact bench, base plus 5 negatives.

**They cannot run before mtp-die publishes a die variant (R25I) with these masters.** `route_view.sh` takes outline and pins from `tools/hbm_die_views.py ports`.

## 7. Questions for the reviewer

1. Plan C (corridor) or Plan B (SM-group re-width)?
2. The svc change: striped kind-2 reads and 8 index-line ports per stack. Who owns it?
3. The SRAM macro output feeds the selector directly (TT clk→q 405 / 545 ps). Adding a capture register needs a read-latency parameter in `ot_hdc_v41x_sel_slice`, which is not built. Accept the direct feed, or require the register?
4. Contiguous stack placement of keys, against `dskv_wb` / `hbm_streams` interleaving.
5. Stop the safe-hbm b2 routes?
