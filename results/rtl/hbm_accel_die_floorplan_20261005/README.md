# HBM accelerator compute die: floorplan, die-level route, PDN/IR, priced wire stages (2026-10-05)

- **Tool:** `tools/hbm_accel_die_fp.py` (`plan | check | real | grt | ir | irwin | record | price`).
- **Pricing and records:** `tools/hbm_accel_die_price.py`.
- **Method:** the same as the DS S81 and Qwen ROM full dies. Every block is an abstract with real ASAP7 signal pins on its facing edges, placed through the orientation-aware snap library and connected by every die-level net. Each case is measured in OpenROAD (`openroad/orfs:asap7lock`) on ot-epyc2 (cases in `/srv/opentallas-scratch/claude/hbm-die-floorplan/cases`).
- **Scope:** first release, for both models. Tape-out workstreams are out of scope.
- **Final round:** r8. Every earlier round is kept in `feasibility.json`, keyed by round.

## 1. Floorplan (r8)

| Item | Value |
|---|---|
| Die | 25,537.7 x 19,722.96 um = **503.7 mm2**, against the 858 mm2 reticle (354 mm2 margin) |
| Placed footprint | 321.8 mm2 (63.9 % of the die) |
| Census | <ul><li>32 SMs (`ot_hbm_accel_sm_v` NC8/SUB4, 8 per stack)</li><li>4 HBM3E PHYs (real `ot_hbm3e_phy_v41x_aw30_e8p5`) and 4 stream services (32 PCs each)</li><li>SU, SFU and HC in four quarters</li><li>64 attention tiles in four per-stack scan quadrants of 16, each beside a quarter of the index path</li><li>spine: TU collective endpoint, cmdproc + pipelined issue, VM / activation-multicast root, barrier root, router + expert workgroup, quantisers, loader</li><li>9 real `ot_pdie_serdes` macros + 18 mm2 SerDes slab</li><li>host `ot_pdie_ucie` + 10 mm2 slab</li><li>229 forwarded-link / multicast / gather / control-distribution stations</li></ul> |
| Layout | <ul><li>The two N/S long edges each carry two PHYs. Their stream service sits above the PHY, then a 129.6 um channel, then the stack's 8-SM group (4 columns x 2 rows on a 259.2 um channel grid).</li><li>The 7.2 mm hub band lies between the S and N groups. From W to E: scan quadrant, HC / SFU / SU quarters, spine, SU / SFU / HC quarters, scan quadrant. The spine is 1.81 mm wide with 1.38 mm channels on both sides; collective, VM and cmdproc each have 1.4 mm faces. A 345.6 um equator channel splits the band S/N.</li><li>The SerDes sits at the centre of the S (5 macros) and N (4 macros) edges, in a 2.59 mm mid channel between the PHY pairs.</li><li>The host link is on the E strip.</li></ul> |
| Records | `floorplan.json` (block ledger with grades, geometry, Manhattan path bounds, lever areas, power, PDN plan, clock regions), `floorplan.def`, `floorplan.svg`, `domains.sdc` |

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
| Activation multicast | 0.576 mm2 | multicast stations and trunk stations, sized as 4 stages x bus width of DFFs at 0.6 utilisation |

**Clock regions** (`domains.sdc`, `floorplan.json` `clock_region_list`):

- Every region is at most 5.0 mm across:
  - eight SM group halves (2 x 2 SMs, 4.67 mm);
  - four scan quadrants (4.97 mm);
  - the centre column;
  - four stream services, on clk_hbm at 1.024 ns;
  - the link strips.
- Crossings are FIFOs: mesochronous hub <-> group (2 periods each, charged in the pricing), async hbm -> stream, 3:4 ratio CDC at the SU / SFU / HC.

**Power-grid plan** (`floorplan.json` `pdn`):

- M8/M9 straps at 0.48 um, aligned to the bump columns.
- Per-net coverage: 0.0878 over the SM field, hub and spine (strap pitch 4.90 um); 0.1639 over the stream services (2.77 um).
- Every core bump is a power bump, on a 63.64 um VDD/VSS lattice anchored to the die. PHY and link strips carry signal bumps.
- Peak in-phase load: 307 W, from densities that are labelled assumptions: SM 1.2 W/mm2, service 3.924, hub 1.05.

## 2. Die-level feasibility (measured, OpenROAD)

| Item | r8 | Verdict |
|---|---|---|
| Macro legality | 369 instances, 0 overlaps, 0 outside | PASS |
| On-track assert | 1,208,318 signal pins, 0 off-track | PASS |
| Pin access | macroNoAp = 0 | PASS |
| GRT k16, 5 iterations | overflow 218 | iterate |
| GRT k16, 50 iterations | <ul><li>**overflow 128** (M7 37, M9 91)</li><li>max use/cap per 4 x 4 GCell window, baseline-subtracted: 1.00 on M6-M8, 0.95 on M9</li><li>0 windows above 1.0</li></ul> | **NOT 0: route iterations remain (handed off)** |
| PSM IR, **every window of the die** | <ul><li>worst interior rail to rail **25.41 mV**</li><li>all 85 load windows pass</li><li>92 windows in all. The other 7 hold no core load and no core bumps: the PHY edge row and the E host strip.</li></ul> | PASS (budget 35 mV) |

**Round history.** Each change was forced by a measured failure. Failed verdicts are kept in `feasibility.json`.

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

## 3. Wire stages from routed lengths, priced into the compositions (`wire_stages.json`)

**Method.**

- **Routed length.** A path's routed length is the sum, over its forwarded segments, of the longest k16 bundle of that segment in the 50-iteration GRT. The stage bound is the sum of ceil(L / 430.56 um), the corridor-gate closing pitch.
- **Meso crossing.** A path between the hub and an SM group pays one meso crossing, 2 cycles.
- **Sensitivity.** `sensitivity_mean_bundle` uses the mean bundle length instead of the longest.
- **Limit.** These are bounds from routed length. They are not die-level STA.

**Results** (DS 1M matched-reference gate: AR 474.808 us, MTP step 1,050.638 us, tau 3.8879; 1.2 GHz).

| Basis | x multicast | control / barrier | result | SU <-> endpoint | endpoint <-> SerDes | Added to DS AR | DS gate AR (us) | DS AR tok/s | DS MTP tok/s | Qwen TP4 tok/s | Qwen TP2 tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Bound:** longest bundle of each routed segment, i50 | 135 | 81 | 57 | 53 + 50 | 25 | **+102.41 us (+21.6 %)** | 577.218 | 1,732.4 | 3,371.8 | 2,108.9 | 1,022.3 |
| Median bundle, i50 | 81 | 64 | 46 | 24 + 38 | 20 | +67.55 us | 542.362 | 1,843.8 | 3,477.0 | 2,122.9 | 1,025.5 |
| Mean bundle, i50 | 86 | 65 | 47 | 29 + 34 | 21 | +70.03 us | 544.841 | 1,835.4 | 3,469.3 | 2,122.1 | 1,025.3 |
| **Floor:** Manhattan between placed stations and pins | 50 | 39 | 38 | 4 + 4 | 16 | **+30.61 us (+6.4 %)** | 505.418 | 1,978.6 | 3,595.8 | 2,140.5 | 1,029.6 |

All stage counts above are one-way cycles at 1.2 GHz.

- **Unpriced baselines.** Before this work the compositions stand at DS gate AR 2,106.1 tok/s and MTP 3,700.5 tok/s; Qwen TP4 2,154.2 and TP2 1,032.8 tok/s.
- **Why the bound sits far above the floor.** The 50-iteration GRT trades length for overflow, and the stage bound follows the worst bundle. Examples:
  - the NE SU quarter <-> endpoint bundles run 22.7 mm against a 4-stage Manhattan;
  - the x trunk's worst bundle against its median: 135 vs 81 stages.
- **Main terms of the bound** (per token, DS): x multicast 32.7 us (291 serial loads x 135); barrier tree delta 29.7 us (343 x +104); SU <-> endpoint 22.7 us; endpoint <-> SerDes 12.7 us; expert fetch 2.8 us; KV / index / attention-out 1.7 us.
- **Verdict.** Die-level wire is not free on a 25.5 x 19.7 mm die. It costs **+6.4 % (floor) to +21.6 % (bound)** of the DS AR token. The x-multicast depth was unpriced before; the barrier was priced on the old 815 mm2 GPU floorplan at 29 + 29.

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
- Priced on this die: endpoint <-> SerDes and SU <-> endpoint per crossing, plus the service -> compute KV first access per layer.
- **Caveat.** The W12 tile die (1,536 tiles, about 382 mm2 of tile core and 421.5 MiB of SRAM residence) is not the SM die. One die cannot carry both measured vehicles. This floorplan is the DS SM organisation, and the Qwen figures are a transfer of its collective and service geometry.

## 4. Still modelled or open

- **Element views.** These are sized placeholders, not hardened views: SM element (route OPEN), SU, SFU, HC, attention tile, index quarter, TU endpoint, cmdproc, VM, stream service.
- **Stage counts.** They are bounds from GRT routed length, not detailed-route STA. The block-level SS/FF closures belong to their owners.
- **Power densities and IR.** The power densities are assumptions. IR uses peak in-phase density over each block, with 20 um load cells.
- **Collective term.** The TU PHY/switch/cable vendor budget and the striping tail are unchanged from the matched reference.

Handoff: `HANDOFF_CODEX.md`: route iterations of the fixed r8 floorplan. Targets: GRT overflow 128 -> 0, and pulling the routed bound toward the floor.

## Replay

```
python3 tools/hbm_accel_die_fp.py plan                       # floorplan.{json,def,svg}, domains.sdc
python3 tools/hbm_accel_die_fp.py check                      # legality, pin clashes, Manhattan bounds
# on the compute host (grt_all.sh / ir_all.sh in the scratch root):
python3 tools/hbm_accel_die_fp.py real --work C/a_real
python3 tools/hbm_accel_die_fp.py grt  --work C/b_k16_i50 --k 16 --iters 50   (+ --iters 5, --empty for the baseline)
for w in $(python3 tools/hbm_accel_die_fp.py irwin); do python3 tools/hbm_accel_die_fp.py ir --work I/c_$w --window $w; done
tools/hbm_accel_die_run_case.sh <case> run.tcl run.log <cpus> <mem_gb>
python3 tools/hbm_accel_die_fp.py record --work <cases root> --out feasibility.json
python3 tools/hbm_accel_die_fp.py price  --work C/b_k16_i50
```
