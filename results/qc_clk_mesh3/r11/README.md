# INFRA-FIRST-QC-R11 (2026-10-26 21:47 PDT) -- all numbers UNCHECKED (NUMBER-CHECK pending)

Branch claude/qc-mesh-r11-1026 = R10 756100d5db + merge of codex/qc-r9-2000@c540e671da (R9 physical tree/stack tools).
Plan: candidate_oneqc0733.json (the plan R9 tree5 and r10 used). Fragment: r10/legal/hold_demand_fragment.json.

## (3) data hold buffers (v4.9 / 12.4a a1) -- `hb_count.json`, `scripts/r11_hb_count.py`
Kit rule (gen_phys.input_hold_min plan_demand): in_min = 12.5 - D per TYPE port (max D over instances); repair pads
D + 12.28 ps; HB4xp67 44.555 ps FF early (46.90 x 0.95), 0.1021 um2.
- 2707 vector seam ports, 1,277,200 bits (286 scalar ports keep the fallback contract), 773 fragment pairs, 0 on default
- HB4 = 2,731,174 cells = 0.2789 mm2 = 0.034 % of the die (per-instance-D lower bound 2,384,086)
- cells/bit: 1 -> 155,117 bits, 2 -> 790,192, 3 -> 331,891; D 20.2..92.8 ps
- FIT: every partition < 0.24 % of its non-hard-core area (worst sl_*_sc 18,985 HB4 = 1,938 um2 of 821,519 um2;
  0.41 % of the est. util-0.6 headroom); 0 partitions over headroom (57 types lack a fill note -> judged on free area);
  0 partitions newly cross 400k cells (228 already above as declared counts)
- TT setup cost at 3 cells = 249 ps (75.2 x 1.05 x 1.0511 each) vs r10 seam TT setup worst +563.51 -> >= +314 bound
## (1a) physical export of the mesh3 top tree on R9 site rules -- `r11_top_sites*.json`, `scripts/r11_phys_sites.py`
- 4682 groups (930 nodes, 2840 repeaters, 912 leaf = column-tap cells on all 19 tap rows) = 8452 BUFx24, 4681 nets
  (4541 M8 x-tree, 140 M9 trunk), 3686 MY by the R9 load-direction rule, 0 footprint overlaps
- R9 site gate FAIL (plan-fixable): 866 cell bodies cross a vertical partition seam + 48 a horizontal seam (max move to
  one host 0.81 um = half a BUFx24), 19 east-column col_taps at x 31215.51 (body past the die edge W 31216.32)
- 12.2a1 per-type islands: sites are NOT identical per type -- union over instances is 6.5-11.3x one instance's count
  (cbf_q01 338 union vs 30), 74 types / 360 partitions host cells -> R9-style union abstract windows or a per-type lattice
- R9 tool gaps before route: (i) die_clock_mesh.NDR has only 4w/8w (mesh3 top = 16W M8/M9: shield/track/pad/via-array
  support needed); (ii) build_lattice() takes only binary midpoint equal-cut H-trees, mesh3 is delay-balanced -> needs an
  explicit-cells build path into C128.fixed_wires; (iii) 2-unit stacked groups need A/Y tie straps as fixed wires
- Renders viewed: r11_top_sites.png (whole die), r11_zoom_centre.png (trunk between the two centre cores)
## (1b) DRC / ndr016 RCX / resistor graph, (2) RCX-fed mesh solve + 377-entry STA: NOT RUN (blocked on (1a) gaps)
