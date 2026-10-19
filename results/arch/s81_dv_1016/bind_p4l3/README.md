# p4l3 real-view bind (S81-LBGAP/G3, 10-18)

`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4l/plan.json --out <scratch>/bind12 --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3.json`
(117 s, 270 MB; table from `bind/mk_table_p4l3.py`). Strict die_port_bind: **PASS** (failing 0, params_not_in_rtl 0, undriven 0, open bindings 0).

Closes LAYERBENCH-S81 gaps (results/rtl/s81_layer_tput_1018/slice_bench/gaps.json on claude/layerbench-s81-1018):
- **G3** landings 224 -> 276 (+52, every one with a land-plan E from landing/p4l2): end slices u_s_0S/0N/7S/7N inbound
  xrW/xrE line lanes (16, dsfd_dvland_276, E 4-5), tvN/tvS rungs (4, dsfd_dvland_276l, E 8-9), staged frame returns
  r_f_0*/7* (24, dsfd_dvland_70, E 2-4), and slice -> PHY lt_lk_* (8, NEW dsfd_dvland_512, E 3). 0-stage returns stay unlanded.
- **G4** frames: `col_h9_l4 / col_h10_l4 / col_h9_MX_l4 #(.INSTANCE("u_<inst>"))` on all 122 frames (ROM image per frame,
  same naming as dv_slice_cut --rom-instance).
- **G5** lep masters parameter-free (no `#(.HB(0))`); tools/die_port_bind.py now checks INLINE parameter overrides
  against the RTL (before: sidecar only) and parses typed `parameter string/logic/...` declarations.
  Witness `witness_g5/`: the die7 bind10 die.v (with HB) FAILS the new check: params_not_in_rtl 3 (lepw/lepe/lepe_nh HB).
- **S-tier map** (S81-LINKTO, coordinator 0hn decision 2): lk_WS0 / lk_ES0 -> ot_pdie_serdes (pma_tx 544), ch_b strap 1'b1,
  ot_pdie_ucie 0 instances.

Owed (die lane): closed view for dsfd_dvland_512 (8 inst; no ref_tile yet -- 70/276/276l/562/682 exist); landing K for the
new lanes comes from landing/p4l2 E (die STA re-derives on the next real-view chain).
