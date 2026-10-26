Reusable delta:
 python3 physical/die_plan/s81/apply_phy_control_pins.py INPUT_PLAN --out OUTPUT_PLAN --repo REPO --report projection.json
Generator gen_plan_v4 invokes the same helper. Scope: S81 sole hard ot_hbm3e_phy_v41x_aw30_e8p5 content; no other type/bus/FT/lane change.
Requires companion gen_phys.tap_points hard-native exact-coordinate fix in the same source commit; otherwise the generic1um clock/reset collision heuristic would move the native reset pin away from the LEF contact.
Selected measured vehicle: A19d115f3aa plan; copied own runtime epyc1:/srv/opentallas-scratch2/claude/codex-s81-phy-reset-2144/plan/candidate.json. Current-tool fullG0C receipt g0_report.json, BOOTledger boot_delta.json. Baseline invalid788.4 retained wf_solve_comparison.json.
Four focused geometry/native-pin tests PASS: exact pin centers+actual type_macros origin, missing-native-pin negative control, invalid-origin/halo rejection, exact192nm hard contact preservation while soft default remains unchanged. No RTL arithmetic or internal pipeline edits.
Apply this reusable helper to later A21/other S81 batch candidates and run their own current-tool gate; A19receipt does not qualify unmeasured future plans.
