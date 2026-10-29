# LP reset contract and inherited failure collection

The LP lane hard children use the existing S81 external reset contract of at least
64 clocked edges. The additive module list change names both identical-body lane
wrappers; it changes neither the reset duration nor a timing/LEC threshold.

Actual source connection: `physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lepw_mab_hbc_prod_mu_72.sv`
drives `u_ln0..3.rs` from `lpr_N0..3_v[0]`. Each path is the parent
`ot_pl_pad(N=1)` followed by `ot_pl_land_reset_forest(DEPTH=3,LEAVES=1)`.
The west and east wrappers in `rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv`
wire that reset directly to the same `ot_s81ph_coll_lane_safe4.rs_n` and its
`ot_rst_relay_tree3`. Native32, REACH=2 has 223 internal leaves.

`tb_lane_reset.sv` uses those actual modules and the original S81 proof's
`cells.sv`. It exercises 65 die relay depths, three same-frequency clock phases
(0, +200, +600 ps modulo the 833-ps period), cold and warm reset:

- HOLD64: every child reset pin sees at least 66 known-low edges; all 223 lane
  leaves simultaneously see at least 69 known-low edges. PASS.
- HOLD61 control: child reset pins see 63 edges, and `BELOW64` catches the wrong
  duration on both cold and warm runs. CAUGHT.

Run receipts are `good.log` and `mutant.log`. The proof was run with ot-run on
intel2 in `/srv/opentallas-scratch2/claude/codex-s81-lp-0825/reset`, unit
`oth-ubuntu-1996205-1793287669`. A first testbench incorrectly used inertial
delay for the 600-ps phase and filtered all its clock pulses; its FAIL logs remain
in that run directory. The corrected bench uses independent phased oscillators.

The original die proof and receipt hash remain unchanged in the reset contract.
This proof justifies extending its hard-child inventory. It does not claim full
LP LEC, placement, timing, or sign-off.

Inherited LP2a LEC stopped before placement: 33,378/33,468 compare points proved,
90 differed (12 direct failures plus 78 unresolved points), and 7/3,742 kept
register bits were missing. That kit had no reset contract, so used four edges.
Its original failure remains immutable. An isolated copy of that exact raw
netlist is running a diagnostic 64-edge LEC at
`intel2:/srv/opentallas-scratch2/claude/codex-s81-lp-0825/rc64`, unit
`oth-ubuntu-1933256-1793287550`. No running inherited kit was changed.

No data or control cycles added.
