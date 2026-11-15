# TYPE-KVIOFT (kv3_io_ft_v1) 2026-11-14 09:15 PST
CLASSIFY (attempt_4, kv102sem_ftgrid, routed 6_final.odb epyc2 .../kv102sem_ftgrid/items/kv3_io_ft_v1/attempt_4/gen/kv3_io_ft_v1): DRC 0, TT setup +17.64 PASS. FF hold -168.5 / 4436 viol = 4264 input-port starts + 8 output-port (advisory, parent). INTERNAL FF hold: 164 reg-to-reg endpoints, WNS -30.64 (TT internal hold 0). 137 of 164 = u_cland_ftN_i u_ring dch u_dsel/y -> u_ft_ftN_o_0 q (cland ring -> ft_o flop-to-flop, FF skew + 25 ps hold unc); rest small control chains. Dump: epyc2 /srv/opentallas-scratch2/claude/typekvioft/out/hold_dump.tsv.
Earlier ECO (b5, whole-design hold repair incl 4264 port paths) made FF -14 but TT -134: port hold buffering broke setup. Not a wide-outline issue: attempt_4 DIE_AREA already 1278.72.
Wave attempt_5 (kvgeom4 plan bc5799a6d171) in flight from 09:05.
PLAN: private ECO from attempt_4 routed DB with OT_PRD_PROTECT_NETS = nets on port-start hold paths (repair only internal), 2 forms (hold margin variants). Then sign R-MINIMAL, AUTO-RESIGN row, archive.

## 2026-11-14 16:13 update
- Split (COORD ask): FF hold = 4264 input-port + 8 output-port starts (advisory) + INTERNAL 164 reg2reg endpoints, WNS -30.64 (internal <0, so not signable as-is). Same on attempt_4 and attempt_5 (kvgeom4 plan bc5799a6d171, TT +17.64, DRC 0).
- Wave late ECO on attempt_5 (15:45) was refused in 98 s: autopilot admission bundle 1215d1008b85 has eco_loop.py requiring ot_prd_hold_scope_assert in prd_hook.tcl, but the bundle prd_hook.tcl (and prd_run.sh) predate it (107 of 108 bundles lack it). Repo tools/die_plan/post_route_drv has the matching hook. NOT a design fault: the nonport (reg2reg) scoped ECO was never run. Fix for KIT-OPS: re-snapshot admission bundle from main.
- Private forms (bundle copy with repo prd_hook/prd_run): A = attempt_5 kit (scratch3) hold-margin 5, out epyc2 .../typekvioft/ecoA; B = attempt_4 kit hold-margin 15, out .../typekvioft/ecoB. Logs intel2 ~/typekvioft/eco{A,B}.log. Both queued on epyc2 memory (09 min). 1 iteration each (OWNER 11-07 cap).
- Next: on ECO signed -> RMINIMAL check (DRC0, TT>=-42, nonport FF>=0), AUTO-RESIGN row, archive AGIdock + rtx-pro NEW dir.

## 2026-11-14 18:26 update 2
- Form A (attempt_5, margin 5, route-keep) ran 51 min: scoped hold repair WORKED (251 internal endpoints, 220 hold buffers, OT_PRD_HOLD_SCOPE_VERIFIED reg2reg) but DRT died in track assignment (make Error 241, peak 17.7 GB, not OOM). Form B on attempt_4 invalid (kit signoff gone).
- Relaunched: A2 = --from grt (full detailed route from pre-DRT GRT DB), B2 = margin 15 + --repair-rc placement. Out typekvioft/ecoA2, ecoB2 on epyc2; logs intel2 ~/typekvioft/eco{A2,B2}.log; queued for memory.

## 2026-11-14 18:41 update 3 (COORD, FABLE-HARD-KV s2)
- Build C: eco_loop --from grt --hold-margin 40 (reg2reg scope, full DRT, no route-keep), hosts epyc9,epyc10,epyc8, out typekvioft/ecoC, log intel2 ~/typekvioft/ecoC.log. A2/B3 left to finish, no further round on that recipe.
- earlyoom evidence (journalctl -u earlyoom): epyc2 18:23:42 openroad VmRSS 15.5 GB = form A DRT crash (18:23:46); epyc10 02:35:32 openroad 12.8 GB = B2 crash. FABLE-HARD-KV says Error 241 was a tool crash; both measured crashes here coincide with earlyoom SIGTERM.
- Bundle note: do NOT rsync with --exclude eco* (drops eco_loop.py).
