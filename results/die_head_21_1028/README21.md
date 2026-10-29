# DIE-HEAD-21 (2026-10-28)
Branch = main 6a56d58118 + FSTART a769e0b2de (approved 08:35, released 12:3x, never merged) + die-head-20@3e6b1671e8.

## 1. DH19 diag run stopped; class of the stuck repair (CHECKED own)
- intel1 dpkit-hd_tile-2789721 stopped at repair_timing it 1100: WNS -86.9 +-2 since it ~150, 2301/2301 endpoints.
- step1/ring21*.tcl: STA on the DH20 GRT-only odb + SPEF (no repair). Worst -130.6 = cland_fstart_in_i (vclk 525 + 166.6)
  -> 384 ps buffered t_rst_n fanout -> 2272 ring writer DFFE muxes, captured by fclk_in_i defined with source latency 0.
- Clock-definition artifact: the forwarded clock reaches the port at sender fwd_out + wire (TT 158.1-163.5).
  Fix = claude/die-head-21-fclklat-1028 (plan edge_clocks[].source_latency_ps); probe worst +27.5, 0 fail.
  (ring21c used 186.1 = writer-CK arrival, which double-counts the receiving fclk tree.)
- Real residual: read crossing set_max_delay 356.5: r_v -88.6, r_lap_ok -60.0 (decode logic, repair scope, UNCHECKED).

## 2. Regeneration from main + FSTART (CHECKED own)
- gen rtl --clock-landing (Codex sidecar) on plan_hd_tile_525 -> 69 u_cland_fstart_* face flops / 16 types (= DH10).
- mk_kit21.py: hd_tile kit; vs DH20 kit only RTL differs; SDC identical.
- Synth (ot-run intel2) + face_guard with land_slots: 1143/1144, only cland_fstart_in_i: 8 loads on u_cland_origin/p_start
  (face_guard_fstart_merged.json). cland_fstart_out_o cleared. fstart_in needs the input-side relay (ASK).

## 3. head_count_strap_sites.py (Codex, codex/head-die-1028-0405, unchanged) + test (4 tests)
- Re-run on Codex plan_rs.json with main tools: report byte-identical, sites identical to plan_rs_countsites_fullpin.json
  (that file differs only by the later corner-view path aliases) (CHECKED).
- Note: plan_hd_tile_525 hd_tile count sites (x 129.6-146.9, y 349.9-358.6) were placed against the pre-ring_ff band
  anchor; they are still legal (outside macro halos / reserved sites, CHECKED) but ~430 um from the new band i.
