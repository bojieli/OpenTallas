# FABLE-FIX-HEAD-SD9F handoff (Fable; owner of HEAD type hd_serdes form sd9f through sign-off + export)
Logs: intel2 ~/fable-fix-head-sd9f-logs/. Lane dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-sd9f.
Gates R-MINIMAL: DRC 0, routed TT >= -42, internal FF hold >= 0 (port hold advisory).
- Started 2026-11-17 10:2x PST. Input: NEEDS-FABLE bundle in HEAD-TYPES-R4.md (eco1-4: DRT 0 viol, clk_t8 + clk_t11 unrouted). Step 1: DB diagnosis of both BPINs.
## 11-17 10:40 PST state
- DB census (E7 lane diag1.out, script diag1.py; renders lane render_orig/site_{t8,t11,t5}_{all,m4up}.png LOOKED): every tap BPIN (M7, 0.032 x 0.768)
  sits INSIDE a reserved die clock-tree site (hard placement blockage + M1-M7 routing obstructions, CLKSITE-RESERVE-1115); 19 of 22 tap
  pins are covered on M1-M7, the tap buffer abuts the site edge.  Original DRT: 17 taps shorted straight through the M7 obstruction
  (19 M7 Shorts); clk_t8 / clk_t11 instead reached the pin from die-reserved M8 (VIA78 on the pin, M8 run 1.2-1.6 um, stack outside the site).
- R4 ECO DBs: clk_t8/clk_t11 keep their wires through 5_2e_geom/pre_drt/guided and have NONE after DRT (5_2_route.odb), every other net routed.
  They were never in the rip list; DRT itself discards the kept M8/VIA78 routes after the M7 carve and does not re-route nets that came in routed.
- Experiments running (E7 lane, plain detailed_route with the kit arguments on R4 eco4 5_2_route.odb = 0 DRC, the 2 nets wire-less):
  xa = as is; xb = same + clean guides for the 2 nets (M7 strip down the carved column + M6..M1 stack at the buffer; no M8).
  Scripts drt_x.tcl, run_x.sh, guides_b.py; logs xa/drt.log, xb/drt.log; client logs intel2 ~/fable-fix-head-sd9f-logs/x{a,b2}.log.
  NEXT: the first with unrouted.txt empty + 0 violations -> `ot-run --mem 96 --hosts epyc7 --dir LANE --stage E7:head-types-r4/sd9f_eco
  --stage E7:fable-fix-head-serdes/sd9f_lane -- bash LANE/run_fin.sh xa fin` (private kit copy LANE/fin/hd_serdes: fill, final, abstract, antenna,
  pin audit, signoff_fable).  Then export (ffht_export.sh pattern) to AGIdock + rtx-pro s81_head/hd_serdes__sd9f_fable_1117 + INDEX rows.
- Routed timing of sd9f was NEVER measured: the original kit stopped at PIN_AUDIT (extra 1088 = pma_rx pads, declared 1057/1057 ok) before
  signoff, and signoff.py on any hd_serdes kit died in golden.sdc: phy_clock_export.tcl opens /work/phy_clock_export_binding.json for write
  on the read-only sign-off mount (TT/FF NOT RUN).  Fixed in the lane kit copies (copy+mv, .gen_orig kept) and on the branch.
  Measurement of R4 eco4 6_final (2 nets unrouted, estimate only): LANE/meas4/hd_serdes/signoff_meas4b (client log so_meas4b.log).
- FLOW branch claude/head-clksite-tap-escape-1117 (E7 lane repo, NOT pushed yet; base main bc7521448860):
  60c22e5730d CLKSITE-TAP-ESCAPE-1117 gen_phys.reserved_sites_tcl: escape column (pin + 0.10 um each side, full site height) in the pin-layer
  obstruction over each interior tap pin + 3-site E/W placement pad of route-obstructed sites (per-site opt-outs tap_escape / edge_pad_sites);
  on the sd9f plan + placed pins it emits 27 columns, M7 pieces identical to R4's carve (val_flow.py).  db7b25b131a PHY-EXPORT-RO-1117.
  Tests: test_clksite_kit (6), test_phy_clock_export (7), test_reserved_sites/test_die_rows/test_region_form_straps/test_s81_ca_band pass.
  NEXT: push + READY once the routed DB proves the geometry (both nets routed, DRC 0).
