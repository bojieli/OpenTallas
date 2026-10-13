# HBM die B2: quadrant-local VM slices (spec, 2026-10-12)

**Status: v0.8 (10-12 PT; v0.8 = wide-lane credits (D-B2-12, coordinator decision 13:25): every slice wide lane holds 4 + 2 x (relay stages each way) credits, a per-lane parameter of the bank tile set from the contract relay count, default 3 -> 10; v0.7 = v0.7 = HC x lanes settled by the HC tile stream (02c9777e0): 8 x 150-b lanes a quarter (4 a tile, 2 tiles a quarter), 1,200 + 16 b, replacing the 2 x 278-b TBD; compiler rule F4 (x transposed in the local / mirrored region); cut re-check in section 6a; v0.6 = IDX.INDEX gets a WIDE lanestation slot (slot 5) on slice SW, operand placement rule IDX-P; v0.5 = HC weight aperture MOVED to 294,912-360,447 (REPL keeps 262,144-294,911), COLL star edge and ring channel adopted as built; v0.4 = GRT gate PASSED (section 7), ring physical channel settled against the built VM-slice RTL, coll_tkm kept, contract v9 proposal in section 6; v0.3 = section 5.0 budget counts EXPOSED cycles + bandwidth sizing; v0.2 = section 5a fixes F1-F3 from the measured OLD-VM traffic, COLL broadcast star 2,112 b).** Streams may build against the constants in section 2a. The open items
are marked TBD. The windowed hub GRT gate PASSED (section 7: window overflow -89.7 % vs v8). Changes after the gate are versioned here and
announced in `claude-takeover-20261007/el1011-hbm-b2.log`.

Owner direction 2026-10-12: make the HBM die easier to close by putting compute next to its data (ROM-die and
GPU/DaVinci practice), with no central hub carrying the main traffic. The study `results/arch/hbm_die_phy_study_1012/STUDY.md`
recommends B2. B2 keeps 4 PHYs and splits the central VM (`hb_hgi_vm`, 32 banks, 2.07 x 2.07 mm, about 62 kb of wide
ports on the spine) into 4 quadrant slices. This file is the B2 spec of record. Branch: `claude/el1011-hbm-b2`. Log:
`claude-takeover-20261007/el1011-hbm-b2.log`.

The current r25gq track stays live as the fallback until B2 is proven.

## 0. Gate: windowed hub GRT (step 1)

Generator preset `r25gqn_b2` in `tools/hbm_accel_die_fp.py` is v8 (`r25gqn_pr8`) with these changes:
- **Removed:** `hb_hgi_vm`, lgE/lgW, `hgi_vmw_dma`, `hgi_vmr2_dma`, `hgi_vmw2_coll` and the central `hgi_vmap`.
- **Added:** the slices, local lane groups, ring, COLL broadcast, ring-client taps, x-load and per-quarter `vmap`
  (sections 1-3).

The GRT settings are identical to the v8 window tests (`w_a`): window 11-19 x 9-17 mm, k = 16, 5 iterations, M4/M5
channel adjustment 0.5, `PYTHONHASHSEED=0`. Results are in section 7.

## 1. Floorplan (physical spec before RTL)

**Slices.** Four `hfd_hgi_vms` slices, each 950.4 x 1,684.8 um (1.60 mm2):

| slice | position (lower-left) | placement |
|---|---|---|
| SW | (13,400, 9,000) | beside its quadrant's SU \| SFU column, inner side |
| NW | (13,400, 15,200) | beside its quadrant's SU \| SFU column, inner side |
| SE | (17,770, 9,000) | mirrored about the SU columns' centre line x = 16,060 |
| NE | (17,770, 15,200) | mirrored about the SU columns' centre line x = 16,060 |

- The spine keeps `hgi_idx`, `idx_sel`, `mtp`, `loader`, `coll`, `cmdproc`, `quant` and `vm8`. The old VM site
  (14,399-16,472 x 12,506-14,580) becomes a free channel.
- Each slice holds:
  - 8 banks of the 32-bank `ot_hgi_vm_wide_bank` design (8 x 8,192 own words + a 4,096-word mirror window a bank);
  - its loader quarter;
  - its ring stop;
  - its local lane-group head.

  Utilisation target 50-60 %. Macro channels ≥ 20 um. Pins on the faces toward their peers:
  - local group: the SU-column face;
  - ring: the N/S face for the vertical link and the spine face for the horizontal link;
  - ring clients: the spine face.

**Local lane group** (replaces lgW/lgE). One per quadrant:
- 8 lanes, lane b ↔ local bank b;
- chain: slice → station at the SU face → station at the SFU face → station at the HC quarter face;
- chain hop bits: rdn 2,067, wdn 19, rup 131, wup 2,243 = 4,460 b, against 17.8 kb for a 32-lane group;
- client tap bits: 2,065 / 17 / 129 / 2,241;
- stations: `hfd_stn_lg<q>{0,1,2}`, 64.8-um banks, 1,036.8 um long;
- every hop is ≤ 504 um a stage, registered.
- **v0.8 lane credits (D-B2-12).** Every wide lane's bank queue holds `4 + 2 x S` entries, and its client holds the same
  number of credits, where S = relay stages each way between the lane's farthest client and the slice face (the chain
  stations count: SU 1, SFU 2, HC 3). The slice default is S = 3 (10 credits) for both read and both write groups.

**Ring** (`ot_hgi_vm_ring`, a 2 x 2 bidirectional ring):
- links SW-NW, SE-NE, SW-SE and NW-NE, each 2,148 b each way plus a 4-b credit return;
- `ot_fwd_link_stage` relays at ≤ 500 um;
- stage counts (generator relay count + 2 face flops) are in section 7.

**COLL broadcast** (replaces `hgi_vmw2_coll`, 8,961 b). **v0.2:** a STAR from `coll` to all 4 slices, one hop each
(the v0.1 2-hop tree doubled the tail). Each edge is 2,130 b (v0.5, as built: 8 sectors = 64 words a cycle, plus header) plus a 1-b
credit. The edge is sized for the gather payload, as section 5 explains. The running GRT gate still models the v0.1
tree of 2 x 1,088 b; the star adds about 4.2 kb on the y = 14 mm line and is re-checked in the next GRT.

**Ring clients.** The central units are 8-lane ring clients of one slice's ring stop (tap 4,452 b):

| client | slice |
|---|---|
| cmdproc CP | NW |
| cmdproc ATT adapter | NE |
| quant | NW |
| hc_eng | SE |

**SM.MATVEC x load and attention.** D19 used to put the x load on lgE slot 0. Now each slice feeds its own
quadrant's `hb_vm_<q>` (x read, 2,065 + 129 b), and attention q / p reads attach to the local slice.

**HC x lanes (v0.7).** Each slice → its own HC quarter: 8 lanes x 150 b = 1,200 b, plus 16 b back (`xl_cr` 8 + `xl_done` 8). v0.6 had 556 + 4 b (2 x 278).

**DMA.** The loader becomes per-quadrant: `lq_<q>` / `lr_<q>` from its svc band end at slice q. The wide 8,992-b
`vmw` and 8,257-b `vmr2` buses disappear from the spine. Their bandwidth is unchanged at 8 lanes x 4 slices.

**Wire reach.** No single-cycle path is longer than 500 um. The longest ring link (SW-NW, about 4.5 mm) is about
10 relay stages.

**Clock.** Each slice is its own hard tile with a local tree (≤ 15k sinks a root) and a clock entry on its spine face.
The die STA follows the view-insertion rule:
- each view's entry is tapped at the region target minus the view's insertion;
- every pin arrival is written as the real arrival plus the view's insertion. `tools/hbm_die_relay_sta.py` already
  works this way: clocks are created at the sink pins in propagated mode, with -source latency = target minus
  insertion, and the ETM arcs carry the insertion. The ideal-mode `set_clock_latency` error found on the Qwen die
  (main 092d3e600) does not apply. The B2 die STA reuses `clock_plan.py balance` for early taps.

## 2. Address map and VM semantics

HGI-1 is unchanged, apart from the additive REPL window below. The VM is still one address space chosen by the
compiler. Slices and mirrors are microarchitecture: a remote access is slower but legal.

| word address range | owner |
|---|---|
| 0 .. 262,143 | slice `addr[17:16]` (q = 0 SW, 1 SE, 2 NW, 3 NE), 65,536 words each; inside a slice, sector s is in bank `s[2:0]`, row `s[15:3]` |
| 262,144 .. 294,911 | **REPL window** (32,768 words), mirrored in every slice (`REPL_BASE` 262,144, `REPL_W` 32,768) |
| 294,912 .. 360,447 | **HC weight aperture** (65,536 words, `HCAP_BASE` 294,912, `HCAP_W` 65,536). **v0.5:** moved up from HGI-1's 262,144-327,679, which overlapped REPL (cmdproc stream, 07:20). Same size; HC-local via `vmap_<q>` |

v0.5 decode rule (cmdproc, compiler, simulator): by RANGE, never by a single address bit. `addr < REPL_BASE` → slice
`addr[17:16]`; `[REPL_BASE, REPL_BASE + REPL_W)` → REPL (local mirror); `[HCAP_BASE, HCAP_BASE + HCAP_W)` → HC
aperture; anything else is a fault. The four constants are parameters in the RTL and the compiler, so a later move is a
parameter change. The simulated VM address space is 360,448 words.

The REPL window uses the mirror storage, so each slice has 98,304 physical words = 1.5x.
- **REPL writes.** A write to REPL commits to the local mirror and streams to the other 3 slices over the ring.
- **REPL reads.** Always local.
- **REPL ordering.** It is per writer, and it is complete only when all 4 copies are written. A consumer in another
  quadrant waits only on the sectors it reads (per-sector valid scoreboard in the mirror, section 4). It never waits
  on a global flag.
- **Capacity check.** The DS HC residual is 20,480 FP32 words and fits the 32,768-word window.

**cmdproc and record adapters.**
- The record's VM operand addresses select the slice (high bits), or REPL.
- Each record is dispatched to the units of the slice(s) its operands live in:
  - SU / SFU / HC / attention records go to the quadrant unit that owns the operand;
  - a record whose operand spans quadrants is split by the compiler into per-quadrant sub-records (STRIPE4) that the
    cmdproc issues to all 4 quadrants in one dispatch beat.
- `cmdproc` routes a packet request (cq/cr) to the owning slice: local ports, or ring forwarding for remote ones.

**Compiler / exporter.**
- The VM allocator places quadrant q's TP slice in slice q: the outputs of SMs 8q..8q+7, its heads, and its SU operands.
- Vectors read by all quadrants (layer inputs x, norms, residual, HC state) go in REPL.
- SU templates are issued per slice.

## 2a. Constants and port protocol (for the compiler, VM slice, cmdproc, SM, attention, SFU / SU and HC streams)

**Clusters.** Quadrant q in {0 SW, 1 SE, 2 NW, 3 NE}. Cluster q contains:
- VM slice q;
- SMs 8q..8q+7;
- attention tiles of quadrant q;
- SU quarter q, SFU quarter q and HC quarter q;
- VM8 quarter `hb_vm_<q>` (the SM x source);
- loader quarter q;
- svc band / HBM stack q.

The central (ring-client) units are cmdproc (CP and the ATT adapter), quant, hc_eng, coll (via the broadcast) and idx
(via packet). **v0.6:** idx is ALSO a wide client: IDX.INDEX takes slot 5 on slice SW's local lane group (below).

**Address map.**
- `VM_WORDS_TOTAL` = 262,144 words, owned, plus the REPL window.
- `LOCAL_W` = 65,536 words a slice. The owner is `addr_word[17:16]`.
- `MIRROR_W` = 32,768 words (REPL, `addr_word` 262,144..294,911), mirrored in every slice.
- Physical size a slice: 98,304 words = 12,288 sectors.
- Banks a slice: `NB` = 8. Bank = `sector[2:0]`, row = `sector[13:3]` (own region) or row 8,192 + `sector[11:3]` (mirror).
- TBD: whether MIRROR_W can drop to 24,576 once the DS / Qwen replicated-vector census is in (compiler stream). The
  constant is fixed at 32,768 until then.

**Local lane group** (slice q ↔ the cluster's wide clients). `ot_hgi_vm_lanechain`, `lanestation` and `lanearb`
protocols are unchanged; only the lane count goes 32 → 8.

| bus | bits | content |
|---|---:|---|
| rdn | 8 x 258 + 3 = 2,067 | {v, sector data 256, + 1} a lane |
| rup | 8 x 16 + 3 = 131 | {v, sector 15} |
| wup | 8 x 280 + 3 = 2,243 | {v, sector 15, data 256, word mask 8} |
| wdn | 8 x 2 + 3 = 19 | credits / done |

- Client taps (lanestation local side): rdn 2,065, wdn 17, rup 129, wup 2,241.
- Lane b ↔ local bank b.
- Slot list a cluster: SU 0, SFU 1, HC 2, ATT (quadrant tiles) 3, SM x-load (VM8 quarter) 4. KE = 5 slots, a
  round-robin lanearb.
- **v0.6 (coordinator decision): IDX.INDEX wide slot.** Slice SW (q 0) is nearest the `hb_hgi_idx` site
  ((14,800, 7,113) um, below the SW slice at y 8,999), so SW's group has KE = 6: slot 5 = `ot_hgi_idx_index_w`
  (`claude/el1011-hbm-idxs`, `ot_hgi_idx_unit` IXW = 1), a standard 8-lane lanestation client (taps rup 129 / rdn 2,065
  / wup 2,241 / wdn 17; lane b ↔ bank sector[2:0]). The other three slices stay at KE = 5. A packet-only IDX.INDEX
  is not allowed: it measured 8.60x over its price on DS L24 (9,291 vs 1,080 cycles). idx keeps its packet port for
  TOPK / MERGE / OWNED.
- **IDX-P placement rule (exporter).** IDX.INDEX's query A (4,096 words), B (32 words) and candidate table C
  (2 x 2,048 words, stride % 32 == 0) go in REPL; its weights and outputs O / R / D go in slice SW's local region
  (0 .. 65,535). Every IDX.INDEX wide access is then slice-local (D-B2-8). The exporter refuses an IDX.INDEX record
  whose operands break this rule.
- TBD: whether attention takes its own station or shares the SU station (attention stream).

**HC x lanes a quarter (v0.7, settled by the HC tile stream, `claude/el1011-hcvm-hc4` 02c9777e0).** The v0.6 TBD (2 vs 4 lanes) is closed:
- **Count.** Each `ot_hgi_hc_tile` writes both of its x macros in one wave, two half rows each. That is 4 lanes a tile. A quarter has 2 tiles (8 a die), so it has **8 lanes**: lane l = 4 t + 2 m + h (tile t, x macro m, half row h), and lane l ↔ local bank l (= sector[2:0]). Each bank feeds exactly one lane.
- **Width.** `vmap_<q>` is **8 x 150 = 1,200 b**. A lane is `{v 1, sector 13 = {0, macro 1, row 10, half 1}, 8 x bf16 128, word mask 8}`. It is the 278-b aperture lane with the low half of each fp32 word dropped, because HC uses x as bf16 (= word[31:16]). The slice's HC station drops those halves, so only 150 b a lane cross the die. The return `vmap_<q>_r` is 16 b: `xl_cr[8]` pulses on the edge a lane's sector is captured (pin flop; one sector a lane every edge) and `xl_done[8]` on the edge it is written.
- **Tile side.** The lane pin flops merge into one macro row write, with the same latency as the old `xw_*`. The tile face carries 600 lane pins + 8 back, against 566 for `xw_*`.
- **Weights do not use these lanes.** The SYS tile path takes its weights from the HBM lanes (`ot_hgi_hc_unit` HSRC 0). The HC aperture range (`HCAP_*`, section 2) stays reserved in the address map.
- **Faults (fail closed).** The tile raises `t_flt` and the HC record faults when a lane's sector does not match its lane (macro, half: `sector & ~0x7FE` must equal `{0, m, 0, h}`), or when the two lanes of one macro name different rows in the same edge. No partial write is committed silently.
- **Mutant.** `MUT_XL` swaps the two half rows of a macro write. The tile bench must FAIL under it (job `hc_tile_xl-c2-8612208d7` judges `mut_xl` with a FAIL regex), which shows the lane-to-half mapping is observable.
- **Placement.** The compiler places x by rule F4 (section 5a).

**Packet clients (cq / cr)** are unchanged: 338 / 274 b, OUT = 4, responses in order. A client is wired to its local
slice, or the nearest one for central units. The slice forwards a non-local address over the ring.

**Ring link** (each direction, `ot_hgi_vm_ring`). **v0.4:** one wide physical channel a direction, 2,224 b + 2 x 2-b per-VC credits
(v0.5 as built in `ot_vms_rstop`; v0.4 quoted 2,223 b as packed by the VM-slice stream's CW channel on `claude/el1011-hbm-b2-vm`, plus a 4-b per-VC credit return),
carrying both VCs. The built RTL's CW-wide + CCW-narrow (292 b) split is replaced by the same wide channel in both
directions: with a narrow CCW, a REPL mirror write reaches the third slice after 3 hops (about 34 cycles instead of
12-23), which adds about 22 exposed cycles per x record (Qwen 0.44 %, DS 2.3 % of layer: over the R3 budget). Both VCs
share the wide channel with per-VC credits; a REPL_WR goes CW to sid+1, CCW to sid+3, and either way to sid+2.
Fields (v0.1 list, packing per the VM-slice RTL):
- fields `{v, kind 3 (RD_REQ / RD_RSP / WR / REPL_WR / RED_CARRY / COLL_BC), src 2, dst 2, tag 16, sector_addr 15,
  data 2,048 (8 sectors x 256), word mask 64, epoch 4, …}`;
- `kind`, `src`, `dst` and `epoch` are fixed. The packing is the VM-slice RTL's (2,223 b);
- credit return: 4 b a direction, credits = relay stages x 2 + 4 (TBD from the stage counts in section 7);
- latency: the hop stages in section 5;
- deadlock freedom: the ring is a 4-node cycle, so RD_REQ, RD_RSP and WR traffic use 2 virtual channels (request and
  response) with separate credits (dateline at the SW-SE link).

**COLL broadcast.** `vcb` (v0.5, as built) is 2,130 b a slice: `{v 1, sector_addr 13, data 2,048 (8 sectors), mask 64, epoch 4}`
plus a 1-b credit. It is a star, coll → each slice in one hop.
- **Cut-through.** Each sector is forwarded as it arrives from the links. The broadcast never stores and forwards a
  whole record.
- It writes REPL (or the owning slice) without a barrier.

**Ring-client tap** (cmdproc CP → NW, ATT adapter → NE, quant → NW, hc_eng → SE). It is the 8-lane tap above
(4,452 b). Remote banks are reached through the ring.

**Ownership and dispatch.** cmdproc dispatches a record to cluster q when its operands are owned by q. A record with
operands spanning clusters is issued as 4 per-cluster sub-records (STRIPE4) in one dispatch beat. The cmdproc address
→ slice function is exactly `addr_word[17:16]` below `REPL_BASE`; REPL and the HC aperture are decoded by range (v0.5).

## 3. Hard rules (owner, binding)

**R1. No global barrier.**
- Every cross-slice exchange (ring traffic, REPL mirror streams, COLL broadcast, reduction partials) is
  compiler-scheduled, streamed and credit-based.
- No record, unit or slice waits for "all slices": there is no barrier, no all-done flag and no die-wide fence in the
  datapath.
- Consumers start on local data while remote segments arrive. Each consumer gates on per-sector valid (mirror
  scoreboard) or per-partial arrival (reduction carry), never on a collective completion.
- The only die-wide synchronisation left is the existing DMA.FENCE record against HBM, which is unchanged.

**R2. Balanced MoE by construction.** Every expert's weight rows (and every dense matrix's rows) are split across all
4 quadrants/clusters:
- rows `[q*R/4, (q+1)*R/4)` sit in quadrant q's HBM stack;
- they are computed by quadrant q's SMs;
- the output segment lands in slice q (or streams into REPL if the next op needs it everywhere).

Any routed expert set therefore loads every quadrant equally. The exporter refuses a placement that puts an expert's
rows in fewer than 4 quadrants.

**R3. Exchange-latency budget per layer.** The budget is in section 5. Every layer's exposed exchange cycles must stay
within it, and the exporter reports the per-layer number.

**R4. Measured, not modelled.** The native die e2e bench (DS L2 / L20 / L24 + Qwen L0) records the actual
cross-slice cycles for every record with a remote operand: first-remote-sector arrival, last-remote-sector arrival,
and exposed cycles (consumer stall waiting on remote data). They are reported next to the budget in section 7.

## 4. Bit-exact cross-slice reductions

- A reduction over a vector spread across slices (norm sum of squares, softmax max/sum, dot partials) is combined in
  **the golden's order**:
  - if the golden reduces in a fixed chunk sequence, slice q computes the partial over its chunks in that sequence, and
    the partials are folded in chunk order by a serial carry around the ring (q0 → q1 → q2 → q3: one ring hop of
    latency a fold, streamed);
  - if the golden's order is a balanced tree whose level-2 subtrees coincide with the slices' chunk ranges, the
    partials combine as `((P0 + P1) + (P2 + P3))`.
- The RTL owner reads the frame reference for every reduction op and records which case applies.
- Re-association is never used.
- No reduction waits for all partials before starting (R1): the carry starts at q0 as soon as q0's local partial is
  done, and each slice folds the incoming carry as soon as its own partial is ready.
- Mirror scoreboard: every REPL sector has a valid bit per slice, cleared by the writer's `epoch` field. A read of an
  invalid sector stalls only that read.

## 5. Exchange-latency budget (R3)

**Hop costs.**
- Ring hop = relay stages (≤ 500 um each) + 2 face flops + 1 ring-stop arbitration.
- The planned values (confirmed from the generator's relay counts in section 7):
  - SW-NW / SE-NE about 12 cycles;
  - SW-SE / NW-NE about 11 cycles;
  - the diagonal (2 hops) about 23 cycles.
- A remote read round trip is at most 2 x 23 + 4 (slice pipeline) = 50 cycles.

**Exposure.** An exchange costs at most one farthest hop of exposure, because consumers start locally and the tail is
streamed. The study's bound is 16 cycles a record with a remote operand.

| | DeepSeek-V4.1 @ 1M (HBM AR) | Qwen3-8B @ 8K (HBM AR) |
|---|---:|---:|
| token cycles (S2) | 565,569 | 1,269,120 |
| layers (ATT records / token) | 40 | 36 |
| cycles / layer | 14,139 | 35,253 |
| records with a cross-slice operand / token | 722: ALL_GATHER 584, GROUP_REDUCE_MCAST 40, HC_PRE_NORM 81, TOPK_MERGE 9, ROW_GATHER 8 | 217: ALL_REDUCE_SUM 72, MATVEC output to REPL 145 |
| ... / layer | 18.1 | 6.0 |
| exposure budget / record | 16 cycles | 16 cycles |
| exposed exchange / layer, budget | 289 cycles = **2.0 %** of layer time | 96 cycles = **0.27 %** |
| no-overlap worst case (23 cycles / record) | 415 = 2.9 % | 139 = 0.39 % |
| overlap credit (SU local lanes, 8 cycles x 1,356 SU.VOP x 0.78 share) | -212 / layer (-1.5 %) | n/a |

The budget passes when the measured exposed cycles a layer (R4) are ≤ 2.0 % of layer time on DS and ≤ 0.3 % on Qwen.

### 5.0 What the budget counts (v0.3, settles the compiler / b2verif question)

**(a) The budget counts EXPOSED cycles only.** An exposed cycle is one in which a consumer stalls because the next
sector it needs is remote and has not arrived yet.
- Serial ring occupancy (words / link width + hops) is BANDWIDTH. It is reported, but not budgeted, as long as it
  overlaps the consumer's own work. Under the no-barrier rule (R1) consumers start on local data and read the remote
  data afterwards.
- The harness model "a 4,096-word x broadcast = 32 + 128 = 160 cycles" is store-and-forward at 32 words a cycle. B2
  does not do that. The exposed cost is

  `exposed = sum over records of max(0, t_arrive(s) - t_need(s))` over the record's remote sectors s,

  where `t_need(s)` is the cycle at which the consumer, reading in its own order, local sectors first, reaches s.
- **Harness rule.** Record per-sector `t_arrive` and `t_need` (R4), and charge `max(0, ...)`. A slice's consumer reads
  its local quarter first.

**(b) Width that keeps the exposed time within 1-2 %.** The exposure is hidden when every slice's inbound remote
bandwidth is at least the remote share of its consumer's read rate, so that only the first remote sector's hop
latency can show:
- **Consumer rate.** The local 8-lane group (and the x load to VM8) reads 8 sectors = 64 words a cycle. With F2, 3/4
  of a replicated vector is remote, so it needs ≥ 48 words a cycle inbound.
- **Ring.** A slice has 2 inbound links x 2,048-b data (64 words a cycle) = 128 words a cycle. That is ≥ 48, so it is
  hidden. A 1,024-b ring link (32 words a cycle, 64 inbound) would also pass for x, but at 1.33x margin only, so the
  ring stays at 2,048 b.
- **COLL broadcast** (single source, all of the vector remote): it needs ≥ 64 words a cycle a slice, hence the star of
  2,048-b data edges (F3). The v0.1 1,024-b edges halve the consumer rate, and THAT is the 128-cycle term in the
  harness.
- **Residual exposure a record:** the first remote sector's hop minus the local lead time. For x, the local quarter
  takes `N/4/64` cycles: 16 cycles at N = 4,096 (Qwen) and 28 at 7,168 (DS). That covers a 12-cycle adjacent hop, but
  not the 23-cycle diagonal. Per broadcast this is ≤ 0-11 cycles. A COLL star record exposes ≤ 10 cycles.
- **Exposed a layer:**
  - Qwen: 4 x-type broadcasts x ≤ 11 + 2 ALL_REDUCE x 10 ≈ 64 cycles = **0.18 %** of 35,253;
  - DS: about 238 cycles = **1.7 %** of 14,139 (section 5a).

  Both are within the 290 / 93 budgets, which are now defined as EXPOSED cycles a layer. The compiler's 1,009 → 540 a
  layer is serial ring occupancy at 32 words a cycle and is not comparable with the budget.

**tok/s from exposed cycles.**

| model | exposed (critical) | estimate | change |
|---|---|---|---|
| DS | ≈ 175 critical cycles a layer (1.2 %) | ≈ 2,095 tok/s; with the SU local-lane saving, 2,110-2,125 | -0.7 to +0.1 % vs 2,121.8 |
| Qwen | ≈ 64 cycles a layer (0.18 %) | ≈ 943.8 tok/s | -0.2 % vs 945.5 |

B2's cost is not materially above 2 %, provided F1-F3 hold and the harness measures exposed cycles as defined here.
If the measured exposed cycles exceed the budget once F1-F3 are in, the escalation trigger to the owner is DS > 2 % or
Qwen > 0.5 %.

### 5a. Measured OLD-VM traffic and the three structural fixes (v0.2, b2verif main 89610e018)

**What was measured.** The B2 verification harness (`results/rtl/comp_regress/b2_traffic_1012/`, `tb_hgi_e2e` B2 = 1)
used TODAY's allocator addresses with owner-computes placement. The exposed ring cycles a layer were:
- DS: 3,082-5,760 (10-20x the 290 budget; on layer bases of 11.6k-30.5k cycles);
- Qwen L0: about 6.5k (70x the 93 budget).

**Drivers in DS L2** (exposed / serial cycles):
- SM.MATVEC 1,968: remote x reads;
- COLL.ALL_GATHER 1,599 over 17 records: 33,744 broadcast words, charged as store-and-forward at 32 words a cycle;
- GROUP_REDUCE_MCAST 448: 12,288 broadcast words;
- TOPK_MERGE 80.

The Qwen driver is remote SU.VOP operands.

These are the costs the B2 allocator and broadcast must remove. They are not B2's cost, but the -0.5 to -2 % claim
holds only after the following three fixes:

| # | driver | rule (binding for the compiler, exporter, cmdproc and coll) | residual exposure a record |
|---|---|---|---|
| F1 | SM.MATVEC reads x from a remote slice | Every MATVEC input x (and every vector read by more than one cluster: norms, residual, HC state) is allocated in **REPL**. The producer streams it into all 4 mirrors as it produces it: its own slice locally, the other 3 over the ring at 64 words a cycle a link. SMs read only their local mirror, so remote x reads = 0. The consumer gates per sector on the mirror scoreboard (R1). | tail of the last remote sector ≤ 1 farthest hop (~12-23 cycles), only when the producer is a remote cluster's record |
| F2 | remote SU.VOP operands (Qwen) | **Partition alignment.** All operands and the result of an elementwise SU / SFU / HC op use the SAME 4-way quadrant partition: element range `[q*N/4, (q+1)*N/4)` in slice q, or REPL. The exporter refuses a VOP whose operands are partitioned differently. Each SU quarter works on its own range, so remote SU operands = 0. Reductions inside a VOP use the section 4 ordered carry. | 0 for elementwise; one carry chain (3 hops, streamed) for a reduction |
| F4 (v0.7) | HC x writes would otherwise need a gather or remote read | **Transposed x for HC.** An HC record's x (the vector that its tiles stage into their x macros) goes in **REPL** (the local mirror) or in the quarter's **local region**, laid out TRANSPOSED: one VM sector = one half row of one x macro of one tile, i.e. tile lanes 16 m + 8 h .. 16 m + 8 h + 7 of x row r, as 8 fp32 words (bf16 in [31:16]). The sector index puts tile t, macro m, half h in local bank 4 t + 2 m + h (sector[2:0]), and the row in the upper bits, so the 8 banks drive the 8 lanes in parallel, one row a cycle. The exporter writes the transposed copy as the producer streams x (as F1 does for REPL), and refuses an HC record whose x is untransposed, remote, or bank-misaligned. With F2's partition, the HC quarter's x is then local or mirrored. | 0: every x lane is a local-bank sector |
| F3 | COLL.ALL_GATHER / GROUP_REDUCE_MCAST result broadcast is bandwidth-limited | Size the broadcast for the gather payload. (a) The width is 64 words a cycle a slice: 2,048-b data edges, more than 9 links x ~5.2 words a cycle of aggregate link arrival, so the broadcast never back-pressures the links. (b) It is a cut-through star from coll: every slice is 1 hop (coll sits on the spine between the 4 slices, ≤ ~3.5 mm, ≤ 8 stages). (c) It overlaps the gather arrival, so only the last flit's hop is exposed. | ≤ 1 hop (≤ ~10 cycles) + 1 sector |

**Re-estimate with the fixes.** Records a layer come from the measured vectors. The critical shares are those of
`tok_model.json`.

DS (a layer of 14,139 cycles, S2):

| source | exposed cycles a layer |
|---|---:|
| ALL_GATHER: 17 x 10 | 170 |
| REPL x tails: about 4 x-producing records x 12 | 48 |
| GROUP_REDUCE_MCAST + TOPK_MERGE: 2 x 10 | 20 |
| **total** | **≈ 238 = 1.7 %** (within the 2.0 % budget) |

- Critical (shares 0.70 / 0.51 / 1.0): about 175 cycles = 1.2 % → about 2,095 tok/s.
- With the SU local-lane saving (-1.5 %): about 2,110-2,125 tok/s, i.e. -0.7 % to +0.1 % against 2,121.8.
- Without F1-F3, the measured OLD-VM traffic gives +3.1-5.8k cycles a layer: 1,500-1,700 tok/s (-20 to -30 %). Do NOT
  adopt B2 without F1-F3.

Qwen (a layer of 35,253 cycles):

| source | exposed cycles a layer |
|---|---:|
| REPL x tails: 4 MATVEC inputs a layer x 12 | 48 |
| ALL_REDUCE broadcast: 2 x 10 | 20 |
| SU.VOP (F2) | 0 |
| **total** | **≈ 68 = 0.19 %** → about 943-945 tok/s (budget 93 = 0.27 %) |

**Acceptance (R4).** The harness reruns with the B2 allocator (`cluster` field per vector, REPL placement, F2
alignment) and the v0.2 broadcast parameters:

| parameter | value |
|---|---|
| `bcast_bits` | 2,048 |
| `bcast_hops` | 1 |
| `ring_link_bits` | 2,048 |
| `ring_hop_cycles` | 12 vertical / 11 horizontal (planned), measured in the RTL bench |

Pass criteria: DS ≤ 290 and Qwen ≤ 93 exposed cycles a layer, on every vector in `b2_traffic_1012`.

**TBD (compiler stream).** The REPL census (words of replicated vectors live at once), which confirms that
MIRROR_W = 32,768 holds them.

## 6. Contract v9 delta (proposal to the HBM die lead)

**D-B2-1.** Slot `hb_hgi_vm` is removed. The new slots are `hb_vms_{SW,SE,NW,NE}`, `hfd_hgi_vms`, 950.4 x 1,684.8 at
the section 1 positions, with clock entry on the spine face.

**D-B2-2.** The lgE/lgW nets and their stations are removed (`hb_stn_lgE_*` and `hb_stn_lgW_*`, plus the relays).
In their place:
- 4 local groups `hgi_lg<q>_*` (chain 4,460 b) with stations `hb_stn_lg<q>_{su,sfu,hc}`;
- ring nets `vring_<a>_<b>` (2,148 b plus a 4-b credit, 8 directed links);
- COLL broadcast `vcb_*` (1,088 + 2 b, 4 edges);
- ring-client taps `vrc_{cp,att,q,hce}_*` (4,452 b);
- x-load `vxl_<q>` (2,065 + 129 b);
- `vmap_<q>` (556 + 4 b; **v0.7: 1,200 + 16 b**, 8 HC x lanes, section 2a).

**D-B2-3.** Removed: `hgi_vmw_dma` (+ rdy / done), `hgi_vmr2_dma` (+ _r) and `hgi_vmw2_coll` (+ _r). `lq_<q>` /
`lr_<q>` re-terminate at `hb_vms_<q>`.

**D-B2-4.** The packet clients' `hgi_vmq_*` / `hgi_vmr_*` go to their nearest slice, and that slice forwards remote
addresses over the ring.

**D-B2-5.** Client port re-facing:
- SU / SFU / HC quarters each gain their local-group tap; the lgW tap was on SW only;
- cmdproc's `f/t_lgE{cp,att}_*` become `f/t_rc{cp,att}_*` (4,452 b, down from 17.8 kb);
- quant and hc_eng: likewise;
- `hb_vm_<q>` gains `f_xl_rdn` / `t_xl_rup`.

**D-B2-6.** HGI-1 (additive): the REPL window, word addresses 262,144-294,911. **v0.5 (HGI-1 change):** the HC
weight aperture moves from 262,144-327,679 to 294,912-360,447 (same 65,536 words); `docs/HBM_GENERIC_INTERFACE.md`
(the aperture paragraph, l. ~698) changes when contract v9 is adopted.

### 6a. Contract v9 proposal (v0.4, supersedes D-B2-2's ring and COLL widths)

| item | v9 |
|---|---|
| D-B2-1 slices | as above; each slice = 8 `ot_vms_bank` tiles (lane b ↔ bank b) + `ot_vms_hub` + CW stop + CCW stop, ONE netlist for all 32 bank tiles (bid / sid straps) |
| address | slice = `addr_word[17:16]` (= sec16 S[14:13]); REPL = range 262,144-294,911 (MIRROR_W 32,768); HC aperture = range 294,912-360,447 (v0.5, moved); decode by range with parameters `REPL_BASE/REPL_W/HCAP_BASE/HCAP_W`, never by bit 18. The bank tiles hold 65,536 mirror words, but growing MIRROR_W past 32,768 now also needs HCAP_BASE moved (a parameter change). The cmdproc slice map of `el1011-hbm-b2-cp` is confirmed |
| D-B2-2 ring | `vring_<a>_<b>`: 8 directed links (4 neighbour pairs x 2 directions), each 2,224 b wide channel + 2 x 2-b per-VC credits = 2,228 b as built in `ot_vms_rstop` (main 7cbecf842), 2 VCs, dateline at SW-SE; relays `ot_vms_relay` ≤ 500 um. Centre-line crossing 2 x 2 x 2,227 = 8.9 kb (8.6 kb in the GRT gate) |
| D-B2-2 COLL | `vcb_<q>`: star coll → each slice, 4 edges x (2,130 + 1) b as built in `ot_vms_star` (main 7cbecf842: v 1, sector_addr 13, data 2,048, mask 64, epoch 4; 1-b credit), cut-through (F3). Adds ≈ 2.1 kb over the gate's tree on the spine cut |
| D-B2-7 coll_tkm | KEEP `ot_hgi_coll_tkm` (16 `hgi_coll_tkm_tile` chain) inside `hb_coll`; result to the slices over `vcb`. `ot_hbm_index_global_order_mt` is the IDX id-merge (no value key, no top-k, no -0 / NaN / tie-to-lower-id rules), so it cannot do COLL.TOPK_MERGE (DS 9 / token, cross-die) |
| D-B2-8 wide lanes | slice-LOCAL only (RG 2 read groups, WG 2 write groups, DMA lane, COLL lane a bank tile). No remote wide reads: F1 (REPL x) and F2 (VOP partition alignment) make them unnecessary, and the exporter refuses a record that would need one. Packet clients (338 / 274 b) reach remote addresses through the ring |
| D-B2-9 VM8 | `hb_vm_<q>` abuts slice q (fixes the 3 link-domain clock / reset reach FAILs at (14.8-15.6, 18.9-20.0) mm, where the x-load pins crowd the tree nodes) |
| D-B2-11 IDX | `hb_hgi_idx` = wide client, slot 5 of slice SW's local group (KE 6 there), `ot_hgi_idx_index_w` 8-lane tap 2,065 / 17 / 129 / 2,241 b, a new SW-group chain station at the idx face; IDX-P placement (A / B / C in REPL; weights and O / R / D in SW-local). Packet port kept for TOPK / MERGE / OWNED |
| D-B2-12 lane credits (v0.8) | Wide lane g of every bank: queue depth = client credits = **4 + 2 x S_g**, S_g = relay stages each way from the slice face to the group's farthest client (contract relay count). RTL: `ot_vms_bank` per-lane parameters `RRS` / `WRS` (4 b a lane, default 3 → 10 entries; pointers wrap at the lane's own depth; overrun latches FAULT), `ot_vms_slice` passes them per group. The bank tile is hardened once at the defaults, so every slice uses S = 3 (the local group's HC station); a client may hold fewer credits (slower), never more. Clients built for 4 credits stay legal. Evidence: QDQ quarter `ot_hgi_qdq_q` (LQ 10 / LD 16) at S = 3: 4 credits 217 / 168 = 1.29x (credit-bound, 24 cyc a 16-beat record); slice default 10 credits **169 / 168 = 1.006x**; S = 1 161 / 168 = 0.96x; all exact, m1 / m2 FAIL. Bench mutant `tb_vms_slice -GBMUT=2` (queues one short of the credits) FAILs on bank FAULT. Cost: 6 more entries a lane queue (2 x 6 x 276 b write + 2 x 6 x 12 b read a bank). |
| D-B2-10 harness | R4 records per-sector t_arrive / t_need; `bcast_bits` 2,048, `bcast_hops` 1, `ring_link_bits` 2,048 both directions, ring hop 12 / 11 |

**Cut analysis (v9, study method of `hbm_die_phy_study_1012/cuts.py`).** The study's B2 spine cut (x = 15 mm, y 10-16)
is 39,863 b at 0.55 with the v0.1 ring (8,592 b) and tree (2,176 b). v9 adds ≈ +0.3 kb (ring) and ≈ +2.1 kb (star):
≈ 42.3 kb, **≈ 0.58**, inside the 0.55-0.60 target. Both full centre lines stay ≤ 0.08. The next die GRT runs with
the star and the v9 ring to confirm.

**Cut re-check v0.7 (HC x lanes 8 x 150 + 16 a quarter).** Script: `results/arch/hbm_b2_1012/cuts_v07.py`. It uses the same segment
count and capacity model as `cuts.py`, applied directly to the `r25gqn_b2` die network with the v9 ring (2,224 b) and the
COLL star (4 x 2,130 b). It also adds one perpendicular cut through every slice → HC quarter segment. Records are in
`cuts_v07.json` and `cuts_v07_y_extra.json`.

| cut (window) | v0.6 (556 + 4) | **v0.7 (1,200 + 16)** | vmap bits on the cut |
|---|---:|---:|---:|
| vmap_SE (x 19.3 mm) | 0.334 | **0.349** (worst slice → HC) | 1,216 |
| vmap_SW / NW / NE | 0.271 / 0.229 / 0.288 | 0.282 / 0.241 / 0.303 | 1,216 each |
| x 12 / x 13 hub | 0.238 / 0.358 | 0.251 / 0.370 | 2,432 |
| y 10 hub | 0.457 | 0.462 | 1,216 |
| x 15 spine | 0.317 | 0.317 | 0 |
| y 16 hub (x 12-18) | 0.764 | 0.770 | 1,216 |
| y 15.1 / y 16.9 hub (just outside the NW / NE slices) | | 0.455 / 0.276 | |

- The extra lanes add at most +0.015 on any cut, and every slice → HC cut stays ≤ 0.35.
- The one line above 0.60, **y = 16 mm, is not caused by the HC lanes**: it was 0.764 in v0.6. That line runs through
  the NW / NE slice bodies just below their centres (y 16,042). The centre-to-centre model therefore counts each slice's
  own lane-group and ring-client fan-out (`hgi_lgnw_*`, `vrc_cp/att_*`) on it, and only M9 is counted over the blocks.
  The real channel cuts on either side of the slices are 0.455 (y 15.1) and 0.276 (y 16.9).
- The worst channel cut is therefore **0.462 (y 10)**, inside the 0.55-0.60 target. No placement, width or relay change
  is needed for the HC lanes.
- The y = 16 artifact still points to one thing to confirm in the die GRT: the NW / NE slices must put their
  local-group and ring-client pins on the faces toward their peers (section 1), not route them through the slice.

## 7. Results

**Windowed hub GRT gate: PASS** (ot-epyc1tb `/srv/opentallas-scratch/claude/hbm-b2/w/`, same code bcf70d463 for both,
window 11-19 x 9-17 mm, k 16, 5 iterations, M4 / M5 0.5, `PYTHONHASHSEED=0`; `winov.py` on `gcell_usage.txt`):

| | r25gqn_pr8 (v8) | **r25gqn_b2** | change |
|---|---:|---:|---:|
| window overflow | 1,367,157 | **141,044** | **-89.7 %** (pass bar ≥ 50 %) |
| die overflow | 1,419,450 | 149,209 | -89.5 % |
| total wirelength (um) | 89,300,839 | 60,897,790 | -31.8 % |
| window overflow M4 / M5 / M6 / M7 / M8 / M9 | 83.5k / 457k / 479k / 141k / 149k / 57.2k | 2.4k / 23.1k / 47.8k / 21.7k / 19.8k / 26.3k | |
| hottest 2-mm bins (lower-left, mm) | (12,10) 309k, (14,12) 215k, (14,16) 177k | (14,14) 25.1k, (12,10) 21.6k, (14,16) 18.0k | |

The residual 141k is local: the (14,14) bin is the old VM site, now crossed by the ring-client taps and the COLL
tree, and (12,10) / (14,16) are the SW / NW slice faces. The die GRT with the v9 ring and star (section 6a) follows.
