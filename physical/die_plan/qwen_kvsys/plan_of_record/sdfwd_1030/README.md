# DIE-KV-49-SD 2026-10-30: kv3_sys_SD / kv3_sys_SD_v1 forwarded-clock export buffer (one-block fix, 12.20 freeze)

Cause (CHECKED, kits48b intel1 /srv/opentallas-scratch2/claude/die-kv-47-sd/kits48b): both SD types export 3 forwarded
clocks (fclk_out_o_serdes_{W|E}_rx_flit, fclk_out_o_serdes_{W|E}_tx_up, fclk_out_cland_up; source clk). The default
landing_export_form "tie" joins each output BTerm onto the clk root net, so TritonCTS sees the port's divide_by 1
generated clock on the clk net: kv3_sys_SD_v1 4_1_cts "CTS-0114 Clock fclk_out_o_serdes_E_rx_flit overlaps a previous
clock". kv3_sys_SD has the same 3 exports (it stopped earlier, at 3_5 DPL-0033, see below).

Fix: clock.landing_export_form = "fwd_buffer" (FLOW-GEN-2 shared opt-in, on main since 10-28) on these 2 types only.
mk_sdfwd.py applies it fail-closed (the JSON differs only in those 2 keys).

Proofs: G0C 28 -> 28 errors, 2055 -> 2055 warnings, 0 new / 0 gone findings (intel2 die-kv-49/sd_g0c vs g0c_b1);
KV die clock replay sd49 vs rx49: tree.json + ctree.v IDENTICAL (intel1 die-kv-49/clk/sd49).

Kit-local (not plan): the kv3_sys_SD 3_5 DPL-0033 is a CLAND FIRM INVx1 placed abutting TAP_TAPCELL_ROW_56_17019.
Timing-driven GPL then resized it in place to INVx3, which put it 108 dbu over the tap (probe: 3_1 INVx1 PLACED ->
3_3 INVx3 FIRM). Fix = OT_CLAND_FIT_RESERVE=resize (FLOW-6) in the SD kits. The plan switch budgets.cland_fit_resize
is die-wide, so it is not set here under the freeze.
