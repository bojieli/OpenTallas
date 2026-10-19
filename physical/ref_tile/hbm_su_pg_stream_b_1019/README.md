# hbm_su_pg_stream_b_1019 (HBM d4g LIGHT SU slice stream sibling, ONE two-root tile; H.STA.BLK.15.3.2)

Kit generator: tools/ref_tile/specs_hbm_su3/mk_pg_stream_b.py. RTL top: ot_hbm_su_static_pg_stream_split
(rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_stream_split.sv, programme/multirate_bridge_split.sv).
Coordinator decision 07:11 (lanes/HBM-SAFE-PGSTREAM.md option b). It replaces the abutted one-root halves
hbm_su_pg_stream_q_1019 + hbm_su_pg_stream_s_1019 (2 x 432 x 216) with one 216 x 259.2 slot.

The banked 2,346-b seam now sits inside the tile as landed crossings. Bank registers on one root feed a 2:1 / 3:1 mux into a
register on the other root at a fixed calendar edge, with no handshake. The kit's spec `seam_windows` emits, for each group,
set_max_delay setup_q*q and set_min_delay -hold_q*q from the bank cells to the reader clock. Clock latency is included, and
STA still applies the sign-off inter-clock reserve (150/210 setup, 100 hold) on top. Generator:
tools/ref_tile/clock_entry_constraints.py seam_window_sdc.

| group | bank (root) | reader (root) | setup | rewrite-after-read |
|---|---|---|---|---|
| bridge_request | u_bq.rq_b*/wq_b* (clk_ctl) | stream launch / pipes (pg_clk) | 4q = 1111 ps | 2q = 556 ps |
| bridge_return | u_bs.rr_b* (pg_clk) | staging p[0] (clk_ctl) | 2q = 556 ps | 4q = 1111 ps |
| inject | u_s.ijb0/1/2 (pg_clk) | ijq (clk_ctl) | 3q = 833 ps | 7q = 1944 ps |

The bench (tb_hbm_su_pg_stream_split) checks exactly these per-group windows. Seam-window mutant MUT 12 reads the request
bank one stream edge early: the data and edges match, and only the window checker fails it. The reset synchroniser sources
(rc_leaf / rc_tap) and the pg-fault synchroniser are ordinary related-clock paths (1q).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: WAIVED, with the register in RTL. Every boundary bit is a register in RTL: request banks from vmr_cmd/su_wq,
  su_rr/ijq/fault synchroniser flops, LG tap in/out registers, and inject decode into bank flops. io_flop_at_pins (4 cols)
  places them at the faces. A wrapper stage would move the 3:4 seam calendar and the VM 10/7 calendar. Resets are landed
  in 3 clk_ctl stages (one epoch).
2 Reach: PASS. The tile is 216 x 259.2, so every face-to-face hop is <= 259 um < 405 um.
3 Fanout: PASS. Bank, launch and output data flops have no reset, which removes the old 5,652-load bridge_rst_n fanout.
  Bank selects are per-bridge counters.
4 Depth: PASS. Each seam arc is bank -> 2:1 (3:1 for inject) mux -> register. The inject decode is in the pg_clk domain
  before the banks. There is no combinational in->out path.
5 Storage: PASS. Banks are 2-deep (3 for inject) seam registers, not delay lines or runtime-indexed arrays over 2 kb.
6 Floorplan: aspect 1.2:1 PASS. No macros, and one full std-cell band. Pins sit on full faces at W 4.7 / E 4.6 / N 3.6 /
  S 3.6 per um (<= 6) PASS. Utilisation is WAIVED as pin-bound: 3,580 external pins on ~3,500 um2. At <= 6/um, W/E need
  >= 197 um, so the coordinator's ~150 x 150 estimate would be 8/um. 216 x 259.2 is the proven pg_stream outline
  (gate 0ff805777: GPL converged with routability ON, trial GRT overflow 0, CTS spread 60/57 ps).
7 Clock: two regional roots (related_pll_ratio 4/3, multiple_cts_roots). clk_ctl is at the S-face west end beside the
  serial register mass (W slice face). pg_clk is at the S-face east end beside the VM leaves / LG tap (E face). Seam arcs
  are landed crossings (seam_windows). Pin-flop spread must be <= 80 ps at TT and FF (gate). io_hold_margin is 0.03.
8 Schedule: PASS. The seam is static, with no credits. Edges are the TW3-PGSTREAM split edges (ij +1 serial, pg_fault +2
  serial, reset release +1 epoch, given to H-D4G). The slot change goes to H-D4G / TW5-HBM-DIE.
