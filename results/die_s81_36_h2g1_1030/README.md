# DIE-S81-36/H2G1: H2 tree re-converted onto FREE native sites; ONE model requal PASS; ONE protected G1 install: tree PASS, strict audit FAIL (post-CTS data repair)

Date Fri Oct 30 11:51:34 PDT 2026. Successor of DIE-S81-35/H2G1 (601ae80bee9, 1307/1811 admitted sites occupied by native cells).
Native kit: copy of intel2 codex-s81types-1030/coll_clock/kit (3_place sha 56af214f..., unchanged), run dir /srv/opentallas-scratch2/claude/die-s81-36/h2g1b.

1. Re-convert (scripts/convert_free.py): admitted record codex-h2-window-1030 tpqt_slew_geometry/plan_geometry.json
   (same 1811 masters/count/depth/memberships/19747 sinks) through the canonical core_plan_to_infra converter with ONE
   added site rule: every placed native instance of 3_place (98292: 68979 core, 21474 welltap, 7784 tie, 55 macro) is a
   hard blockage. Displacement max 10.125 um / mean 0.92 um, 197 >2 um, 38 >5 um (convert_free.json). Converter ring
   limit raised to 320 um because the macro-cut ROW list is fragment-indexed (the canonical window grows by fragment
   index, so it missed nearby free sites at R<=20; the found sites are all within 10.125 um). Record update for the model:
   nodes at the free centres; every driven wire segment lengthened by its driver displacement (+1363.4 um total, hub kept,
   moved children priced as landed stubs) -- conservative.
2. ONE UF3 model requal (scripts/qualify_free_once.py = Codex qualify_h2_calibration_once.py with only record/sites/output
   changed; unchanged uf_phys3_v1 fit/kernel, 3 kernel calls TT rise, FF rise+fall): MODEL_ADMISSION_PASS.
   TT mean 367.42 window 43.26 (INFO) all-buffer slew in/out 51.21/47.83; FF mean 273.22 window 32.74 all-buffer 39.23/35.94;
   sink envelope TT 43.86 / FF 33.50 < 80; native PG 1811 edges 0 blocked. Structural compile (compile_free.py, no kernel
   re-call) takes the exact modelled sites (free() proven) after the first in-script compile stopped in the ring search
   (model_compile_convert_FAIL.log kept). Independent site probe on 3_place: 0/1811 blocked; 0 tree-tree overlaps.
   LOOK.json + free_sites.png personally viewed.
3. GEN/PREFLIGHT: canonical kit_apply + plan_tree_cts (main 16f2590f75f): prep PASS (tcl regenerated exact, 1811/19747/1811,
   6 islands, 0 CTS-open); kit_preflight PASS (plan dir = event3 physical/die_plan/s81).
4. ONE protected G1 install (ot-run unit oth-ubuntu-1409813-1793385445, exit 0, 4_cts.odb sha 096cf4b9d8cd...):
   OT_CORE_INFRA_LATE_DPL max_disp 0.000 (late DPL converged, no-op); tree audit: 1811 cells exact (0 um), all FIRM,
   0 master/orient mismatch, 19747/19747 sinks on planned nets, 0 unplanned clock drivers, ck[0] M5 pin native.
   Strict audit verdict FAIL ONLY because the kit POST_CTS setup repair_timing (data side, placement RC) added 43 non-tree
   rebuffers, removed 1 cell and moved 45 pre-existing cells incl 4 FFs (u_ep.g_rb_safe..., u_gb.bg[89/90]); post-repair
   check_placement PASS. INFO UNCHECKED (placement RC): OT_TAP_RC insertion 230..298 ps (mean 268), setup WNS -267.8 ps /
   88 viol at u_ep.g_rb_safe.g_address[1].ready_r D (same endpoint as the DIE-S81-35 run; data path, not clock).
No GRT/DRT/G2 run. G2 not authorised.
