# s81dv_slice_lp_k8f -- FALLBACK landed slice parent ot_s81sl_slice_c3x_k8_cap5r_lp (c3x), S81-SLICE/PARENT 10-21 (pair: k8e)
CRITICAL prefix s81dv_slice: gate PNGs -> COORD-REVIEW-QUEUE; never REVIEW.json / submit.  DIAGNOSTIC while stand-ins remain.
Serves: HB=1 die slices s_4S (band q/pv) and s_3S (ot_s81sl_slice_iq: bo -> dsdv_idx_bsplit).  Die bind: parameter-free wrapper ot_s81sl_slice_c3x_k8_cap5r_w (landed/c3x_k8_cap5r/).
Generator tools/s81_slice/pl_slice/mk_slicep_k8c.py (RTL/records: mk_k8_cap5r_c3x.py).  Successor of k8a/k8b (synth FAIL
06:17: stale xfin view, no e_dd port).  Parent RTL = CURRENT: CLOSED capc5r (s81sl_capc5r-163d31541 / 4a4d275ee) + CAP
fixed-depth reset forests, u_xg ot_s81sl_xgt_xo (6468d5e7d), u_xr ot_s81sl_xrt3 (570.24 wide, bi/bo).
Children: CLOSED + current (LEF ports == RTL header, sources unchanged since closure): vq, rxsf, rxsb, vsw, vn x5, eg, capc5r.
STAND-INS (STANDIN_NOT_A_VIEW, OBS M1-M5, successor outline/faces): vp x5 734.4x864, ve x5 345.6^2, vs x5 172.8^2 (view
b5a2e98f8 stale vs SW-wr RTL 8158a1e89), xgt_xo 734.4x777.6, xrt3 570.24x395.28 (CLOSED xr3 not aliased),
xfin 345.6^2 (view stale: predates ENG 269ef81a1; SL-CHILD xfin_e2 outline).
Outline 1512.0 x 6868.8 (10.39 mm2), column channel 86.4; bands S->N L4 / L3 / C2 (leaf 2) / CC 3412.8-4622.4 / L1 / L0.
## SAFE checklist (8 points, 10-21)
1 pins: PASS -- all parent ports region C on the W/E faces of the C rows (C2+CC 2289.6-4622.4): W 6624 b / 2293 um = 2.9/um,
  E ~4.97 kb = 2.2/um (<= 4/um); io_flop_at_pins (21 cols) + keep_pin_regs; children register their own pins; reset: lp
  root -> per-region runs + per-chunk forests + 5 CAP region forests (cap5r), port net = 1 sink.
2 reach: PASS (gate measures) -- every leaf<->centre bundle crosses a D4/E2 landing; centre pairs adjacent: xg N -> xr (R180)
  W face 43.2 gap, xr cfg -> cap N ~60 um, xfin e_* -> eg ~380 um, xr x_* -> xfin S ~200-450 um; eg g -> xr eg_* ~700 um
  (35 b) is the longest centre wire: pin-registered at both ends, repeated reach measured 600-750 -> gate decides; if it
  fails timing the fix is a relay stage in region C (+1 edge on eg -> xr, priced), not a squeeze.
3 fanout: PASS by construction -- chunk-8 landings + kept enable (lepenh2 recipe, max 32), reset forests ROOT_LOADS 1;
  in-gate mapped census decides (owner 10-21: no new census campaign).
4 depth: PASS -- parent glue = relays / landing muxes (registered one-hot selects); no new logic.
5 storage: PASS -- no parent storage (4-slot static landing rings, chunked).
6 floorplan: fixed -- children on the 43.2 lattice (eg/xfin row, xr R180); channels 86.4 column / 43.2 rows, 21.6 between
  small children (4 x halo); outline grown to H 6868.8 instead of squeezing (k8a 6739.2 cannot hold xgt_xo 734.4x777.6
  + xfin_e2 345.6^2); hard 60% (std-cell fill of the free area is low); aspect 4.5:1 waived (die slice column).
7 clock: PASS (gate measures) -- 10 regional roots C / L0 / L1 / L3 / L4 / CAP_RT/CW/CE/RN/RS, every crossing landed
  (mesochronous ring, fixed latency); spread <= 80 ps TT+FF judged per region; hold margin 0.03.
8 schedule: PASS -- static; landed leaf<->centre +0 vs reference, reset +13, fault +3, CAP +12 capture edges
  (OT_S81_CAP5_C=1), xgt_xo xw_v/xw_d +1 / fault +1 (MU.S81.CAL); c3x = c1x schedule + xr3 band path (child-internal).
## Die finding (to S81 die owner)
Slot 1512.0 x 6868.8 vs plan 1252.8 x 6739.2: H +129.6 (row pitch 6912 -> street 43.2, or upper slice row +43.2).
c3x W +216 (MAIN) / +259.2 (FALLBACK) for s_3S and s_4S: columns 3 and 4 widen (die W 32648 -> ~33080: reticle!) -- die re-plan decision.
