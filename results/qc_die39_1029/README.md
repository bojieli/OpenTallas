# DIE-QC-39 (2026-10-29 16:50-18:10 PDT) - provider leaf loads, QC-001 landing reserve, A0 estimate, VMR

QC die FROZEN, fix-only. Base: DIE-QC-38 variant D (intel2 die-qc38/prov_R7D: top 2,903, census 542/88).
Run data: intel2:/srv/opentallas-scratch2/claude/die-qc39/ (leaf_geom, leaf_loads.json, access_leaf_resite, prov_R7{E1,E2,L1..L6}).

## 1. Shared tool: leaf-driver A pins as fixed-tree loads (READY ROOT-MERGE)
- claude/die-qc-39-pcl-1029@3426f16d7f4: main tools/clk/provider_clock_loads.py accepts role=clock_leaf, pin=A, CKINVDC/INV master
  loads; register-only inventories byte-identical (CHECKED: extend() main vs branch on QC 22,365-load inventory, JSON equal);
  13 tests pass, 2 new fail on main.
- The QC prebuild actually runs Codex's UNMERGED codex/qc-provider-clock-0834@d1f6310e9 (provider_clock_loads with entry/M3 jog/stage
  binding, plan_provider_clock_access.py, fixed_tree_provider.py; snapshot die-qc34/src_pc). claude/die-qc-39-pcl-cx-1029@6ca6cd8ede7 =
  main + that branch + the same leaf change in provider_clock_loads.py and plan_provider_clock_access.py; 20 tests pass; FF-only
  byte-identical vs the Codex file on the real inventory (CHECKED). This run used a die-local patched snapshot die-qc39/src_pc
  (scripts/patch_pcl.py, scripts/ppca_leaf.py) = the -cx content.

## 2. Leaf ODB inputs (CHECKED)
- export_geometry119 on leaf ODB (die-qc38/leaf_apply/provider/provider.odb) -> leaf_geom/geometry.json.
- scripts/leaf_inventory.py: 3,266 loads = trunk-side CKINVDCx5p33 A pins (actual M1 metal from readback) on 2,420 trunk nets
  (was 22,365 FF CLK on the same nets; 6.85x fewer).
- scripts/retained_resite.py: provider access reserves the R7 RE-SITED clock-cell stacks + clock-cell vias (810,974 M1..M7 shapes from
  prov_R7D prebuild) instead of the pre-resite clock_seed.json.
- Access plan (plan_provider_clock_access leaf copy): LOWER_ACCESS_GEOMETRY_PASS 3,266/3,266, 0 failed (runs/access_leaf_resite).

## 3. QC-001 prebuild variants (all on R7 backbone, variant D rules PROV=A NAT=1 NEAR_A=8.64; all CHECKED prebuild.json/classify.json)
| var | loads | native landing-row reserve | M9 jog column | top conflicts | census short/spacing | track stage |
|---|---|---|---|---|---|---|
| D (QC-38) | 22,365 FF | - | pin x | 2,903 | 542 / 88 | PASS |
| E1 | FF | strap-band ports (750 vertical; 557 kept, 193 blocked) | pin x | 1,679 | 551 / 91 | PASS |
| E2 | FF | all vertical-net native ports (1,092 kept / 304 blocked) | pin x | 1,514 | 551 / 91 | PASS |
| L1 | 3,266 leaf A | band | pin x | 1,013 | 18 / 6 | PASS |
| L2 | leaf A | all | pin x | 848 | 18 / 6 | PASS |
| L3 | = L2 + blocker census | all | pin x | (same) | | 301/304 blocked = shield hit w/o PG flank, 3 = PG shield spacing |
| **L4** | leaf A | all | nearest M9 track outside M9 PG band (+-0.32), <=2.0 um | **413** | **18 / 6** | PASS |
| L5 | leaf A | all | same, <=4.32 um | 413 | 18 / 6 | PASS |
| L6 | leaf A | all | outside wide-spacing band (+-0.5, PG straps 0.672 wide), <=4.32 | 665 | 18 / 6 | PASS |
Best = L4: top 2,903 -> 413 (-86 %), census 542/88 -> 18/6 (-96 %). Prebuild still FAIL.

L4 residual (runs/prov_R7L4/classify.json): 123 clock-cell VIA78 M8 patch vs adjacent tree segment end (e.g. ck_rn39_0 patch 0.309 um
from ck_n38 end, < 0.32); 108 provider riser M8 pads vs trunk VSS shields (84 spacing / 24 short); 120 M9 jog vs PG wide-spacing
(jog column clear of the 0.32 band, not of the 0.5 wide row); ~70 M9 jog vs other shields/tree; census 24 = native M7 port vs
re-sited cell stacks. L6 shows the jog column must be chosen against the full router index (PG wide row + shields + tree), not a PG band.

Next (successor): (a) jog column via router.place('M9', ..., dry) on the actual jog span (shield/tree/wide-PG aware) for the 304
blocked landings; (b) provider near-riser M8 pad keep the shield spacing (move pad along the riser or take the far PG-clear drop);
(c) clock-cell VIA78 patch vs tree segment end: extend/trim the tree segment end to the patch (same-net merge) or shift patch;
(d) 24 native census rows. Then PG access -> materialize -> mesh qc_mesh_p2 -> GRT0 >=50 it -> probe3 -> clock check.

## 4. A0 (sub-agent, claude/die-qc-39-a0-1029@0ed171249, results only): NO BUILD
Standard stages measured 25.02+-4.2 ps FF (CHECKED). Estimate (UNCHECKED): NK -351..-394 vs TritonCTS -571.84 (beats); NL corrected
~-182 vs TritonCTS -172.53 (does not beat) -> core_infra stays OFF. Opt-in generator flags in results gen_a0_tree39.py (byte-identical off).
Cause: macro rows force 279-554 legs >60 um, isolated registers 200-265 um legs, NK macro chains 173-216 um.

## 5. VMR MIF1 ECO: see vmr/ (sub-agent) if present.
