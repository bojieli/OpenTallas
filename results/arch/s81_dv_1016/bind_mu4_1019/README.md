# S81 GEN mu4 strict bind (LEAD2-S81/BIND, 10-19)

Branch claude/s81-bind-mu4-1019. Base: final ceaed19c4 (mu3), which FAILs the canonical main checker (tools/die_port_bind.py blob 92f649eb, = 58fc3dbc1) with 1,182 unread bits and 28 open output entries. Both checks below ran that main checker on the fleet (ot-epyc7, plan p4l_lkcol_mu_pf, table bind_table_p4l3_mu.json, land plan landing/p4l3).

| run | source | unread bits | open entries | pad bits | other counters | die.v sha256 |
|---|---|---|---|---|---|---|
| mu3 final (baseline) | ceaed19c4 | 1,182 | 28 | 210,677 | 0 | 61b683b6... |
| mu4a | d809b3a05 (frames _nx, MU lep without tf) | 1,182 | 20 | 210,677 | 0 | 6dfceca1... |
| mu4b | d4a7aeda9 (+ K-only HBM macro) | 1,182 | 10 | 210,628 | 0 | abf9424a... |
| **mu4c** | 5541f28af (+ 513-b band port B, fork claude/s81-bind-mu4-xr-1019) | **0** | **10** | 210,628 | 0 | ce6b7913... |

In mu4c the spare-out total falls 210,500 -> 202,226, because class D (C1 slice bo = 0) is now 14 x 513 bits.

Every removal is at the source. There are no ties, no new spare-out classes and no waivers. The spare-out rules are unchanged (210,500 bits).

- **Frame xo/xok, 64 chain-end frames.** frame_l4.py emits col_h9_l4_nx and col_h10_l4_nx. These drop xo/xok and the 4 relays that are their only drivers. The existing _l4 outputs stay byte-identical. dv_bind binds them through the `chain_end` rule: an instance with no xo plan link gets the _nx module. The die has 58 col_h9_l4_nx and 6 col_h10_l4_nx; the 26 forwarding col_h10_l4 and the 32 col_h9_MX_l4 frames are unchanged. Bench: frame_bench.sh L4=1 NX=1 PASS 12/12 for both masters, and the xlane mutant FAILs 12/12 (fb_*.log).
- **LEP tf/tfb on 4 MU masters.** The lane tile tf is `ot_s81ph_ckbuf` (assign y = a), a clock feedthrough. A census found no consumer on any die. New tile tops dsfd_coll_lane_w_ntf / _e_ntf keep the same core and parameters without the pin, and the MU wrappers have no tf/tfb. The lep MU die-master lint PASSes. The hardened lane view needs a re-kit; the only pin delta is tf.
- **HBM PHY, 10 open entries and 49 W pad bits.** The die now uses ot_hbm3e_phy_v41x_aw30_e8p5_k, which has no W port and no model-counter ports. Its abstract comes from tools/s81_dv/phy_k_variant.py: the LEF loses 2,331 pins with the same outline, K pins and PDN, and the libs, bb.v and json are derived the same way. The model is in tools/s81_dv/phy_k_model.py, with the K logic byte-identical. k_oor goes to the die status pin phy_hbm_k_oor. HBM gate with PHY_K=1 on Verilator 5.050: base PASS (0 bad, 0 timing violations) and MUT1 tRCD FAIL (32 violations). The die physical flow must load the _k LEF and libs.

## Remaining FAIL (mu4c)
- **unread 1,182 is CLOSED in mu4c.** The xr B port is 513 bits (bo = {pk[511:0], valid}), which carries the same entry q bits as before. A dir-B send of more than 2 pairs raises the sticky fault f_bw (mutant MUT_BWIDE has a committed witness), and the dv_layer_compile.send_cfg encoder refuses it. xr bench on Verilator 5.050: HB0 and HB1 PASS. Benches are in ../bind_mu4_xr/. There is no xr3/C3 kit to re-gate; the xr3 kit is still owed. The c3x/c1x lockstep benches were still building on the fleet at hand-off.
- **open 10: svc_rs (x14) and svc_rs_entry (x2) SM face w_v/w_a/w_m/w_d/w_st.** The SM share's write rows have no consumer, because the SM target storage (ot_s81_su_sm parent) is not on the die (table module null). This is an architecture item: the S81-SVC-TARGET-MODEL lane (bb3262ac4) is model-only, and the target storage RTL plus a plan block have to exist before these can be wired.
