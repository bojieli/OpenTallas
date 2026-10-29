# DIE-HBM-15 (2026-10-29) -- HBM C25c: G0C core_faces fix at the plan source + S1 lane estimate

## (3) 14 G0C core_faces errors -> plan-source per-port re-pin (CHECKED: main check.py re-run, image viewed)
- Root cause: the hub pin tables were written before later partner moves (vmdel/xl_ctl/dbk/hcollks/gq_land pair move
  C25c, station resite d15). check.py core_faces then sees 167 hub port groups (q_hub_nw 75, q_hub_ne 92) + q_spb0 x2
  (ep sd_tx) whose pins face away from their partner. core_pins_orient.py (whole-core mirror variants) only fixes 8.
- Fix: NEW opt-in tool tools/die_plan/core_face_repin.py (+ test_core_face_repin.py 4/4; with test_check.py and
  test_core_pins_orient.py 51 passed). It uses the SAME check.py core_faces model (new optional
  check_core_faces(collect=...) kwarg, nothing else changes, no new check) and moves only data-port pins of a failing
  port to the face that lowers its FAIL count over every instance of the table. It places them on the table's own
  track lattice on that face (same layer, same depth, 2-track spacing) and never moves clock/reset/island pins.
  Outline, origin and orient do not change.
- Plan c25c_d16 (sha 6ba9f877d23f; intel2 /srv/opentallas-scratch2/claude/die-hbm-15/c25c_d16) = c25c_d15 + 2 passes
  on q_hub_nw/q_hub_ne:
  - pass 1 (shared tables, 0 new designs): 52 ports in 7 tables (repin_pass1_shared.json). This alone =
    c25c_d16/die_plan.fr.json (variant S: 80 core designs).
  - pass 2 (--per-orient, COORD CLOCK-KV-R13 form, <=1 view per orient): 21 ports in 7 tables
    (repin_pass2_per_orient.json). Core designs 80 -> 87 (vms_bank vecd4ae 1->4, vec6293 1->2, gq_land 1->3,
    gq_issue 1->2).
- G0C: d15 FAIL 14 errors (167 hub groups) -> d16 FAIL 10 errors (15 hub groups + q_spb0 x2 sd_tx); warnings
  744 = 744; no new error class. G0 PASS 0 errors. Pin tables: 0 duplicate xy, 0 duplicate names, interior pin count
  unchanged (CHECKED, script in log).
- Remaining 15 hub groups: vms_bank instances of ONE table+orient whose single partner (u_hb_dbk, u_xl_Q_ctl,
  u_hcollks_Q_p*, vmdel_Q6/Q7) sits on different sides of different instances, so no single face serves all
  (rem.py output). The fix is a placement fix (move those partners) or per-instance views. SPB ep sd_tx (-0.11, about
  perpendicular) is left alone because the OWNER SPB M6/M7 escape contract owns those pins (G2 live).
- Image repin_ne.png (q_hub_ne W half, before/after, VIEWED): moved groups sit on the partner-facing edges and no pin
  is inside a core.

## S1 lanes (HBM-BIND-2 handover, 158 pairs / 179,387 b): 12.14b ESTIMATE BEFORE BUILD (s1_lane_estimate.txt, UNCHECKED)
Shared-face supply = 50% of M4+M6 (or M5+M7) tracks on the shared edge, minus the existing port widths:
| class | pairs | bits |
|---|---|---|
| adjacent, fits the shared face | 48 | 90,680 (IDX scorer 41,976 / SU split 42,150) |
| non-adjacent <= 1.2 mm (street apart) | 20 | 32,418 (SU split 25,722) |
| non-adjacent 1.2-4.6 mm | 44 | 28,993 (SFU 12,404 / other 9,542) |
| non-adjacent > 4.6 mm (up to 12.8 mm) | 46 | 27,296 (IDX 10,604 / SFU 9,992 / SFU<->SU 6,672) |
None of the adjacent pairs is over the face supply. The 46 far pairs (b113 SFU control/store <-> b110-b112 lanes and
all 4 SU slices; b100->b102 scorer chain 8.9 mm) break 12.13 LOCALITY FIRST as point-to-point lanes: each would be a
hop chain of up to ~32 stations across 3-6 partitions.
