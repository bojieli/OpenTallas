# Owner-selected72-frame implementation

This replaces the unconstrained rectangle model as the one selected implementation. The source constructor `tools/s81_dv/dv_floorplan72.py` retains all142actual named envelopes in32000x25000um with86.4um corridors, no rotation or hard-outline shrink. Ten physical columns contain seven frames each; two additional h10 frames occupy the inner streets above the unchanged SerDes tiles. This physical grouping does not change the logical16-slice inventory:60h9+12h10,660ROMslots, exactnamehash5dd06ab657e89b6ad46ffe9581062cb7f4c8dfd6ea10cf82d5d650ec4c6a477f. `inventory72.json` is the capacity campaign's exact inventory.

The service hierarchy is one2x8group14428.8x7603.2um at8785.6,1846.4. Even services are lower and odd services upper. This preserves every old gather/scatter N/S/E/W neighbor face and keeps all2133/1077-bit buses short. They must not receive nonexistent long-wide relay families. The actual wide-face landing/root composition remains part of service source integration, not something geometry establishes.

`dv_plan72.py` binds those envelopes to actual instance/master names and rebuilds748logical links.48removed-frame chains are bypassed to the real surviving predecessor; removed frame returns disappear. No output is tied as a substitute for a removed frame. `plan_unrouted.json` is explicitly not yet usable as a routed GEN input. Its old computed facts are historical diagnostics until the route step replaces them; no timing/cut/capacity credit comes from the predecessor plan.

`dv_route72.py` is the selected macro-free route constructor. It preserves short adjacent buses without relay stages and plans350um chains for existing narrow-relay families. It runs on fleet, not a validation campaign. Actual relay hard-body legalization, source/view pin projection and clocks/reset/source bind must complete before intended GEN/GRT. Do not confuse planned points with implemented relay cells.

PMA placement assumption: package bumps over/along actual pin faces of the eight unchanged interior SerDes/PMA columns. No outer-shoreline PMA route is assumed. Keep actual existing source nets and emit pin-location manifest from selected kit/view during GEN; this is not package electrical closure. If external interface requires shoreline pads, actual paths must be included rather than waived.

MU end parent2764.8x6825.6 reservations require source/child reassembly around the selected6739.2-high slice; old2462.4x5788.8diagnostic parents are not a binding. Co-located service1728x3758.4 remains the current target envelope; it is not a newly closed hard parent. Frame source uses actual rf3rlfs1 outlines3369.6/3672; normal h9 reused with physicalMX needs explicit pin transform and INSTANCE identity, not an invented separate logic equivalence.

CurrentCAP/CPR compiler/source opt-ins are on mainb09575108: CAP+12 input/output landings, CPRQ-only launchadvance. CurrentGU source82 supersedes old capacity source. The source-correct MAP72 capacity/automatic map-exact flow runs independently; no stage/die/rate headline is adopted here. Old98/84campaigns remain diagnostic.

## G3 (LEAD-S81-G3 10-21)

`g3/` holds the G3 floorplan inputs/outputs: `template_fallback72_input.json` (the dv_floorplan72 template, = Codex
fallback72/input.json) and `base_plan.json` (the dv_plan72 base), `placement_g3.json` from `tools/s81_dv/dv_floorplan72_g3.py`
and `plan_unrouted_g3.json` from `dv_plan72.py` (die size now from the floorplan; G2 r3 output is unchanged byte-for-byte).
Slot fixes: real SerDes 518.4 x 3844.8 (4 per side in column A from y 86.4) + 2 reserved slots per side in column B (5th
lane pair + copy-A/B; blockage only, owner decision pending); die 32302.4 x 25200 (was 32000 x 25000) so every block keeps
>= 86.4 streets; service 1728 x 3801.6 x16 with the ctrl row +43.2; lepe MU72 parents 2851.2 wide; idx readers
1036.8 x 1209.6; seqhost 475.2 x 993.6. The route (dv_route72 + dv_station_dirs72) runs inside `release72/run_die72_g3.sh`.

## G4 (S81-LINK5 L5-G4 10-21, owner-approved 5th lane pair)

`g4/placement_g4.json` from `tools/s81_dv/dv_floorplan72_g4.py` (G3 template): W column B link_0_4/0_5 are REAL
ot_pdie_serdes slots 518.4 x 3844.8 (plan lk_WN2/lk_WN3); E column B link_1_4/1_5 stay copy-A/B blockage reserves;
end_parent_1 (s_0N) = ot_s81sl_slice_lepw_mab_mu_72 2851.2 x 6825.6 (s_0S stays 2505.6); die 32302.4 -> 32648.0 x 25200
(column 1 + E side +345.6, centre blocks +172.8; every G3 street/channel unchanged). `g4/plan_unrouted_g4.json` from
`tools/s81_dv/dv_plan72_g4.py` (G3 base + lk_WN2/3 + links lt/lr_lk_WN2/3: s_0N tx2/tx3 512 b -> SerDes tx, SerDes rx
562 b -> s_0N rx2/rx3, copied from lt/lr_lk_WN0/1); 144 blocks, 752 links, 2 blockages. Route + chain in
`release72/run_die72_g4.sh` (land plan + 4 sibling rows via `release72/mk_land_plan_g4.py`).
