# HBM-HUBMESH-1 one-page ESTIMATE (12.14b): hub regional clock MESH for T028 NW_hub / T029 NE_hub

2026-10-31 02:0x PDT. Plan d44f (DIE-HBM-45 plan dir, intel2 die-hbm-45/plan/d44f), tap map = DIE-HBM-45 B kit tree.json
(the same 374/371 hub taps C1/C2/C3 use). Parallel form to HBM-CLKLOC-1 (sb63 physical DME); hubs only (OWNER 12.26).
Labels: CHECKED = read from plan/tree files; MODEL = my linear-RC solve (main `qc_clk_mesh2.solve_netlist`, unchanged,
ngspice-fit BUFx24 Thevenin `qc_mesh_pilot_1/thev_m1.json`), not routed; UNCHECKED = analytic scaling.

## 0. Hub facts (CHECKED, hm_hubtaps.json)
| | NW_hub (R0) | NE_hub (MY) |
|---|---|---|
| outline | 8216.64 x 4320 um, 6.39 M cells | same type size |
| hard cores (outline) | 154, 16.4 % of area, largest u_svg 776x647 | 111, 16.2 % |
| taps | 230 glue (clk_t, 72 x / 50 y values: scattered, NOT a lattice) + 143 core (clk_c) | 230 + 140 |
| early core taps | 35 (35-196 ps early, B tree model) ; 108 zero-early | 35 (35-196) |
| plan clock entry | (4298.4, 1468.8) M9 = 0.19/0.69 mm off centre | (4449.6, 630.7) = 0.34/1.53 mm off centre |
| glue distance | any point <= 323 um from a glue (non-core) site; 84 % of the area is glue | same |
| B tree in-box wire | 251.5 mm, 763 nodes, 153-169 stages from die root | 258.0 mm, 753 nodes |

## 1. Mesh grid (two variants, 12.17)
Uniform grid over the full hub box; M9 vertical straps, M8 horizontal straps, 4W (0.16 um) NDR in PG gaps (4.32 lattice,
mesh_form snap_gap), strap keep-out 0.32 (qc_mesh_p2 form). Drivers BUFx24 on the vertical straps.
| variant | V straps (M9) | H straps (M8) | drivers | driver pitch | strap wire | max / mean stub |
|---|---|---|---|---|---|---|
| **A** | 16 @ 513.5 um | 16 @ 270 um | 256 (16/col) | 513 x 270 um | 200 mm | 135 / 57 um |
| **B** | 32 @ 256.8 um | 16 @ 270 um | 512 (16/col) | 257 x 270 um | 270 mm | 128 / 45 um |
Tracks (UNCHECKED vs die GRT use): one strap + 2x0.32 NDR spacing + 2x0.32 keep-out = 1.44 um = 18 tracks at the 0.08 M8/M9
pitch. A: 16 x 18 = 288 of 102.7k M9 tracks across the hub (0.28 %), 288 of 54k M8 (0.53 %); B: 0.56 % M9 / 0.53 % M8.
Pre-mesh H-tree legs add about the same again in any cross-section. PG on M8/M9 (0.48/0.672 at 4.32) takes 11-16 %; straps
fit the 3.65-3.84 um PG gaps. Against: the tree form B already carries 252-258 mm of clock wire inside each hub box.
Die signal use of hub M8/M9 (leftover, FT-M89) is NOT measured here -> the die GRT0 rerun with the mesh is the check.

## 2. Pre-mesh tree (UNCHECKED)
Equal-leg H-tree from the hub root to 128 (A) / 256 (B) leaf nodes, each leaf drives 2 mesh drivers at +-p/2 (mesh_form
C->D->M pattern), BUFx24 + 4W NDR on M8/M9 OVER the cores (cores own M1-M7, 12.1a), repeaters <= 360 um (QC pilot pitch,
< 450 owner max) in glue (84 % of area, <= 323 um to a site: legal by a <= few-um slide).
- Path root -> leaf: x W*15/32 = 3.85 mm (B: 31/64 = 3.98) + y H*15/32 = 2.03 mm = **5.9-6.0 mm**, plus the shared trunk
  from the plan entry to the box centre 0.88 mm (NW) / 1.87 mm (NE).
- Stages: (6.8-7.9 mm)/0.36 = **19-22 BUFx24 stages** (+ branch nodes), vs 48 inverter stages for the region DME tree.
- Insertion at the QC pilot rate (523 ps root->mesh over ~1.8 mm, 7 stages = ~280 ps/mm incl. mesh driver):
  **NW ~1.95 ns, NE ~2.25 ns** (tree form 2.1 ns). Shared trunk = no skew, only seam phase (section 5).
- Pre-mesh nominal residual (routed): QC pilot 29-40 ps at 7 stages (GRT x-jogs onto core edges; straight legs 0 jog).
  Hub at 19-22 stages: sqrt 51-71 ps .. linear 83-125 ps. M8/M9 over cores means no wall detours (the B root cause).

## 3. Mesh skew (MODEL, est.py, both hubs, nominal, est_AB.jsonl)
| variant | corner | nominal mesh skew (equal driver arrivals) | with 60-ps uniform pre-mesh residual | mesh delay |
|---|---|---|---|---|
| A 16x16/256 | TT / FF | **31.3 / 30.7** (NE 30.6/30.0) | 51.7 / 56.7 (NE 52.7/57.6) | 84 / 69 ps |
| B 32x16/512 | TT / FF | **15.1 / 14.8** (NE 15.0/14.7) | 36.4 / 38.9 (NE 40.6/43.5) | 65 / 53 ps |
Sweep (TT, NW): 16x8/128 65 ps; 32x16/256 drivers 45.5; 32x32/512 18.7; 64x16/1024 8.9. Dense drivers pass ~60-70 % of
the pre-mesh residual (each tap is close to one driver); the grid is driver-limited, not strap-limited.
Stubs (strap -> tap): taps are off-lattice, so each tap gets its mesh load cell (BUFx4f, published_grid_clock) on the
nearest off-core strap point (jog <= 2 um, as the QC pilot) and the 0-135 um stub to the tap becomes a regular routed net
driven by that cell: +25-35 ps common, +0-15 ps nominal spread (UNCHECKED), included in the routed STA, not in the mesh sim.
Variation sign-off U (12.8e, |mu|+3 sigma, UNCHECKED): QC pilot 45-54 ps at 7 stages; hub random tree part x sqrt(20/7)
and 0.21 %/mm over 8.2 mm (~29 ps systematic at 2 ns, partly averaged) -> **U ~60-110 ps** (A high end, B low end).

## 4. Clock power (INFO, UNCHECKED)
Switched C per hub: A = 41 pF mesh (38 straps + stubs + loads, MODEL) + H-tree ~126 mm (13-24 pF) + 256 BUFx24 + ~350
repeaters ~= 60-70 pF -> ~35-40 mW at 0.7 V/1.2 GHz (+ internal ~30 %); B = 54 pF mesh -> ~75-85 pF, ~45-50 mW.
Tree form B: ~252 mm 1x wire (~25 pF) + ~1400 inv2 repeaters ~= 30-35 pF. **Mesh = 2-2.5x the hub clock power** (both hubs:
+~60-90 mW die, INFO; tok/s unaffected).

## 5. Seams (hub <-> SM / other regions) and contracts
- All hub crossings are region crossings of the sb63 map (773 die crossings, CA D4 762 / D8 11 / FAIL 0 in HBM-CLKLOC-1
  ESTIMATE section 4): they are LANDED (count-aligned) hops, so the unshared global-tree delay is absorbed by the CA window,
  not timed as a related pair. The landing plan event is needed for both forms (d44f has no landing rows) and stays with
  HBM-CLKLOC-1. Mesh effect on seams = only the hub phase: insertion is deterministic (equal legs), the c21 link feed
  balances region roots to the declared insertion, so the hub phase error is the model error of section 2 (~+-100 ps,
  UNCHECKED) + mesh skew; SM side keeps its own residual (197-330 ps est, HBM-CLKLOC-1). CA margin decides (>= 100 ps).
- Non-landed related pairs crossing the hub boundary: none expected (face_xing budgeted; to be CHECKED in die_sta_related).
- Core contracts: 108 zero-early cores sit on the mesh: arrival = mesh +- (skew/2) -> +-8..29 ps around the hub mean
  (inside insertion_tol 40; the 20 ps band is a target). 35 early cores (35-196 ps): DEFAULT = early branches taken off
  the pre-mesh H-tree at the level whose arrival is (mesh - early), plan-computed sizing (12.8 d1/v5.0 early taps from the
  core's own view); their CPPR point is that H-tree node, not the mesh. Residual vs contract ~+-20-30 ps (UNCHECKED).

## 6. Verdict and plan
FEASIBLE on the estimate (UNCHECKED): nominal intra-hub clock spread 15-31 ps mesh (+ passed pre-mesh residual 36-58) vs
233-470 ps for the 48-stage tree; with the 12.8e signed-mesh common point the intra-hub related pairs carry U ~60-110 ps.
Setup at 833 ps is not the risk; **FF hold >= +10 on zero-logic glue pairs is** (hold <= U - clk->q): needs flow data-path
hold buffers (12.4a a1) on those pairs; count reported. If U > ~110 the B grid (512 drivers) is the fallback density.
Blockers (not estimate failures):
1. TOOL: tools/clk/mesh_form.py is wired for the QC 4-column, taps-on-lattice topology only (cols == 4, 2 early-tap rows,
   ConfigError otherwise). The hub needs a generic `region.mesh.topology: grid` (2^a x 2^b drivers, equal-leg H-tree,
   glue-site legalization of tree cells, off-lattice taps via buffered stubs, early-tap branches). Generic change + tests,
   default byte-identical (qc_mesh_p1 replay), ROOT-MERGE. ~3-4 h. No die-local builder (owner: one clock tool).
2. DIE ARRIVALS: seam/landed pricing and the hub root arrival need a routed die clock; C1/C2/C3 kits are still in region
   DME (HBM-CLKLOC-1, 01:33). Hub-internal build/route/MC/STA does not wait for it (region harness from the hub root port).
Build plan: T028 A and B in parallel (region harness = mesh_form run.sh: GRT -> DRT -> RCX, FF dump), explicit_mesh_signoff
rec+mc (60 samples), die_sta_related --mesh-signoff on hub pairs once a C proof exists; then T029 (mirror).
