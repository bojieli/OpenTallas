# dsdv_seq_host_c -- S81 seq_host compact core parent (DIAGNOSTIC kit)

S81-SHLK/PARENT re-kit, 2026-10-19, branch `claude/s81-shp-1019`. Source spec `tools/ref_tile/specs_pl_seq/dsdv_seq_host_c.json`;
regenerate with `python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs_pl_seq/dsdv_seq_host_c.json`.

Wires-only parent `rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv` (PL-SEQ option B), one clock region `ck`, outline 345.6 x 648.0 um.

| inst | child | view | slot (x, y) | size |
|---|---|---|---|---|
| u_l0 | dsdv_sh_lk | STAND-IN `standin/dsdv_sh_lk` (RL 1 outline-grow --cts odb, `STANDIN_NOT_A_VIEW`) | 43.2, 43.2 | 254.88 x 151.2 |
| u_l1 | dsdv_sh_sq | CLOSED `physical/ref_tile/dsdv_sh_sq/views/dsdv_sh_sq` (closure baa6e2280, native PASS ef5587213; SRAM walker) | 43.2, 216.0 | 254.88 x 151.2 |
| u_l2 | dsdv_sh_vc | CLOSED `physical/ref_tile/dsdv_sh_vc/views/dsdv_sh_vc` (ce989b78c) | 43.2, 388.8 | 226.8 x 213.84 |

Channels lk-sq 21.6 um, sq-vc 21.6 um (was 51.84 with the old 120.96-um sq); the 43.2 lattice plus the 20-um channel rule leave no
closer vc origin, so the outline stays 345.6 x 648.0. The closed lk view on main (ef442ffba) is NOT used: it carries the RL 0 interface
(`ck_ih` / `ck_ic` pins, which the RL 1 parent RTL no longer has) and fails the own-R audit (spread 94/88). The lk structural redesign
(dsdv_sh_lk_sr9, 518.4 x 280.8) runs in another lane; this kit is re-packed again when that view closes. DIAGNOSTIC: no submit.

## SAFE-DESIGN checklist (owner 10-19)

1. Pins: pin regs OFF -- waived: wires-only parent, every parent port goes straight to one leaf pin and each leaf is flop-first /
   flop-last at its pins (lk RL 1 rung landed at both faces). Reset: `reset_landing` 2 stages at the parent face (PASS; +2 reset-release
   edges, a scheduled constant), and sq / lk land reset again inside (2 stages each).
2. Reach: longest parent wire ~50 um (ck/rst_n E pin to sq E face; vc N face to the N edge 45 um); child-to-child 21.6 um. PASS (< 405).
3. Fanout: no parent logic except reset landing + pin hold pads. PASS.
4. Depth: no parent logic; no combinational in->out path in the parent (leaf boundaries registered). PASS.
5. Storage: parent none. sq calendar moved to 2x ot_sram_1r1w_128x256 (fixed in the sq view). lk flop storage (16x514 / 16x289 /
   8x289) is owned by the lk SRAM redesign -- waived for this diagnostic only.
6. Floorplan: children on the 43.2 lattice (x 43.2; y 43.2 / 216.0 / 388.8); aspect 1.88 (<= 2); fill = hard children ~56 % of the
   outline. Face pin density 10.5 pins/um on S (lk vo_s) and N (vc cw_d) -- waived: inherited from the closed leaf faces, pins go straight
   out (the 10-18 gate pin-geometry check: 0 inaccessible). route.pin_balance {group_max 1, M4 M6 / M5} gives every >32-b abutted
   bus a defined bit order (gate pin_order). No std-cell band needed (no parent logic beyond pin/reset cells).
7. Clock: one region (parent < 1 mm, 0.35 x 0.65 mm: no landed crossings needed), spine on `ck` with hard-child macro leaves; judged per
   linked child pair u_l0-u_l1 / u_l1-u_l2 at child boundary flops, TT and FF <= 80 ps (gate `clock_child_pair`). io_hold_margin 0.03. PASS
   pending the gate numbers.
8. Schedule: static; rung 5 edges each way in-parent (record results/arch/landed_parent_1018/dsdv_seq_host/core_b), host path golden + 2,
   sq walker 0 added data edges; parent reset landing +2 reset-release edges handed to the die schedule.

Bench: `rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_c_bench.sh` now lists `ot_dsdv_walk_issue.sv` + the SRAM model, runs the pair seeds and
mutant 10 (as run_seq_host_bench.sh). Run it on the fleet only.
