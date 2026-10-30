# Unsigned collar clock geometry correction

Base D34e3 actual collar pin table had clk at(88.872,44.424) despite clock_entries declaring centre(43.2,43.2); mk_c20 projected the kit clock to the centre and hid the raw-plan mismatch. clk_in also remained an M4 .192x.024 edge pin, failing current preflight clock geometry2 checks. No placement ran on that failure.

Fresh constructor moves actual raw clk to M5(43.224,43.2), clk_in to adjacent M5(44.664,43.2), both .048x.48 inside the existing entry island. 1557 other pins byte-identical;1559 names/outline/RTL/parameters/cycles unchanged; merged clock_entries[clk,clk_in] unchanged. No new clock domain or timing tolerance.

Candidate intel1:/srv/opentallas-scratch2/claude/codex-hbm-cores-1030/collar_clock_plan2, planSHA82ed3ca4c377, pinsSHAae70500553b2. G0 PASS0; G0C8errors/128pending-view EXACT error findings equal to D34e3 baseline (all8 inherited q_hub u_vmb core_faces; root clean). Whole-die G0C FAIL remains; no die freeze/adoption claim.

Personally viewed plan.png/context.png under `collar_clock_checks/review/ot_hbm_static_cfg_collar_idx256r_ae70500553b2`: uniform full-face data pins<=5.7/um, two centre clock pins inside existing island, no SRAMs/halos/walls, original dataflow partners unchanged. PASS-COND for unsigned trial PLACE only. Actual placed full r2r/clock/PDN review before GRT/CTS/route. Independent prior parent preplace approval remains; no new SIGNED/G3 credit.

Native12058/12058EQ+wrong-hint refutation from preceding659f33 source remains a logic receipt (only physical coordinates changed); fresh kit preflight must match the new plan canonical pins.

Initial constructor asserted the previously assumed43.224 centre, failed on the real88.872 pin and wrote no changed plan. Its separate first output dir is not a candidate; immutable failed preflight and assertion evidence retained.
