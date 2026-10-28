# CORES-EARLY-1 (2026-10-28): sign off the early-tapped hard cores that block die gates

## QC qfd_dv_s5_su8_rst3 (12 early taps on qc_k2b_phase12) -- SIGNED, view exported, pins 12/12 canonical
- Run: intel1:/srv/opentallas-scratch2/claude/qccores1-1027/rst3_k0/hold_b (QC-CORES-2 K0 re-sign, kit src
  claude/qc-cores-1027-rst3@478883e62a; 6_final.odb 2026-10-27 04:49:48, unchanged).
- 10-27 demotion cause (routed LEC KEEP FAIL, 16 replica flops) was fixed by that K0 RTL lane-0 fix: routed LEC
  EQUIVALENT 7234/7234 on 6_final.v sha256 c432381f... (= the current file; lec 04:52 > odb 04:49) -> resign_rst3/lec_routed.json.
- 10-27 autopilot STRUCTURAL pg-unbound (32cde8d976ee): the kit signoff.py had no PG census. Re-signed the SAME ODB with
  main tools/die_plan/signoff.py @aec2b2f471 (no physical step):
  - auto mode: NOT SIGNED only for hold_ff ff_ref_missing (the 10-27 kit SDC has one vclk = TT 250; no per-corner FF
    binding) -> resign_rst3/signoff_auto_ffrefmissing.json. PG census PASS 0/225032 open.
  - --ff-vclk bound-ff --ff-bound-ps 202.5 (METHODOLOGY 12.3 QC FF common latency, the option signoff.py provides for an
    already-routed core kit without insertion_ff_ps): **SIGNED** TT setup +100.89, FF hold +4.39 (sdc 2.86), DRV 0,
    DRC/antenna 0, pair skew TT/FF 37.9/35.9, PG PASS 0/225032 -> resign_rst3/signoff_bff.json (sha256 f34e0dbc...).
- Abstract: ORFS do-generate_abstract on the same 6_final.odb (LEF + tc/bc libs; odb mtime unchanged).
- View: tools/autopilot/export_view.py (main ca9fed98ec) -> qfd_dv_s5_su8_rst3/ (complete, problems none,
  pins_sha256 e56fadd2..., pins_canon a832b058...).
- Pin match (CORE-VIEWS-1 checks/match.py = die_sta_related.pins_relation) on qc_k2b_phase12: **canonical 12/12**
  (cores/su/signed/qfd_dv_s5_su8_rst3_pins.json). ETM clock tree TT 231.3-275.7 / FF 173.3-213.5 ps.
- Status: SIGNED-UNVERSIONED (no flow tag covers src 478883e62a); counts for the freeze gate after the QC flow tag
  (same condition COORD set for crh_rp1 f4g).
