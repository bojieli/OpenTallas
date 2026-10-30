# DIE-HBM-37 (HBM die owner, 2026-10-30 12:02-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-37.
Tools: branch base db22a258fa5 (tools = main 16f2590f75f, same as DIE-HBM-35 d35a gates).

## d35b = d35a + collar_idx256r signed-view pins (COORD RULINGS 12:03 (1) (A)) -- CHECKED
mk_d35b.py BASE=d35a OUT=d35b DEF=signed view (intel1 hbm-cores-kits-27/collar_s30wl 6_final.def; 6_final.odb sha 93bc75ef).
Only the collar (root u_col_idx, origin 976.32,734.4, outline 88.992 square, R0) changes:
- clk    (88.872,44.424) C -> (43.224,43.2) M5 C; clk_in (0.096,52.584) W M4 -> (44.664,43.2) M5 C. Both inside the plan
  centre clock entry island already in clock_entries.json (u_col_idx xy 43.2,43.2, island 38.88-47.52, merged clk+clk_in):
  the plan clock entry is unchanged, the stale pins file now agrees with it.
- c_done: d35a already used the W pin (pin_select {c_done: c_done__W}, W M4 0.096,52.968) = the view's c_done position.
  d35b names that pin c_done, drops the unused N-face c_done (60.696,88.896) and the alias, removes pin_select.
  -> no parent-side connection moves.
- 4 island FT ports of the view (mp_isl0_ck_i/o, mp_isl0_rst_i/o, M5 inside the island) recorded as die-owned FT sidecar
  cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b_die_owned_ft.json (schema core_die_owned_ft.v1, as QC vmr).
Pins file cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b.json (1559 pins, sha 59da3314...);
die_plan.json sha 9349ccf9...; sidecar sha 0d5252ff... (plan_of_record/d35b, gz + SHA256SUMS; other files = d35a).
Gates:
- pincmp v2 (SIGNOFF-SPRINT-2 /tmp/pincmp_sp2.py) view vs d35b pins + sidecar: MATCH 1563/1563, outline 88.992 OK,
  0 moved >0.25 um, 0 layer diffs; vs pins alone: only_view = the 4 FT ports (pincmp_*.txt).
- G0 FAIL 6 err/918 warn and G0C FAIL 14 err/128 pending/910 warn on d35b = IDENTICAL finding set to d35a on the same tools
  (0 new, 0 gone; g0_d35b/*diff*); d35a rerun = DIE-HBM-35's d35a report exactly. Collar-related findings: only the 2
  inherited WARNs (core_pg LEF path, u_hb_idx__selector.k face orientation).
- Neighbour pins: the moved pins are interior (centre island) and c_done keeps its parent position; the collar has no
  partition-face pins; G0C core_faces unchanged. Render viewed: collar_d35b_pins.png.
