# HBM accelerator compute die: floorplan, die-level route, PDN/IR, priced wire stages (2026-10-05)

- **Tool:** `tools/hbm_accel_die_fp.py` (`plan | check | real | grt | ir | irwin | record | price | floor`, each with `--variant adopted | r8 | <JSON>`).
- **Pricing and records:** `tools/hbm_accel_die_price.py`. `floor` prices a plan's Manhattan floor without a route.
- **Method:** the same as the DS S81 and Qwen ROM full dies. Every block is an abstract with real ASAP7 signal pins on its facing edges, placed through the orientation-aware snap library and connected by every die-level net. Each case is measured in OpenROAD (`openroad/orfs:asap7lock`) on ot-epyc2:
  - rounds r1-r8 in `/srv/opentallas-scratch/claude/hbm-die-floorplan/cases`;
  - rounds r10-r14 in `/srv/opentallas-scratch2/scratch/claude/hbm-ds-die-grt/cases`.
- **Scope:** first release, for both models. Tape-out workstreams are out of scope.
- **Owner:** Claude (HBM-DS-DIE). The Codex route loop is withdrawn (`HANDOFF_CODEX.md`).
- **Final round:** r14b (`ADOPTED` in the tool). Every earlier round, including the failed and stopped ones, is kept in `feasibility.json`, keyed by round.

## 1. Floorplan (r14b)

| Item | Value |
|---|---|
| Die | 24,401.5 x 19,722.96 um = **481.3 mm2**, against the 858 mm2 reticle (376.7 mm2 margin). r8 was 503.7 mm2. |
| Placed footprint | 321.7 mm2 (66.8 % of the die) |
| Census | <ul><li>32 SMs (`ot_hbm_accel_sm_v` NC8/SUB4, 8 per stack)</li><li>4 HBM3E PHYs (real `ot_hbm3e_phy_v41x_aw30_e8p5`) and 4 stream services (32 PCs each)</li><li>SU, SFU and HC in four quarters</li><li>64 attention tiles in four per-stack scan quadrants of 16, each beside a quarter of the index path</li><li>spine: TU collective endpoint, cmdproc + pipelined issue, VM / activation-multicast root, barrier root, router + expert workgroup, quantisers, loader</li><li>9 real `ot_pdie_serdes` macros + 18 mm2 SerDes slab</li><li>host `ot_pdie_ucie` + 10 mm2 slab</li><li>208 forwarded-link / multicast / gather / control-distribution stations</li></ul> |
| Layout | <ul><li>The two N/S long edges each carry two PHYs. Each PHY has its stream service above it, then a 129.6 um channel, then the stack's 8-SM group (4 columns x 2 rows on a 259.2 um channel grid, with a 259.2 um channel between row 1 and the hub band on both N and S).</li><li>The W groups are mirrored (MY), so every group's activation (x) face looks at the spine.</li><li>The 7.2 mm hub band lies between the S and N groups. From W to E: scan quadrant, HC / SFU / SU quarters, spine, SU / SFU / HC quarters, scan quadrant. The four copies of each shared hub master are mirror images of the SW copy (SE MY, NW MX, NE R180).</li><li>The spine is 1.81 mm wide with 1.04 mm channels on both sides. Collective, VM and cmdproc have 1.4 mm faces. A 345.6 um equator channel splits the band S/N.</li><li>The SerDes sits at the centre of the S (5 macros) and N (4 macros) edges, in a 2.59 mm mid channel between the PHY pairs, with a 250.56 um routing gap beside each macro's io face.</li><li>The host link is on an 864 um E strip; its slab spans the die height.</li></ul> |
| Records | `floorplan.json` (block ledger with grades, geometry, Manhattan path bounds, lever areas, power, PDN plan, clock regions, the adopted variant), `floorplan.def`, `floorplan.svg`, `domains.sdc` |

**Block areas.** The source and grade of each are in `floorplan.json` `block_ledger`.

| Grade | Blocks |
|---|---|
| Measured | <ul><li>SM element 4.566 mm2: the sm_r2 placed context, 202 macros. The element route is OPEN.</li><li>SU lane array 11.96 mm2: placed lanes.</li><li>Router 0.086 mm2 + 0.1 mm2 workgroup estimate.</li><li>Barrier: routed.</li><li>Loader: slot 0.332 mm2.</li></ul> |
| Model ledger | SFU 8.819, HC 6.087, index 20.57 mm2 (`uarch_model.hbm_gpu_design(v41)`); SerDes 18 and host 10 mm2 reservations |
| Labelled estimates | attention tile 0.5 mm2 x 64, stream service 1.4 mm2/stack, TU endpoint 1.1, cmdproc 0.6, VM 1.5, quantisers 0.5, fused SU +3.59 mm2 |

**Area of the levers being built.** Each lever's area sits in the block named.

| Lever | Area | Location |
|---|---|---|
| Fused SU chains | 3.59 mm2 | SU quarters |
| Expert workgroup | 0.1 mm2 | router |
| Pipelined issue | 0.6 mm2 | cmdproc |
| Activation multicast | `floorplan.json` `lever_area_mm2` | multicast stations and x-trunk stations, sized as 4 stages x bus width of DFFs at 0.6 utilisation |

**Clock regions** (`domains.sdc`, `floorplan.json` `clock_region_list`):

- Every region is at most 5.0 mm across:
  - eight SM group halves (2 x 2 SMs);
  - four scan quadrants;
  - the centre column;
  - four stream services, on clk_hbm at 1.024 ns;
  - the link strips.
- Crossings are FIFOs: mesochronous hub <-> group (2 periods each, charged in the pricing), async hbm -> stream, 3:4 ratio CDC at the SU / SFU / HC.

**Power-grid plan** (`floorplan.json` `pdn`), unchanged from r8:

- M8/M9 straps at 0.48 um, aligned to the bump columns.
- Per-net coverage: 0.0878 over the SM field, hub and spine (strap pitch 4.90 um); 0.1639 over the stream services (2.77 um).
- Every core bump is a power bump, on a 63.64 um VDD/VSS lattice anchored to the die. PHY and link strips carry signal bumps.
- Peak in-phase load: 307 W, from densities that are labelled assumptions: SM 1.2 W/mm2, service 3.924, hub 1.05.

## 2. Die-level feasibility (measured, OpenROAD)

| Item | r14b | r8 | Verdict |
|---|---|---|---|
| Macro legality | 348 instances, 0 overlaps, 0 outside | 369, 0, 0 | PASS |
| On-track assert | 1,232,220 signal pins, 0 off-track | 1,208,318, 0 | PASS |
| Pin access | macroNoAp = 0 | 0 | PASS |
| Net endpoints without a pin | **0** | **128** (found in r11) | PASS |
| GRT k16, 5 iterations | overflow 33 | 218 | — |
| GRT k16, 50 iterations | <ul><li>**overflow 0** (converged after 19 extra iterations, 13 min 21 s)</li><li>max use/cap per 4 x 4 GCell window, baseline-subtracted: 1.0 on M6-M8; 0 windows above 1.0</li></ul> | overflow 128 (M7 37, M9 91), 78 min | **PASS** |
| PSM IR, **every window of the die** | <ul><li>worst interior rail to rail **25.41 mV**</li><li>all 88 load windows pass</li><li>99 windows in all. The other 11 hold no core load and no core bumps: the PHY edge row and the E host strip.</li></ul> | 25.41 mV, 85 load windows | PASS (budget 35 mV) |

**Round history.** Each change was forced by a measured failure. Failed and stopped rounds are kept in `feasibility.json`.

| Round | Change | Measured result |
|---|---|---|
| r1 | SerDes on E/W strips, VM / coll at the hub centre | <ul><li>Legality and pin access PASS</li><li>GRT i5 726, i50 198</li><li>IR at field coverage 0.0439: 9 top-row windows FAIL, worst 41.45 mV</li><li>Endpoint -> SerDes path 56 routed stages</li></ul> |
| r2 | SerDes moved to the N/S edge centres (endpoint -> farthest macro 56 -> 22 stages); field PG raised to 0.0878; IR windows anchored to the bump lattice | <ul><li>IR PASS, 25.44 mV</li><li>GRT i5 2,868, i50 830, at the spine faces</li></ul> |
| r3 | SU / SFU / HC split into quarters, so each stack quadrant's results land on its own side; 691 um spine channels | GRT i5 2,519, at the coll / VM faces |
| r4 | Every hub port spread evenly over its face | GRT i5 5,223 (worse; reverted) |
| r5 | 1,382 um spine channels | GRT i5 2,212 |
| r6 | Coll / VM pins spread | GRT i5 2,284. Root cause found: the VM's S face looked at the 142 um gap under it |
| r7 | Spine blocks escape only through their W/E faces | GRT i5 454, i50 417. Residual: the stream-service N face abutted the SM row-0 S face |
| r8 | 129.6 um channel between each stream service and its SM row 0 | GRT i5 218, i50 128 |
| r9 | Codex: r8 geometry with FastRoute seeds and CUGR | Stopped by Claude on take-over; superseded by r10 |
| r10 | <ul><li>**N rows mirror S.** All 128 r8 overflows sat on one line, y = 13,453 um: the N row 1 abutted the hub band, where the S side has a 259.2 um channel.</li><li>W groups MY.</li><li>x multicast entered at the inner column and chained outward. r8 entered at column 2, so the E groups' column-0 leaf doubled back two SM pitches.</li><li>Host strip 2,000 -> 864 um: 503.7 -> 481.3 mm2.</li></ul> | <ul><li>Legality, track and pin access PASS</li><li>GRT i5 17</li><li>r10b CUGR: 12,959 congestion units, counting via demand on the blocked M2-M5 pin layers. Not comparable; not adopted.</li><li>i50 stopped when r11 found the pin defect</li></ul> |
| r11 | <ul><li>**Port fix.** r1-r10 placed the four copies of each shared master R0 and took every pin from the SW copy. Quadrant-named ports of the other copies did not exist: 128 net ends had no pin, namely all tile chains and tile KV links, 3 of 4 result trunks and attention outputs, 6 KV / index rows, and 20 SU / SFU / HC links.</li><li>The E quarters' spine pins sat on the far face. That caused the r8 SU <-> endpoint detours: 53 stages against 4.</li><li>Copies are now mirrored and the ports named by role.</li></ul> | GRT i5: 436 (r11a), 253 (r11b, 1,037 um spine channels), 4,758 (r11c, 691 um). The SU E <-> W links, now connected, crossed the spine blocks: 402 M6 overflows. i50 stopped. |
| r12 | SU E <-> W links routed through the router/cmdproc and VM/barrier gaps of the spine. Variants: b = 1,037 um spine channels; c = 691 um; d = SM x / c pins centred; e = row 1 flipped + chained control | <ul><li>GRT i5: 14 / 17 / 4,864 / 10 / 8</li><li>**i50 0** on a, b, d and e</li><li>DS AR bound +46.7 / +45.0 / — / +45.2 / +46.9 us</li><li>c rejected</li><li>e rejected: floor +3 us, no gain in the bound</li></ul> |
| r13 | Every trunk gets a lane in the spine and hub-edge channels; SM pins centred; 1,037 um spine channels. Variants: b = 1,382 um channels; c = no pin spread on coll / VM | <ul><li>a: i5 24, **i50 0**, bound +43.18 us</li><li>b: i50 0, +43.31</li><li>c: i5 137, i50 not converged after 38 iterations (stopped, rejected)</li></ul> |
| **r14** | Trunk roots at the face end toward their trunk; b adds a 250.56 um SerDes io gap; c and d without pin spread | <ul><li>a: i50 0, +43.66 us</li><li>**b: i5 33, i50 0, +43.13 us (adopted)**</li><li>c, d: i5 140 / 137, i50 not converged after 34 iterations (stopped, rejected)</li></ul> |

## 3. Wire stages from routed lengths, priced into the compositions (`wire_stages.json`)

**Method** (unchanged from r8).

- **Routed length.** A path's routed length is the sum, over its forwarded segments, of the longest k16 bundle of that segment in the 50-iteration GRT. The stage bound is the sum of ceil(L / 430.56 um), the corridor-gate closing pitch.
- **Meso crossing.** A path between the hub and an SM group pays one meso crossing, 2 cycles.
- **Sensitivity.** `sensitivity_mean_bundle` uses the mean bundle length instead of the longest.
- **Limit.** These are bounds from routed length. They are not die-level STA.
- **MTP.** MTP tok/s now uses the gate's tau, 4.159 (owner 6-class blend). r8 used 3.8879. The step is tau-independent.

**Results** (DS 1M matched-reference gate: AR 474.808 us, MTP step 1,050.638 us; 1.2 GHz; r14b, GRT k16 i50).

| Basis | x multicast | control / barrier | SU <-> endpoint | endpoint <-> SerDes | Added to DS AR | DS gate AR (us) | DS AR tok/s | DS MTP tok/s (tau 4.159) | Qwen TP4 tok/s | Qwen TP2 tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Bound:** longest bundle of each routed segment | 64 | 47 | 4 + 6 | 22 | **+43.13 us (+9.1 %)** | 517.934 | 1,930.7 | 3,802.5 | 2,136.0 | 1,028.6 |
| Median bundle | 52 | 46 | 4 + 4 | 18 | +36.78 us | 511.591 | 1,954.7 | 3,824.6 | 2,138.9 | 1,029.3 |
| Mean bundle | 54 | 46 | 4 + 4 | 18 | +37.31 us | 512.116 | 1,952.7 | 3,822.8 | 2,138.9 | 1,029.3 |
| **Floor:** Manhattan between placed stations and pins | 43 | 38 | 3 + 3 | 12 | **+25.91 us (+5.5 %)** | 500.722 | 1,997.1 | 3,863.3 | 2,143.0 | 1,030.2 |

All stage counts above are one-way cycles at 1.2 GHz.

**Against r8.**

| Basis | r8 (503.7 mm2, i50 overflow 128) | r14b (481.3 mm2, i50 overflow 0) |
|---|---:|---:|
| Bound | +102.41 us: AR 1,732.4 tok/s, MTP 3,606.9 at tau 4.159 | +43.13 us: AR 1,930.7, MTP 3,802.5 |
| Median | +67.55 us | +36.78 us |
| Floor | +30.61 us | +25.91 us |
| Qwen TP4 / TP2, bound | 2,108.9 / 1,022.3 | 2,136.0 / 1,028.6 |

- **Unpriced baselines.** Before any die wire is charged, the compositions stand at DS gate AR 2,106.1 tok/s and MTP 3,958.5 tok/s (tau 4.159); Qwen TP4 2,154.2 and TP2 1,032.8 tok/s.
- **r8 under-counted some paths.** Its records had no pin at 128 net ends (§2), so those nets were never routed. The result-gather, attention-out and KV-row paths of three stacks were priced from the SW stack alone.
- **Main terms at the bound** (per token, DS):
  - x multicast 15.5 us (291 serial loads x 64);
  - endpoint <-> SerDes 11.2 us (305 x 2 x 22);
  - barrier tree delta 10.3 us (343 x (2 x 47 - 58));
  - expert fetch 2.3 us;
  - SU <-> endpoint 2.2 us (r8: 22.7 us);
  - KV / index / attention-out 1.6 us.
- **What remains between the bound and the floor.** It is not overflow; GRT i50 is clean. Three things remain:
  - **Quantisation.** Stations sit every 4 x 430.56 um. A bundle that routes a 1.6-1.7 mm segment 100-600 um long pays a fifth stage. This is the multicast and control trunks, 4 -> 5-6 stages per segment.
  - **Pin spread.** On the multicast leaf and the SerDes macro face the pins span about 1 mm and 2.25 mm. The longest bundle of the last link segment routes 2.6 mm against 0.38 mm Manhattan, 7 stages against 1.
  - **Star control leaves.** These run from column 2 to the outer columns' c faces: 3.9-4.0 mm routed, 10 stages against 7.
  - Two structural variants were tried against these and rejected on the measured route: closer stations (floor +4 us) and a chained control comb with row-1 flip (r12e, floor +3 us).
- **Not done (architectural, no length gain under this pricing).** A hierarchical multicast/barrier tree with four quarter roots and a regional relay. Stage counts follow routed length, and a relay does not shorten the root -> farthest SM distance.
- **Verdict.** On a clean route, die-level wire costs **+5.5 % (floor) to +9.1 % (bound)** of the DS AR token. r8 put it at +6.4 % to +21.6 %.

**How each class is charged per token** (counts from the matched-reference walk):

| Class | Charged |
|---|---|
| x multicast | Once per serial x load: 291 first-not-resident loads, of 571 load phases |
| Barrier | Arrive + release over the routed control tree, in place of the 29 + 29 wire cycles inside the measured 62-cycle barrier RTL (343 barriers) |
| Result gather | Rides with the arrive, so it is exposed only beyond the barrier round trip (0) |
| SU <-> endpoint | Once per collective (265) |
| Endpoint <-> farthest SerDes | Both ways per switch crossing (305). The TU vendor budget excludes the on-die run. |
| Expert fetch | Router -> service + service -> farthest SM (40) |
| KV / index rows | Service -> scan quadrant |
| Attention out | Tile row -> SU |

The MTP step carries the same traversals.

**Qwen 8K.**

- The HA8 W12 vehicle keeps its measured spine/tile tree (BD31) inside its cycles.
- Priced on this die: endpoint <-> SerDes and SU <-> endpoint per crossing, plus the service -> compute KV first access per layer: 4,734 cycles per token (TP4 +0.85 %, TP2 +0.41 %).
- **Caveat.** The W12 tile die (1,536 tiles, about 382 mm2 of tile core and 421.5 MiB of SRAM residence) is not the SM die. Its own floorplan is the Qwen HBM tile die (separate Claude stream). The Qwen figures here are a transfer of this die's collective and service geometry.

## 4. Still modelled or open

- **Element views.** These are sized placeholders, not hardened views: SM element (route OPEN), SU, SFU, HC, attention tile, index quarter, TU endpoint, cmdproc, VM, stream service. When an element is hardened, its owner hands the LEF to Claude, who re-runs the round.
- **Stage counts.** They are bounds from GRT routed length, not detailed-route STA. The block-level SS/FF closures belong to their owners.
- **Power densities and IR.** The power densities are assumptions. IR uses peak in-phase density over each block, with 20 um load cells.
- **Collective term.** The TU PHY/switch/cable vendor budget and the striping tail are unchanged from the matched reference.

## Replay

```
python3 tools/hbm_accel_die_fp.py plan                       # floorplan.{json,def,svg}, domains.sdc (adopted variant)
python3 tools/hbm_accel_die_fp.py check                      # legality, pin clashes, Manhattan bounds
python3 tools/hbm_accel_die_fp.py floor [--variant JSON]     # plan-time Manhattan floor priced (no route)
# on the compute host (grt_round.sh <round> <variant> / ir_round.sh <round> <variant> in the scratch root):
python3 tools/hbm_accel_die_fp.py real --work C/a_real
python3 tools/hbm_accel_die_fp.py grt  --work C/b_k16_i50 --k 16 --iters 50   (+ --iters 5, --empty for the baseline)
for w in $(python3 tools/hbm_accel_die_fp.py irwin); do python3 tools/hbm_accel_die_fp.py ir --work I/c_$w --window $w; done
tools/hbm_accel_die_run_case.sh <case> run.tcl run.log <cpus> <mem_gb>
python3 tools/hbm_accel_die_fp.py record --work <cases root>     # merges into feasibility.json, earlier rounds kept
python3 tools/hbm_accel_die_fp.py price  --work C/b_k16_i50
python3 tools/hbm_accel_die_fp.py <mode> --variant r8         # the r1-r8 geometry
```
