# DIE-HEAD-46 (HEAD die owner), 2026-10-30

## l46 = l45 + one-block hd_st_str fix (r2r + clock_reach), OWNER 12.20 fix-only
l45/l44 st_str kits (non-plan variants: l40 kit, l44 pinslot kit) still failed r2r 463 x4 and clock_reach 220.27.
- r2r root cause: the d_i landing ring status (u_cland_d_i ready/fault_state at (1386,358)) had ONE status input stage before the
  N-input collect, for agg (1035,250; 463 um) and d_o (1050,275; 420 um); the u_i ring already has two.
  Fix: clock.landing_status_input_stages agg.d_i += first stage (1210,305), d_o.d_i += first stage (1215,320) (all hops <= 230 um,
  +1 status cycle on d_i = u_i depth, 0 data cycles), their clock.sink_sites_um rows [1210,305,2],[1215,320,2], and the two new
  stages on local reset copy e.
- clock_reach root cause: plan clock.tap_radius_um 250 > the 220 gate (far sink = reset relays u_rrl/u_srl_45..76 at y 78).
  Fix: tap_radius_um 200 (the value wshim/eshim/tile/turn_b already use).  Variant l46b (radius 220) -> reach 221.91 FAIL, rejected.
- Built with the DIE-HEAD-43/45 event machinery (build_event_stable6 on input_l40 + edits_l46a.json = edits_l45 + the st_str set,
  chain.sh), then budgets.cland_pinslot_types as l45.  Plan diff vs l45 = partition_types.hd_st_str only (the edited keys + event re-picks
  of raw START relays: landing_reader/writer_start raw_reset, landing_local_resets raw, reset_start_raw_exports, landing_contract pins).
  RTL: ot_s81hd_st_str.sv + start_stages json; top RTL = +.clk_t17 on the 4 st_str instances (top_diff_l45_l46a.txt); sidecar = l45.
- source_plan sha256 bd1dd9ff3e306751116064b58f736b113712d1d538427d8ff546c021efdad25a (sidecar 02dececead4a = l45).
- G0C (main tools 4b5f73abea9, --completeness): l45 1 err / 18 warn, l46a 1 / 18, 0 new / 0 gone.
- strict bind (run_source_portbind.py at 4b5f73abea9): PASS, 358 inst, nested 6111 (l45 6106).
- die clock l46aa405 (l45 config, plan path only): GRT TT/FF overflow 0 (90713 nets), spread scaled 122.33/120.14, OCV stated
  149.78/142.16, duty 0 outside 45-55 (= l45; 12521 taps vs 12517).
- st_str l46a kit (main 4b5f73abea9, head_rekit_current.py): LEC EQUIVALENT 11275/11275, PLACE rc 0, AUTO-GEOM r2r 463.0 x4 -> 391.3 x0 PASS,
  clock_reach 220.27 -> 215.67 PASS, GRT 0.  Left: aspect/fill/empty (outline, standing), pin_reg_max 170.9 = START pins (COORD 15:44 3A),
  pin_reg_p90 64.4 = landing-ring pinslot form (FLOW-12 item, same as turn_b).

## wshim_rx on l45 (main 4b5f73abea9): LEC EQ 5403/5403, AUTO-GEOM = l45 line (reach 182.1, r2r 369.4); route launched.
