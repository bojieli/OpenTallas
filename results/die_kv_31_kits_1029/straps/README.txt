DIE-KV-31-KITS straps step (2026-10-29 10:3x PDT): count-strap pin sites for the 7 core-free KV kits.

Root cause of the six die-kv-30 FAIL_PREFLOOR port_bind failures (CHECKED). None of the KV plan's
partition_types[*].count_straps carries layer/sites_um. gen_phys.strap_pin_sites (9f6da9e92, already present in the
Codex generator 93a731342f) only emits strap pins, port_bind_pins and straps.json for straps that have sites. The strap
bits per type therefore equal each port_bind "extra": hroot 140, io_cor 134, io_cor_v1 152, io_ft 26, io_ft_v1 26,
hub_Ei 488 (sys_c 140, sys_SD/_v1 14 each).

Fix: a die-local plan-data step, physical/die_plan/qwen_kvsys/g3/kv_count_strap_sites.py (+ test_kv_count_strap_sites.py,
2 PASS). It is a plan delta on count_straps only, idempotent (a second run changes 0 types and gives an identical plan,
CHECKED) and fail-closed on a partial or different assignment. It follows the HEAD form (DIE-HEAD-5 TILEIO: interior
strap row at y 4.32, 34 M7 tracks = 2.176 um apart).
  - Layer = the type's own signal ceiling, the kit MAX_ROUTING_LAYER: M7 for all 7 types (CHECKED config.mk). No type is M5-capped.
  - x on the M7 track grid (0.032 + 0.064k, from the kit make_tracks.tcl), starting at 21.6 um.
  - Sites refused within 1 um of any plan pin, inside a content macro box grown by 4.32 um, or inside a clock keepout /
    die island grown by 2 um.
  - Input plan: plan_snap (the sys_c grid snap). Output: plan_straps (sha in plan_straps.sha256).
  - Result (strap_sites_report.json): one row at y 4.32 per type; x span 21.6 to
      hroot 324.1, io_cor 311.0, io_cor_v1 350.2, io_ft/_v1 76.0, hub_Ei 1081.3 (of 1278.72), sys_c 324.1.
Regenerated the 7 kits with the same Codex generator (gen_straps.sh via ot-run intel1, about 18 s / 0.2 GB each).
KIT_PREFLIGHT --contract --plan-dir: 7/7 PASS 0 issues (preflight/, CHECKED).
Kit diff (kit_delta/; vs the die-kv-30 copies, sys_c vs the snapped kits_gen; CHECKED):
  - io.tcl: 0 lines removed; only strap place_pin lines added (140/134/152/26/26/488/140).
  - plan_pins.json and port_bind_pins.json: 0 records gone, 0 non-strap records added.
  - freeze.json: pins sha and pin count only.
  - straps.json: new.
  - Every other file is byte-identical, rtl/ and reset_tree.tcl included.
Pin views straps_sys_c.png and straps_hub_Ei.png VIEWED: one red strap row along the south edge, clear of the
d2d/UCIe/ROM macros and keepouts and of the edge pins.
Place-only runs (run_kit.sh GOAL=place) were relaunched via ot-run --hosts intel1, admitted 10:3x. Units:

| Kit | ot-run unit | Memory |
|---|---|---|
| hroot | oth-ubuntu-2775793 | 24 GB |
| io_cor | 2775822 | 24 GB |
| io_cor_v1 | 2775826 | 32 GB |
| io_ft | 2773919 | 16 GB |
| io_ft_v1 | 2775791 | 16 GB |
| hub_Ei | 2775810 | 48 GB |
| sys_c | 2775816 | 32 GB |

Memory figures are the die-kv-30 values, UNCHECKED. Kits: intel1:/srv/opentallas-scratch2/claude/die-kv-31-kits-1029/kits_gen2/<type>
(run_place.log, FAIL_PREFLOOR, port_bind.json, lec/). Client logs: intel2:/srv/opentallas-scratch2/claude/die-kv-31-kits-1029-clients/<type>.place.otrun.log.
FOLLOW-UP (bind / die top, not done here):
  1. The die top must tie each instance's strap pins (12.15a), so the KV bind/die-top needs these sites.
  2. Die-level access from M8 down to these interior M7 pins at y 4.32 must be checked against die PG and clock M8/M9 use.
  3. The die plan/bind must take both deltas (kv_sysc_grid_snap then kv_count_strap_sites) before the next bind.
  4. kv3_sys_SD/_v1 are not regenerated: they are still held on the x6 PHY alias. Their 14 strap bits each get sites when
     they are unblocked (run the script with --type kv3_sys_SD=M7:...).
