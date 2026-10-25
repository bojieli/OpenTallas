# S81 adopt178 integrated bind (TOK-DS/BIND, 2026-10-25)

Plan: main's adopt178 `physical/die_plan/s81/die_plan.json` (sha256 a2fdf1ab…, 178 types / 399 partitions / 860 lanes,
`reset.release = "wavefront"`). Plan NOT changed. CLOCK-RESET start broadcast (claude/clock-reset-1025@e84452a8fd)
is NOT on main, so it is not in this bind (wavefront-only reset, as on main).

## Sources (branch claude/tok-ds-bind178-1025)
- `rtl/`, `tools/s81_dv/`, `physical/die_plan/s81/bind/`: the merge-tree result of origin/main + codex/s81-portfix-1025@6246d2d30
  for these paths only (PORTFIX boot/fault/dead ABI, C3 RTLC, XG padding, 24 frame forwards, IDXNET six lanes + 4 reserve
  PHYs, qfs, TP leps). Auto-merged with no conflicts. The CODEX branch's plan, G0 and latency files are NOT taken.
- NO F2B sources (COORD gather ruling B: full-width fold rung; F2B RTL not adopted).
- `tools/die_plan/bind.py`: CODEX's opt-in `asbuilt.io_roles` (it was an uncommitted patch on epyc1) + its test; a fix so an
  EMIT failure under wavefront reset is reported instead of a `bind_reset.json` traceback.
- `physical/die_plan/s81/bind/bind178_manifest.py`: builds the as-built manifest from CODEX PORTFIX r6. Main's newer RTL wins
  over the CODEX r6 cache copies (12 files differ, e.g. ot_s81sl_xrt.sv deskew, ot_s81sl_slice.sv, vn/vq, kv_bank, idx_tree, l20s, the lep files).
  cap30 as-built sources stay a frozen snapshot (as on main's asbuilt_s81_*.json).
- As-built netlist: PORTFIX `die_pf.v` -> `frame_forward_bind.py` (24 links, 26,496 b) -> `idxnet_die_bind.py` (6 lanes, 4 reserve
  PHYs) = `asb/die_b178.v` (it equals CODEX's die_idxnet.v minus the 44 F2B lines).

## Result on the main plan: strict bind FAIL (22 errors), no RTL emitted
Run: epyc1 `/srv/opentallas-scratch2/claude/tok-ds/bind178` (unit oth-ubuntu-577318-1792930899). elab: 119 modules, 0 undefined.
proof: unbound 11,718 / tied 0 / undriven 0 / multiply-bound 0; 398 partitions mapped; TYPE_SPLIT 0 (io_roles fixes the 3 SerDes splits).
Every error is a PLAN gap. None is an RTL or tool gap:
1. 11 attnh fold lanes (svc pairs 0-1, 2-3, 3-2, 4-5, 5-4, 6-7, 7-6, 9-8, 10-11, 14-15, 15-14) are 1068 b beats 2 in the plan.
   The full-width fold RTL needs 2133 b, so each lane has 1065 unplanned bits (1062 on 14-15 and 15-14). 11,709 b in all.
   This is the ruling-B plan delta (owner: S81-PLAN/FTCHAN).
2. 9 one-bit PORTFIX fault feeders with no plan lane: bk_sel->gunit, eng->svc_14, gunit->s_3N_C, iqf->svc_0, phy_hbm->svc_8,
   s_0N_LP->s_0N_C, s_0S_LP->s_0S_C, s_7N_LP->s_7N_C, s_7S_LP->s_7S_C. Owner: the S81-PORTS faultfeed delta.
3. EMPTY_PARTITION s_5N_x06 (type slice_station__t19 has 0 buses, 0 ft slots and 0 contents). The wavefront reset tree still
   routes bk_sel's reset through it (parent s_5N_L4 -> s_5N_x06 -> bk_sel), so EMIT stops with "wavefront reset carriers lack
   bound partitions" and no RTL is written. Delta: drop s_5N_x06 and re-derive the reset tree (PORTFIX decision 5 / S81-PORTS).

## Previews (NOT port-bind PASS, NOT the adopted plan)
The elab is plan independent, so both previews reuse the main-plan elab. Runs are on epyc3 under the same run dir.
- `out_preview` uses main + delta 1 (attnh 2133 b, beats 1) + delta 3 (s_5N_x06 dropped), made by `bind178_preview_plan.py`.
  Result: 10 errors (the 9 fault feeders + EMIT); unbound 9, tied 0, undriven 0, multiply 0.
- `out_ff` is the **adopt178+faultfeed preview, not main**: S81-PORTS claude/s81-faultfeed-1025@3a58b44a01 die_plan.json
  (9 feeders, s_5N_x06 removed) + delta 1. Result: **1 error**. unbound 0 / tied 0 / undriven 0 / multiply-bound 0 /
  TYPE_SPLIT 0; 398 partitions, 177 types, 869 crossings, 606,165 b. The 1 error is the blocker below.

## Remaining blocker: the binder cannot deliver wavefront reset to plan hard cores inside as-built leaves (tool/as-built gap, not a plan gap)
`EMIT wavefront core reset col_h10_r0_p1__t1/u_r0.u_e0.rst_n: expected one bound leaf, found 0`. The wavefront plan sends a
reset tap to each plan hard core: 2,787 targets in 118 soft types (col frames u_r*.u_e*/u_bn*, svc u_rsv.u_att...u_hc.g_h[*].u_c,
leaf u_lf.u_ve/u_vn, slice C u_c.u_eg/xf/xr). The cap30 as-built binds those partitions at frame/leaf level
(col_h10_l4_lp_* u_core, etc.). The cores are nested *inside* a bound leaf, and `Binder.emit_type` only matches bound leaves,
so EMIT stops and no RTL is written. Fix options: (a) the binder threads a hierarchical core reset port into the leaf, or
(b) the manifest dissolves the frame/svc/leaf parents down to the plan's hard-core instances. Option (b) is the as-built
equivalent of the split cores. Until one lands, no wavefront S81 bind can emit RTL, on any plan.
The binder's wavefront code was only ever tested on fixtures (test_bind_wavefront.py).
With release != wavefront the bind would emit (plan reset change, not allowed).

## Cut flow (tools/s81_dv/dv_slice_cut.py)
The bound top cannot feed the cut flow as it is. Its shape: `s81_bound_top` = 398 partition instances (plan names,
s81p_<type>), with the lane flops (ot_dp_st), lane pads (ot_dp_dly) and reset relays inside the partitions. dv_slice_cut
needs a flat dv_die: instance lines named u_s_*/u_f_*, relay class dsfd_dvrlyh_/dsfd_rly_/dsfd_dvland_, and a dv_rtl_kit +
port_bind.json built from git-ref RTL. Two ways to feed it:
1. Now, with no adapter: `asb/die_b178.v` is a dv_die netlist in the same format as bind9 die.v. It carries all PORTFIX,
   IDXNET, frame-forward and reserve-PHY wiring, with real RTL on this branch. Lane timing there is the as-built cap30
   relay chain, NOT the adopt178 priced lane cycles.
2. Once the bound top emits: a small adapter. (i) The cut instance set = plan partition names; instance_map.json maps the
   old u_f_* names to fE*_p*_b*, and P_core_INSTANCE carries them. (ii) Run with --no-grow, because lane registers live
   inside the partitions and partition ports are the cut boundary. (iii) The kit = bind.f / out/rtl instead of git-ref RTL.
   (iv) Drive clk_<domain> + rst_n (wavefront; the release offsets are in bind_reset.json).
