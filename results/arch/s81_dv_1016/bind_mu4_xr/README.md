# BIND mu4 / xr: C3 band port B is 513 b at the source (10-19)

Strict bind of the final mu3 die (ceaed19c4 vs the 58fc checker) had 1,182 unread bits on `u_s_3S/u_s_4S .bo`:
header bits 1..51, `pk[1023:512]` (bo 564..1075) and the 28-bit zero pad (1076..1103). The cause was `ot_s81sl_xr`
g_bo, which registered the whole 1,104-b SEND word on B.

Census: B is point-to-point. Slice `bo` goes over the two `q_{W,E}` lanes to `dsdv_svc_rs_entry.q`, and from there to
`ot_s81_svc_job.q`. That port reads `q[0]` (valid) and `q[512:1]` (one 512-b word). Nothing else on the die reads slice
`bo`: no bench, no die path, no other master. The single-user/MU table `q.o` rule only ever carried `bo[0]` plus
`bo[52 +: 512]`. The compiler (`dv_layer_compile.py`) did not lower any send config (CTL target 4) before this change.

Change (no added cycle; bo_r stays the same register stage):
- `ot_s81sl_xr`: new parameter `BW = 513`. `bo = {pk[511:0], 1'b1}` is registered when a send goes to B. A dir-B send
  config with pairs > 2 (`body[42]`) raises the sticky `fault` (`f_bw`). Bench mutant `OT_S81SL_XR_MUT_BWIDE` removes
  that check.
- `bo [512:0]` is propagated through `ot_s81sl_xr3`, `ot_s81sl_slice` (C1 `513'd0`), the c1x/c3x flat and landed
  variants, the lep and lep_mu wrappers, `lpwrap`, `slice_flat_gen.py` and the benches. `dv_spare_out` class D now
  covers C1 bo 0..512.
- `dv_layer_compile.send_cfg()` encodes the send body and refuses a B send with more than 2 pairs. Test:
  `test_send_cfg_b_width`.
- `mk_table_p4l3_mu.py band_b_513()`: `q.o` is now `bo[275:0]` -> lane 0 and `bo[512:276]` -> lane 1 bits 0..236.
  `rtl_widths.bo` is 513.

Entry `q` stays 515 b. Bits 514:513 are `{fault, live}` of the shared `ot_s81_svc_job` die-pin protocol (s81_ph svcio
kits), not part of the q word. Narrowing the port would only move that tie inward, so it is left to the svc owner.

Benches (fleet ot-epyc7, Verilator 5.050, units oth-ubuntu-348728-1792452932 / -363449 / see summary):
base HB0 s1/s2 PASS, base HB1 s1/s2 PASS (431 / 510 B sends checked bit-exact, 14 illegal programs fault),
mutant bwide HB1 FAIL (`XRFAULT case=14 fault=0`, witness `bwide_s1_hb1_run.log`), hops HB1 FAIL as before.

Kit: no `s81sl_xr3` or C3 slice kit/closed view exists (only `s81sl_xr1`, HB 0, whose netlist is unchanged: bo is a
constant there). xr3 kit owed as before.
