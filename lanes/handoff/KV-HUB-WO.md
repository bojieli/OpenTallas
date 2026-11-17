# KV-HUB-WO handoff (Sonnet; class f5fa4d600f, type kv3_hub_Wo; 2026-11-16 ~20:3x PST)

## Finding
- Failing bands (7yhr attempt_4, same coordinates in HG2c plan fac383f38bc4 plan_c.json, so HG2c does not fix it):
  clock.landing_raw_branches stage 1 of `fs_o_idsrc_WN_y` (535.976,669.3) and `fs_o_seq__g_fan_N__u_fan_kc_d1` (535.21,669.3).
  Each is a 4.32 x 4.32 um window (18.7 um2) for 2 literal local-reset flops (need 0.9 um2, ratio 0.05). The two windows also overlap each other by 3.5 um.
- NOT band size, NOT macro, NOT PG, NOT tapcell, NOT reserved clock sites (no cland_avoid_rects/di_rects in this kit, no blockages in the window, rows full width).
- Cause: ft-station flops landed FIRM before the raw bands (face_flops.tcl OT_FACE_FLOPS landed ft slots) form a comb over x 522..543 um, y 660..680: in all 16 rows a 1.080 um DFF every 2.160 um. Free gaps are 1.080 um; the packer fit width is the cell family width 1.188 um (cland_family_w), so no gap fits. Measured by DIAG dump of cland_occ in a copy of the kit (epyc10 kv-hub-wo/exp1.log, exp1.diag).
- A site-ful free strip exists at x 543.3..553.1 (only tapcells at 553.176) in the same rows.

## Fix (plan delta on HG2c plan fac383f38bc4, no core reshape)
Move 2 stages (type kv3_hub_Wo, clock.landing_raw_branches):
- fs_o_idsrc_WN_y stage 1: (535.976,669.3) -> (545.6,669.3)
- fs_o_seq__g_fan_N__u_fan_kc_d1 stage 1: (535.21,669.3) -> (550.5,669.3)
Hops to neighbours stay <= 382 um (< 400 tap pitch / 405 reach).
Delta file: lanes/handoff/KV-HUB-WO-delta.json; applier epyc10 /srv/opentallas-scratch2/claude/kv-hub-wo/delta.py SRC DST; patched plan copy epyc10 /srv/opentallas-scratch2/claude/kv-hub-wo/delta/plan_c.json.

## Proof (copies only, no live kit or tree touched)
- plan_gate_pre check on the patched plan copy: PASS findings=0 (delta/proof.txt).
- landing_place.tcl diff old vs patched plan: exactly the 2 literal-local-reset rects change, 2282 lines otherwise identical.
- Real placement on a copy of the 7yhr attempt_4 kit with those 2 rects: 3_3 landing dry pass 0 BAND FAIL, "OT_CLAND placed 70435 actual mapped cells FIRM" (epyc10 kv-hub-wo/exp2.log; the rest of 3_3 still ran when this was written, not claimed).

## Next for KV-R
Fold the delta into KV's next tree switch (D10 or later), same switch, no separate one. After the switch relaunch kv3_hub_Wo place once; first place pass is the final proof. If a new tree moves the ft stations, re-check that the two windows are still comb-free.

## F1 kv3_hgi_v8 fs_ft11_o stages 1,2 (HG3 006e38e15a71; from FABLE-PLAN-KV-HG3 via COORD)
- Kit generated from the HG3 tree (gen.py phys, kit_rtl from KV-HG1 hgi_v8 rtl). KV-R preflight cland_band_sites (origin/claude/kv-r-cland-band-preflight-1116 @6f8c943e9ea) reports exactly 2 errors: u_cland_raw_fs_ft11_o_1 and _2, best gap 0.756 um < 1.188 (51 and 48 FIRM ft cells touch the windows).
- Delta (lanes/handoff/KV-HUB-WO-v8-delta.json): stage 1 (1213.92,762.408)->(1215.0,771.048), stage 2 (1213.92,375.684)->(1215.0,391.074). Candidate windows: best gap 4.32 um (11 and 10 cells touch, full free rows).
- Proof on copies: plan_gate_pre PASS 0 findings; regenerated kit differs from the unpatched one in exactly the 2 rects; preflight on it 0 errors. NOT done: a real landing pass, because no hgi_v8 ODB exists (needs synth+floorplan+3_2 of the type); preflight is the static twin.
- exp2 (Wo placement copy) had already exited (3_3 Error 247 after the landing pass, no process left); nothing to kill. No leftover job of mine on epyc10.

## exp2 error 247 (COORD question)
- Not a design failure and not a copy-kit artifact. rc 247 = SIGKILL (-9 & 0xFF). Cause: PLANGUARD in /usr/local/bin/ot-oom-age (--guard-s timer): /var/tmp/ot-oom-age/kills.log on epyc10 "2026-11-17 04:55:54 GUARD SIGKILL 1243805 openroad RSS 5528 MiB adj 571: MemAvailable < 5 percent with a plan job running". epyc10 MemAvailable was 5.78% at 04:55:02 and a plan job (hg1A bind kit-rtl, unit 1708832) started 04:56:20; container scope ended 04:55:55 after 27m27 (5.3 GB peak).
- Not OOM: no earlyoom action, no kernel OOM in that window, peak 5.3 GB under the 12 GB admitted. Last log line is GPL iteration 170 (overflow 0.64), no error text. The Wo landing pass (0 BAND FAIL) was already done before the kill.
- Fix: nothing in the design. The relaunch is exposed to the same guard whenever a plan job runs on a host under 5% MemAvailable: retry on rc 247 (the remove-conservative-limits rule allows reset retries), and prefer a host with MemAvailable well above 5% when launching an ~8-30 min place. The real kit run uses the same path (youngest build process dies first).
