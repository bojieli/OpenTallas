# ot_s81c_attn_hcore WPRE route gate (S81-P10/P11, 2026-10-24) -- NOT SIGNED

Kit `kits/ot_s81c_attn_hcore__157.68x259.2_wpre` (RTL WPRE opt-in, 89c161bd5 / 212da8d904; old-generation core kit SDC).
Run epyc2:/srv/opentallas-scratch/s81/hcore/ot_s81c_attn_hcore__157.68x259.2_wpre (ot-heavy oth-ubuntu-80375), route DONE 10-24.
- route: DRC 0, antenna 0, pin audit PASS 1214/1214; ORFS finish TT worst slack +29.62 ps (was -25.29 ps / 88 endpoints, 10-23).
- signoff.py (main tools, TT setup / FF hold): **NOT SIGNED** -- setup_tt PASS +29.62; hold_ff FAIL -8.90 ps / 532 endpoints;
  DRV FAIL (max slew TT 417 / FF 390); spread TT/FF 25.61/23.21 PASS; sdc_lint FAIL 30 (old kit SDC: regexp port filter,
  plain set_output_delay waives seam hold, 30 ps inter-clock uncertainty); face_guard FAIL shared 9.
- Verdict: the WPRE RTL fix removes the -25 ps ld_grp setup failure (TT +29.62); the core still needs a re-kit with the current
  core-kit standard (SDC lint, face_keep, FF hold repair, DRV) before it can sign.
