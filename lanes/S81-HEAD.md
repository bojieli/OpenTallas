# S81-HEAD lane (claude/s81-head-1024, worktree localhost:~/wt/s81-head)
Scope: S81.HEAD head die top-down (uarch sizing -> die_plan G0/G0C -> die_io vs layer die), LINK5/HOST check of the
S81 layer-die plan. Host share intel2 32 thr: not used (all work is seconds-scale analytics; no P&R launched).

## Where it stood (task 1)
- SPEC v1 results/arch/s81_head_1021/SPEC.md (10-21): 253 tiles (ot_s81hd_tile = bundle 5 elem / 10 ROM4096), spo/spr
  spine, ctl, lep (= stage s_0N lep), 13 lanes, 17 SerDes (incl. 5 draft fan-out), no HBM.
- Bottom-up die chain H1..H11 (tools/s81_dv/head72 on claude/s81c-die2-h11r4-1022, never merged). Last evidence
  (old intel2 nvme /mnt/old-nvme0/claude/stw-s81-head-h10/h10bm): BIND/CASE/GEN/GRT done 10-22 06:12, IR PASS
  8.34 mV, STA TT setup WNS -11,022.8 ps / TNS -27.2 us, hold WNS -22,207.7 ps, die clock check "NO COMMON ROOT"
  on station pairs => H10 FAIL. H11 r4 prep only (glue R5-R8 kits), not run.
- CLOSED leaves: s81hd_spo_m, s81hd_spr_m4/f4, 7 lane sub-children s81hd_lsc_*, dshead elemA/elemB at SS.
  s81hd_tile r5..r7k kits never closed (r6 crashed RSZ-3006; r7kg/kh kits only).
- LINK5 / HOST / SerDes: rack plan in docs/RELEASE_RACK.md 2.1; lanes/S81-LINK5.md lost with rtx-pro. SerDes column
  lp8b CLOSED TT +159.84 / FF +6.47 (SS sensitivity -60.83); ot_pdie_serdes / ot_pdie_ucie parents open.

## Results (task 2, commit cc7b6206fc)
- uarch: tools/s81_head_die_model.py (`uarch_model.py --s81-head-die` -> results/uarch/s81_head_die.json). Tile =
  4 elemA + 1 elemB CLOSED views as hard cores, 691.2 x 1036.8 um, ~1.07M cells; 264 slots (253 active, 11 dark);
  die 21,120 MAC/cycle, 45.2 kB/cycle ROM; head path 9,056 cycles a position vs calendar window 10,357;
  1 TP4 group = <= 35% busy at saturated AR / 21.5% MTP.
- die plan: physical/die_plan/s81_head (gen_plan.py from the model): 17.52 x 17.56 mm = 307.6 mm2; 326 partitions /
  16 types, 425 ports, 325 lanes. G0 PASS 0 err; G0C (--completeness) PASS 0 err, 4 warn (core_faces unchecked
  for tile cores, r8 no as-built groups, die.reach_um note, census none = new die); 16/16 types G3-eligible.
- die_io: 12 SerDes windows (= layer-die slot / PHY / 150-um bumps), host:true on HOST0/HOST1.
- cross-die (tools/die_plan/xdie_io.py, new): head die 0 errors (head_hop S-H 4, H-H 8, token_return H-S 4,
  tp_mesh H-H 18, host 12). Layer die FAIL 130 (copy-A/B pairs + host flag) -> reported in lanes/S81.md.
## Merged: main 84bbf08c9f (13 files, 0 deletions)
## Task 3: LINK5 present on the layer die (10 SerDes, all bound); gaps -> lanes/S81.md "Gaps reported by S81-HEAD".
## Known limits (honest)
- tile cells for elemA = elemB cells x area ratio (ASSUMED); ctl / mesh / host cells ASSUMED; elements' CLOSED view
  is ot_dsrom_head_elem CUT 0x1ff, S81 tile RTL uses ot_s81hd_elem CUT 0x17b (status rework: equivalence or re-close).
- spine-node internal stations declared but not G0C-checked (no content boxes); tile core_faces unchecked (WARN).
- Not run: G1 GEOM review, G2 probes, any P&R.
## Next
G1 review of die_plan.png; G2 probes (worst types: hd_turn_*, hd_spn) on intel2; tile G3 kit on CLOSED elements.
## OWNER?
1. Head-die count: rack has 12 (3 TP4 groups, 10-06 record); model: 1 group (4 dies) carries saturated AR + MTP and
   single-user MTP positions never overlap (>= 23,239 cycles apart). 12 -> 4 saves 8 dies + 8 host links.
2. HBM on head dies: rack says 4 stacks/die (48); this die needs none (ROM-resident head). Plan has none.
3. Draft fan-out SerDes (SPEC v1: 5): rack wires none (placeholders); plan has none. Confirm MTP draft rides copy-B.
4. 11 dark tile slots (ten=0) kept for a regular chain; alternative shorter last chain, same outline.
5. Copy-A/B 6th pair on 64 layer dies (EN2/3, WS2/3) missing from the layer-die plan (S81 lane).
