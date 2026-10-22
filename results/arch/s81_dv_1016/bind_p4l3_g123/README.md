# p4l3 + G1 + G2 + G6 bind (LB2-S81 L0 integration, 10-18)

Branch claude/lb2-s81-l0-1018 = claude/lb2-s81-cc-1018 206291806 (CC forks svc/vs/xs/vpx) + S81-LBGAP g1 995f717a2 + g2 3eee44b8d + g3 5cb5cddc3 + lb2-s81-run 89fd9969d.
`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4l/plan.json --out <scratch>/bind --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3.json` (4.4 min).
Strict die_port_bind (G6 child closure, --prefer-list + --ref-tile-prefer): **PASS** masters 40 / instances 8,391, unresolved_children 0, ambiguous_children 0, variant_children 20.
Composition check: 276 landings (G3) = 276 hop-0 ICGx4 gates (G1), 122 frames #(.INSTANCE) (G4), lep masters parameter-free (G5), rstop sid 2c+r (G2, RTL).
Worktree note: the strict child closure needs physical/ref_tile/*/spec.json + */src/, physical/rom_host_ingest/ and physical/asap7_memory_macros/*/*.v in a sparse checkout (else "no RTL" / AMBIGUOUS children).
Open: G8 (bundle lanes with unequal E tear multi-lane beats; slice_bench/gaps.json) -- K straps here are still K = E per lane.
Sim kit list `sim_kit_sources.f` = `die_kit_sources.f` with the four dscoll_lane_w_rt closed-view SNAPSHOT files (ot_s81ph_coll_lane / mem1r1w / link_gbx / link_ep)
replaced by rtl/ (+ rtl/common/ot_link_credit.sv, a new child of the rtl/ coll lane): ot_s81sl_slice_lep.sv instantiates dsfd_coll_lane_w/e #(.LCR(1)) and ot_s81ph_mem1r1w #(.WREG(1)) .rst_n, which only rtl/ has
(Verilator 5.050 PINNOTFOUND x6 with the snapshot, ot-epyc5 10-18 19:05). This is G7 (owner S81-LINKTO: close dscoll_lane_*_lt from rtl/);
the die kit's --ref-tile-prefer pick is wrong for the lep slices until then.
