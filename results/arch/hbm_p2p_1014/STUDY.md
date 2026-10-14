# HBM die R25GQ: peer-to-peer / quadrant-local hub? Architecture study, 2026-10-14

Owner direction (10-14): make the HBM accelerator peer-to-peer like a GPU (SM + L2 slices over a distributed fabric) or
Da Vinci, with no central hub that many unit types converge on. Only small data (scalars, partial sums, reductions,
control) should cross quadrants. This is a study before RTL. **It is a proposal: the contract is not changed.**

Inputs:
- the v13 window model (`hbm_r25gq_windows.py --dump-model`, branch `claude/hbm-native-die-1013` 31a02920b, 06:28 PT; pickle
  `EPYC1:/srv/opentallas-scratch/claude/hbmdie-v13/win14/v13.pkl`);
- the B2 spec (`results/arch/hbm_b2_1012/SPEC.md`, v0.8);
- the prices in `results/arch/token_path_20261009`: DS 549,131 cycles = 2,185.3 tok/s; Qwen 1,258,136 cycles = 953.8 tok/s.

Scripts (in this directory):
- `traffic.py`: the logical-bus traffic matrix, giving `buses_v13.json`;
- `groups.py`: the matrix by family, giving `groups_v13.json`;
- `scen.py`: the scenarios, giving `scen_*.json` and `check_*.log`.

`scen.py` reproduces the committed v13 window verdict exactly: FAIL 86/21/4, worst 1.351.

## 1. Traffic matrix: what loads the hub today (v13)

Hub demand is wire bit·mm inside x 11.0-21.5 / y 7-20 mm. The hot window is x 12-15 / y 14-17 mm. Bits are per-cycle
bus widths, summed over the family.

| family | producer → consumer | bits | hub | hot | why it crosses |
|---|---|---:|---:|---:|---|
| SU ↔ VM8 (`hb_su_q_vm`, `hb_vm_su_q`) | SU q ↔ VM8 quarter q | 8 x 2,048 | 14.1 % | 14.6 % | **placement**: the VM8 union (25 closed tiles) sits in the spine N (y 16.9-18.9). The SW/SE SUs are 8 mm away, with 22-43 relay stages |
| lane groups `hgi_lg<q>` | slice q → its SU / SFU / HC stations | 94,060 | 13.1 % | 11.6 % | local by design (B2). They sit in the hub only because the quadrant units do |
| VM ring `vring` | slice ↔ slice | 8 x 2,148 | 10.7 % | 9.0 % | **data**: REPL mirror, remote reads and RED_CARRY. This is the peer fabric |
| link chains `lk_lk` | COLL (spine centre) ↔ 9 `lk_ep` (N / S edges) | 9 x 1,122 | 8.1 % | 9.9 % | **architecture**: one COLL engine for 9 links. Each chain is 20-31 stages |
| cmdproc fan-out | cmdproc → SU_SW 2,198, hgi_idx 2,075, HC_SW 939, `ct_q` 4 x 899 | 17,871 | 7.0 % | 5.4 % | architecture (central dispatch) |
| x trunks `xt` / `xl` / `xh` | VM8 → 32 SMs | 107,376 | 6.4 % | 7.6 % | **placement**: trunks run from the spine N to the S SM arrays (`xt_SW` 39 stages) |
| SU ↔ SU | SU q ↔ SU p | 8 x 1,024 | 6.1 % | 2.1 % | data (cross-quadrant SU exchange). The width needs an audit |
| DMA loader `lw` / `lq` / `lr` | svc q (PHY edge) ↔ dbk / slice q | 11,848 | 6.0 % | 4.7 % | local (already per quadrant) |
| TKM `tkm_*` | COLL ↔ TKM cluster (NW HC column) | 2,773 | 4.2 % | **16.5 %** | **placement**: the 32-tile cluster did not fit the spine. It sits 7.6 mm from COLL, with ~18+ stages each way, on every delivered flit |
| x load `vxl` | slice q → VM8 q | 4 x 2,194 | 4.0 % | 4.4 % | placement (the VM8 site) |
| IDX | quadrant score grids ↔ spine selector | 75,347 | 3.8 % | 0.3 % | data (global top-k) |
| ring clients `vrc` | cmdproc CP / ATT, quant, hc_eng ↔ one slice | 13,548 | 3.2 % | 4.0 % | architecture (central units) |
| SU ↔ COLL | SU q ↔ COLL | 6,576 | 2.6 % | 2.7 % | architecture (central COLL) |
| COLL broadcast `vcb` | COLL → slices (tree) | 4,360 | 1.8 % | 1.4 % | architecture |
| VM8 cross `hb_vm_x_*` | VM8 quarter ↔ neighbour quarter | 8 x 4,776 | ~0 | ~0 | **data**: one x row store split by address. The quarters are abutted, so these wires are short. They are why VM8 cannot simply be pulled apart (see VM below) |

## 2. Quadrant-local alternative and what must still cross

- **COLL (link chains, TKM, SU↔COLL, broadcast).**
  - Four COLL engines, each at its quadrant's link edge. Links are rail-aligned 3/2/2/2: SW S0-S2, SE S3-S4, NW N0-N1,
    NE N2-N3. The TU endpoint already stripes over a switch; the switch must route by (die, quadrant).
  - The payload is element-partitioned: rail q carries the elements of slice q. Element-wise reductions keep their
    rank-order tree, so they stay bit-exact.
  - TKM becomes 4 x 8 of the closed `ot_hgi_coll_tkm_tile`, each group beside its COLL.
  - Each COLL delivers to its own slice. The other 3/4 of a gathered vector reaches the other slices as REPL writes on the
    ring. B2 F2/F3 sizing holds: 128 words a cycle inbound per slice, against 48 needed.
  - What still crosses: a COLL peer ring of 256 b each way (sequencing, credits, top-k / argmax partial streams).
    TOPK_MERGE needs a final 4-way merge of 512-entry partial lists, about 74 kb a merge. On the slice ring that is about
    36 cycles plus one hop.
- **VM8 (SU↔VM8, x trunk, x load).** There are two steps.
  - **(A) VMC, placement only.** Move the VM8 union into the spine void at the die centre (14.7-16.1 x 12.5-14.5 mm).
    cmdproc moves up 176 µm. The closed tiles stand and the cross buses stay abutted.
  - **(B) VMX, RTL.** Each quarter becomes an independent x root beside its slice and holds the full x, fed from its local
    REPL copy. The cross-quarter buses are removed, and x replication goes over the ring, as B2 already budgets for x.
  - Moving the quarters apart *without* VMX is worse: scenario VM below.
- **SU.** It is already four quadrant units (B2 STRIPE4).
  - The SU↔SU links (8 x 1,024 b) should carry only the bit-exact reduction carry (ring RED_CARRY, B2 §4).
  - They should be narrowed to ≤ 256 b, or removed, once the SU owner names the record that needs 1,024 b. This is not
    modelled here.
- **Not moved.**
  - cmdproc stays a central sequencer. Per-quadrant dispatchers gave no window gain in this model (COLL+CP is worse than
    COLL). The 2 kb `hgi_su_cmd` / `hgi_idx_cmd` widths should be audited.
  - The IDX selector stays central. Global top-k is a true reduction, and IDX is 0.3 % of the hot window.
  - quant and hc_eng stay central. They are small ring clients.
  - The lane groups, DMA, HC and SM paths are already local.

## 3. Inter-quadrant fabric

The fabric is a **2 x 2 ring, not a mesh**: a mesh's two diagonals would cross the very centre this study empties. Its links:
- the slice ring, 2,148 b a direction (built);
- the COLL peer ring, 256 b;
- the SU carry, ≤ 256 b.

All of them use registered relays ≤ 500 µm apart.

Hop stages:
- B2 §5 plans 11-12 stages a hop, and 23 for the diagonal.
- v13 routes them at 14 (SW-NW), 17 (NW-NE), 21 (SE-NE) and 29 (SW-SE). These are detours around the spine; SW-SE
  shortens once COLL leaves the spine middle.

Cuts (`hbm_r25gq_cuts.py` capacity; all ≤ 0.55 with margin):

| scenario | x = 16.49 hub (y 7-20) | y = 12.99 hub (x 11-21.5) | x full | y full |
|---|---:|---:|---:|---:|
| v13 | 63,508 b, 0.170 | 48,840 b, 0.209 | 0.118 | 0.081 |
| VMC + COLL | 44,779 b, 0.120 | 28,995 b, 0.143 | 0.081 | 0.056 |
| VM + VMX + COLL | 29,408 b, 0.079 | 26,094 b, 0.112 | 0.055 | 0.051 |

**Window check** (the binding criterion: limits 0.90 / 0.75 / 0.60; over-limit windows centred in the hub, and the worst
hub window):

| scenario | 500 µm | 1,000 µm | 2,000 µm | hub bit·mm | hot bit·mm |
|---|---|---|---|---:|---:|
| S0 v13 as committed | 48, 1.351 | 12, 1.013 | 4, 0.816 | 1,094k | 160k |
| VM (quarters moved, cross buses kept) | 138, 2.102 | 43, 1.527 | 5, 0.800 | 1,102k | 144k |
| VMC (VM8 union to the centre void) | 63, 1.482 | 13, 1.140 | 0, 0.583 | 943k | 131k |
| COLL (quadrant COLL + TKM + rails) | 39, 1.128 | 4, 0.803 | 1, 0.607 | 957k | 119k |
| COLL + CP (plus dispatchers) | 52, 1.385 | 2, 0.803 | 1, 0.662 | 923k | 113k |
| VM + VMX | 19, 1.268 | 7, 0.881 | 0, 0.569 | 865k | 115k |
| **VMC + COLL** (step 1) | **23, 1.073** | **3, 0.824** | **0, 0.373** | 806k (-26 %) | 91k (-43 %) |
| **VM + VMX + COLL** (step 2) | **12, 1.078** | **1, 0.773** | **0, 0.438** | 727k (-34 %) | 75k (-53 %) |

Caveats:
- Rewired buses are modelled as direct L-shaped hops from box to box, with no detours. Untouched buses keep their v13
  pin-to-pin relay routes, and no PathFinder rounds are applied. The comparison is pre-PathFinder against the v13 S0
  (86/21/4), not against v13 PathFinder round 3 (11/1/0 worst 1.096, reached by detours into the S SM channels).
- The residual worst window (x 13.2-13.7 / y 15.8-16.3) is NW-local: lane group plus `lw_NW` in the 43-µm slice
  channel. It needs a local station or channel fix.
- The non-hub SM / IDX score-grid windows (for example x 24.6 / y 1.3, 0.82 at 1,000 µm) are the same in every scenario.

## 4. Costs

**Area.**
- Added, gross:
  - 4 COLL cores instead of 1: +1.5-2.6 mm²;
  - 3 more TKM sequencer strips: +0.8 mm²;
  - with VMX, a full x row store in each quarter: +0.5-1.0 mm².
- Freed:
  - the `hb_coll` spine slot, 2.19 mm². It sits next to `idx_selector`, so IDX can grow into it;
  - the `hb_tkm` site, 4.16 mm²;
  - with VMX, the spine N slot, 2.80 mm².
- Net placed area is about +0 to +1 mm² on a fixed 856.95 mm² die. This does not solve the IDX shortfall (38.2 vs
  21.2 mm² of slots); it frees about 2 mm² next to the selector.

**Cycles.** These are modelled, not priced; RTL measurement is needed. The deltas are against the v13 central floorplan,
whose relay stages are NOT in the price.

| term | DS cycles / token | Qwen cycles / token |
|---|---:|---:|
| link tx + rx chains, about 19 stages each way saved, on 511 critical collectives (Qwen 73) | -19.4k | -2.8k |
| TKM round trip, about 2 x 16 stages saved | -16.4k | -2.3k |
| x fill SU → VM8 → SM, about 30 stages saved (VMX only), on 244 critical SM.MATVEC (Qwen 145) | -7.3k | -4.4k |
| remote quarter of a COLL result over the ring instead of the star (≤ 7 a gather) | ≤ +3.2k | n/a (all-reduce is element-local) |
| TOPK_MERGE 4-way final merge | +0.5k | 0 |
| x over the ring for small x, diagonal exposure | ≤ +2.5k | ≤ +1.6k |
| rail link time, if links bind (3/2/2/2 vs 9 shared) | ≤ +3.6k | small |
| **net, worst-case adders** | **-28.5k (step 1: COLL + VMC) / -33.3k (step 2: + VMX)** | **about -7.9k** |

- DS: these stages put the central v13 die 6.5-7.8 % of token cycles above the price (35.8-43.1k of 549,131). P2P avoids
  most of that: +5.5 % (step 1) or +6.5 % (step 2) tok/s against v13-central with worst-case adders, and up to +8.5 %
  with none.
- Qwen: about +0.6 %. Qwen is SM / HBM bound. The HBM price (99 B/cycle/SM, physical bandwidth) is unchanged, because
  weights are already quadrant-local (B2 R2).
- **Not claimed** (upside, needs RTL): 4 endpoints each serialise 1/4 of the flits (the price's in-package term is
  13.2 cycles a flit a rank), and SU STRIPE4 across 4 SUs.

## 5. Recommendation: adopt partially, in two steps

1. **Step 1, contract v14 proposal.** Quadrant COLL (4 engines at the link edges, links rail-aligned 3/2/2/2, TKM 4 x 8,
   256-b COLL peer ring), plus the VM8 union moved into the centre void.
   - Result: hub windows 48/12/4 → 23/3/0 (worst 1.073), hot demand -43 %.
   - RTL: the COLL partition, re-closed. COLL already fails its price (+9.55 %), and its selector is at -622 ps.
   - Reused: `lk_ep` x 9, the SerDes slabs, `ot_hcoll_port` x 9, TKM tiles x 32 (closed), the slices and ring, and the
     VM8 25 tiles (moved, not re-routed).
   - New masters: `coll_q` (two port counts, so two masters, each hardened once) and the `tkm_q` cluster parent
     (hardened once, mirrored E).
2. **Step 2.** VM8 VMX: independent quadrant x roots beside the slices, x over the REPL ring.
   - Result: hub windows → 12/1/0 (worst 1.078), hub demand -34 %, hot -53 %.
   - It needs an RTL variant of the closed VM8 union: its cross and face tiles are re-closed.
3. **Not adopted:** per-quadrant cmdproc, the IDX selector, quant and hc_eng. SU↔SU narrowed after an audit.

**Owner decisions needed:**
- (a) Links 3/2/2/2 (two COLL masters), 2/2/2/2 (drop one link, -11 % raw link bandwidth), or 3 x 4 (+3 link endpoints
  and SerDes, about +8 mm²).
- (b) Package switch routing by (die, quadrant).
- (c) VMX as an RTL change of a closed union.
