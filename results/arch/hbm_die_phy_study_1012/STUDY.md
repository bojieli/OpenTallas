# HBM generic die (R25GQ): 4 PHYs or 2? Physical study, 2026-10-12

Owner question: the R25GQ die (4 HBM3E PHYs, ~4.8 TB/s, 32 SMs, 856.95 mm2) will not route on ASAP7 with open tools.
The last full die GRT (iteration 0, `grt_r25gqn_v10`) left 1,374,522 overflow, and 77 % of it sat in the hub,
x 12-18 mm / y 10-16 mm. Should we go to 2 PHYs a die and double the fleet?

**Answer: no. Adopt B2: keep 4 PHYs and make the die quadrant-local, VM included.** The congestion is not caused by the
PHY count. It comes from one central VM with ~62 kb of wide ports converging on the spine. Halving the die (C) keeps that
structure and adds die-to-die communication.

Every number below is recomputed by the scripts in this directory, on main `c17a02367` (contract v8, variant
`r25gqn_pr8`, `PYTHONHASHSEED=0`).

## 0. What lgE / lgW are, and what actually crosses the die

Evidence: `tools/hbm_accel_die_fp.py` lines 651 and 685-701, and `rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv`.

**The two buses.** Each is one VM lane group (`ot_hgi_vm_lanechain` / `lanearb` / `lanestation`). A group has 32 lanes,
lane b is bank b, and every hop is registered (≤ 504 um a stage). Its four chain buses are:

| bus | direction | bits | content |
|---|---|---:|---|
| rdn | VM → clients | 8,259 / 8,260 | 32 x {v, 256 b sector}, 1 KB/cycle of read data |
| rup | clients → VM | 515 / 516 | 32 x {v, sector 15}, read requests |
| wup | clients → VM | 8,963 / 8,964 | 32 x {v, sector 15, data 256, mask 8}, 1 KB/cycle of write data |
| wdn | VM → clients | 67 / 68 | per-lane write credits / done |

That is 17,804 b for lgW and 17,808 b for lgE.

**Clients** (time-shared by lanearb slots):
- **lgW** leaves the VM's W face. It serves the SU (slot 0, SW SU E face), the SFU (SW SFU N face) and HC (SW HC N face). It is activation and vector traffic for the SU, SFU and HC stage/drain.
- **lgE** leaves the VM's E face. Its KE = 4 slots are CP 0 (which also carries the SM.MATVEC x-load, D19), ATT 1 (the ATT record adapter in cmdproc, W face), quant 2 and HC_ENG 3. The chain runs VM → hc_eng (E) → back W to cmdproc → quant → ATT, so it crosses the spine's east edge twice.

**Other wide VM ports on the same spine.** All of these are on top of lgE and lgW:
- the DMA wide write `hgi_vmw_dma`, 8,960 b (32 x 280, loader → VM);
- the DMA wide read `hgi_vmr2_dma`, 8,257 b;
- the COLL W2 write `hgi_vmw2_coll`, 8,961 b;
- the HC aperture `hgi_vmap`, 2,224 b;
- the SM x trunks `xt*`, 2-4 kb.

Together that is about 62 kb of wide ports converging on one 2.07 x 2.07 mm block.

**Weights do not cross the die today.** Each PHY's svc band feeds only its own quadrant's 8 SMs. Across the die's
centre lines, the bus classes `weight`, `weight_req`, `kv_rows` and `phy_dfi` carry **0 bits**.

What does cross the vertical centre line (x = 16.49 mm), by bus class:

| class | bits |
|---|---:|
| hub | 57,050 (lane groups, VM ports, command buses) |
| x_trunk | 8,272 |
| link_flit | 4,480 |
| link | 3,896 |
| loader_mem | 2,580 |
| index_native | 2,374 |
| others | ≤ 1,800 each |

The horizontal centre line carries hub 95,327 b. Script: `wchk` logic in `cuts.py`.

**Correction to the premise.** The PHYs are not on four edges. They sit two on the S edge (SW, SE) and two on the N edge
(NW, NE), each 8.5 x 1.18 mm.

## 1. Worst cut: bits across a line vs usable tracks

**Method** (`cuts.py`, `post.py`, records `cuts_today.json` and `cuts_options.json`):
- Every die bus segment of the `r25gqn_pr8` network (33,610 buses, relay-staged) is drawn centre to centre.
- A segment counts on a cut when it spans the cut position and its other coordinate overlaps the cut's window.
- **Capacity.** ASAP7 pitches are M6/M7 64 nm and M8/M9 80 nm. Raw M6-M9 capacity across a 6 mm hub cut is 168,750 tracks.
- **Usable tracks:**
  - Over hard blocks, only the die layer counts (M8 for a vertical cut, M9 for a horizontal one; blocks own M1-M7 by the layer contract), at 75 % after the PDN.
  - In channels, M6 (or M7) at 75 % plus M4 (or M5) at 50 % (the D21 GRT model).
- **Target:** ≤ 0.55-0.60.

| cut (window) | A today bits | A util | B util | **B2** bits | **B2 util** | C, 32-lane groups | C, 16-lane groups |
|---|---:|---:|---:|---:|---:|---:|---:|
| x = 15.0 mm, spine (y 10-16; 5.25 of 6 mm under blocks) | 123,775 | **1.70** | 1.70 | 39,863 | **0.55** | 1.70 | 1.05 |
| y = 12.0 mm, hub (x 12-18) | 118,912 | 0.90 | 0.90 | 35,068 | 0.27 | 0.90 | 0.54 |
| y = 14.0 mm, hub | 92,818 | 0.79 | 0.79 | 37,650 | 0.32 | 0.79 | 0.51 |
| x = 14.4 mm, VM W face | 106,465 | 0.74 | 0.74 | 38,551 | 0.27 | 0.74 | 0.47 |
| x = 13.0 mm, hub | 71,928 | 0.69 | 0.69 | 21,934 | 0.21 | 0.69 | 0.40 |
| die centre, vertical (full height) | 83,221 | 0.14 | 0.14 | 41,909 | 0.07 | - | - |
| die centre, horizontal (full width) | 113,265 | 0.13 | 0.13 | 44,647 | 0.05 | - | - |

**Lane-group share at the worst cut (x = 15 mm).** Lane groups are 53.4 kb of the 123.8 kb. The VM's wide ports are
94.7 kb (76 %), which matches the GRT's 77 % hub share.

How each option's columns were derived:
- **A and B:** today's network. B moves no bits, because weights are already local.
- **B2:** A minus every VM-wide family, plus the cross-quadrant ring and the COLL broadcast tree.
  - The ring is 2 links across any line, each carrying 2,048 b each way plus control: 8,592 b.
  - The broadcast tree is 2 x 1,088 b.
- **C:** the C die is the W half plus the same spine. Its hub keeps the same window and the same central VM.
  - **C, 32-lane groups:** today's bits.
  - **C, 16-lane groups:** the VM-wide bits halved. Replicated-vector operations then run at half rate.

**Reading.** The die's capacity is ample: both full centre lines are under 0.15. The overflow is local, where the VM's
ports meet the spine.
- Only B2 removes those wide ports from the spine.
- C keeps them. Even with halved lanes the spine cut stays at about 1.05.
- **B2 residual cross-quadrant traffic:**
  - the ring, 8.6 kb on any line;
  - the COLL broadcast, 2.2 kb;
  - the existing narrow traffic: command dispatch (`hgi_*_cmd`, ~10 kb), SerDes links, index query/score, and SU quarter↔quarter 1,024 b links.

## 2. Area, utilisation, die and package counts

Area is the sum of contract v8 slots (`area.py`). Placed today: 426.1 of 856.95 mm2 (49.7 %).
- **Per-quadrant blocks** (SM, attention, PHY, SU, index grid, svc, HC, SFU): 350.8 mm2.
- **Singletons** (link endpoints and SerDes, host slab, hc_eng, VM, coll, cmdproc, index, quant, loader, MTP): 75.3 mm2.

| | A today | B | B2 | C (2 PHYs) |
|---|---|---|---|---|
| die | 856.95 mm2 | same | same, + about 4-6 mm2 of VM slices and ring stations | ~18 x 26 mm ≈ 470 mm2 (the W half plus the full spine) |
| placed / util | 426.1 / 49.7 % | same | ~431 / 50 % | 250.7 / ~53 % |
| DS-V4.1 at 1M | 96 dies (TP96 = 12 x 8) | 96 | 96 | **192** |
| Qwen3-8B | 4 dies (TP4) | 4 | 4 | **8** (TP8; TP4 halves the bandwidth: 535 tok/s) |
| DS fleet silicon | 82.3k mm2 | same | +0.6 % | ~90.2k mm2 (+10 %; placed +18 %, because the spine is duplicated) |

C can only use the 192 group by changing the HGI-1 contract: the legal group sizes are 1, 2, 4, 8 and 96, the reduction
tree has 8 inputs, and C would need 192 SPMD images.

## 3. Communication: hop count and its cost per token

Sources:
- the measured S2 composition: `results/arch/throughput_budget_20261010/budget.json`, DS 565,569 cycles = 2,121.8 tok/s fixed-RTL, target 2,208.1; Qwen 945.5 tok/s;
- each op's critical share from its measured +10 % elasticity;
- the measured TU collective model: `tools/hgi_sim/perf.coll_cycles`, `results/rtl/dshbm_1m_allmeasured_20261004` (377.6 ns a switch crossing; endpoint RTL measured);
- the in-package stage numbers from `tb_v41_stage_collective` (all-reduce tail 195-254 cycles, stage hop 419-473; memory `v41-collective-overlap-is-exposed`).

Script: `tok_model.py`, record `tok_model.json`. These are linear lower bounds on any slowdown, because an op's critical
share only grows with its cost.

| | switch crossings / DS token | on-die change | DS tok/s per user (A = 2,121.8) | Qwen tok/s (A = 945.5) |
|---|---:|---|---:|---:|
| A today | 98 (40 GROUP_REDUCE x 2 + 8 ROW + 9 TOPK + 1 ARGMAX); 584 ALL_GATHER stay in the 8-die package | - | 2,121.8 | 945.5 |
| B | 98 | none | 2,121.8 (0 %) | 945.5 |
| **B2** | 98 | ring hop ≈ +16 cycles on ≤ 722 records with a remote operand (+11.6k worst); local SU lanes save ~8 cycles x 1,356 SU.VOP (-8.5k) | **2,079 worst / ~2,110 net (-0.5 to -2.0 %)** | ≥ 943 (-0.3 %) |
| C, 16-die package (needs a 16-input tree; contract change) | 98 | none: half the SMs with half the bandwidth gives the same per-die time | 2,121.8 at 2x dies | 945.5 at 8 dies |
| C, 8-die package, one switch tier (256 x 200G radix) | 682 (every ALL_GATHER leaves the package: 389 → 955.5 cycles) | - | **≤ 1,504 (-29 %)** | - |
| C, 8-die package, 2-tier switch (192 endpoints > 128-port radix) | 682 crossings x 3 switches | - | **≤ 953 (-55 %)** | - |

C gives no compute speedup: each die has half the SMs, half the HBM bandwidth and half the weights. Its best case is
today's rate per user, on twice the dies. MTP (3,640 tok/s) scales the same way, because its verify step is
collective-bound.

## 4. Rework

### B (weight placement only)
B changes the compiler or the SM layout rule only. It needs no RTL change and no new closures, and it gains nothing,
because weights are already quadrant-local.

### B2 (quadrant-local die, distributed VM)

**RTL.** About 17 mm2 is re-closed (3.9 % of placed area: hgi_vm 4.3, vm 2.8, hc_eng 6.9, cmdproc 2.0, quant 0.5, loader 0.3).
- **`ot_hgi_vm_unit`, 4 instances.** Each is 8 banks and 8 lanes (NC / RP / W2 / WP already parametric; `ot_hgi_vm_core` / `wide_bank` bank count 32 → 8). Each slice holds 65,536 words, plus a mirror window for replicated vectors; size it at ~1.5x (98,304 words) for the DS HC residual (20,480 FP32).
- **Lane groups.** lgE and lgW are removed. Each quadrant gets a local group of 8 lanes (~4.45 kb) through `lanechain` stations to its own SU/SFU/HC quarter, attention tiles and SM x-trunks.
- **New `ot_hgi_vm_ring`.** A 2 x 2 mesh with credit links that handles mirror-write broadcast, remote-read forwarding and the COLL result broadcast. It is built from `ot_fwd_link_stage` / `lanestation`, with ≤ 504 um a stage.
- **cmdproc and record adapters.** The VM word address selects the slice (high bits) or the mirror window, and each record is dispatched to its slice. Central units (quant, hc_eng, idx, the ATT adapter, coll) become ring clients.
- **DMA.** The loader becomes per-quadrant at each svc band.
- **Cross-quadrant reductions** (norm sums, ...) are combined in the golden's chunk order to stay bit-exact.

**Compiler and record mapping.**
- The VM allocator places quadrant q's TP slice (the outputs of SMs 8q..8q+7, its heads and its SU operands) in slice q, and replicated vectors in the mirror window.
- SU templates are issued per slice.
- STRIPE4 is used only where an operand must span stacks (the DS HC weight rows); those rows go over the ring.

**Contracts.**
- HGI-1 is unchanged. VM stays one address space chosen by the compiler; slices and the mirror window are microarchitectural, and remote access is slower but legal.
- The die contract (`r25gq.json`) changes. The VM slot becomes 4 slices, the lgE/lgW nets are removed, and ring nets are added. That is a v9+ re-plan for the die lead; this study does not edit it.

**Reused unchanged.** SM x32, attention halves x64, svc x34, PHY x4, SU/SFU/HC tiles and quarters (their lgW tap ports are re-faced to the local group), index grids, coll, SerDes. That is about 85 % of placed area.

**Re-run.** The die GRT and the region routes.

### C (2 PHYs, half die)
- A new die floorplan and contract, a new die GRT and new packaging.
- Quadrant blocks are reused, but every spine block and the hub congestion remain.
- HGI-1 changes: group sizes 16/192, a 16-input COLL tree, 192 images, and SerDes/endpoint counts.
- The DS and Qwen programs are regenerated, and every collective bench is re-qualified.

## Recommendation: B2

B2 is the only option that removes the cause: about 95 kb of VM-wide ports converging on the spine. It brings the worst
cut from 1.70 to 0.55 at an unchanged die count and an unchanged HGI-1 contract, for a 0.5-2 % rate risk on DS. B alone
is a no-op. C doubles the dies and still leaves the spine at 1.05-1.70, and its communication costs -29 % to -55 % DS
tok/s per user unless the HGI group-size contract changes, in which case it only breaks even.

**Risk.** B2 rests on four things:
1. bit-exact cross-slice reductions in the golden's order;
2. VM slice capacity for the replicated vectors (mirror window size);
3. no record whose operands span quadrants landing on the critical path more often than the ≤ 722 a token assumed here;
4. the residual 0.55 at the spine cut. That is at the 0.55-0.60 target, not below it, so command-bus trimming or spine widening may still be needed.

The cut model is a centre-to-centre segment count, not a GRT. B2 must be confirmed with a windowed hub GRT (k = 16,
5 iterations) before the die lead re-plans.
