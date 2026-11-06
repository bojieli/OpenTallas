# Native KS packet diagnostic

The retained V1c diagnostic forced `seqhost.u_u_seqhost.u.u_u.f_ks`, bypassing the real source mux and the native link. The opt-in `+NATIVE_KS_LINK` successor instead sends one type-2 HOST-plane frame through real peer `dsfd_coll_lane_e` endpoints and `ot_pdie_serdes_col` PMA models into the die's EN0/EN1 pads. Both halves use the same frame parity, as in `tb_s81sl_lep_host`.

The selected receive path is LEP `f_ks` -> 604-bit `unit_o0` -> the declared 88-cycle bound lane -> `unit_i1[603:551]` -> `dsdv_hostb_source` -> source landing -> sequencer mux. No KS force runs in the opt-in mode. The old diagnostic remains available without the new flag. Host programme words still use the existing V1c diagnostic stimulus; this is a KS-source diagnostic, not a complete external-host boot or token qualification.

`native_ks_link_tb.py INPUT OUTPUT` patches the exact retained V1c generated bench and refuses an unexpected layout. Add `native_ks_peer.sv` to its simulator input list. The patch also corrects the original `1ns/1ps` precision, which rounded 416.5-ps half-cycles to 417 ps. The successor uses `1ns/1fs` and checks/reports an actual root-clock period of 833000 fs.

`PROG KS` records the observed core receive/dispatch edge, not the peer queue edge. The compiled-calendar checker can therefore compare the subsequent commands against the real arrival. No design RTL, pins or cycles change.

The source cohort is the pinned 11-01 V1c vehicle. This is separate from current-main/G5 qualification. Native833 frontend, backend, corrected-main link and loader all PASS. Building only the top requires retaining `--main` when replacing `--binary`; this attempt initially omitted it, and the missing-main link failure is retained separately. A subsequent main-only relink used the unchanged generic simulation loop from the original build.

The bounded native diagnostic measured833000fs, then FAILed before KS could be queued: landed-parent slot0 epoch4 expected0 in s_7S_LP.u_u_lnl1.u_kn.u_r chunk68 at root92.047ns, cycle46 after release. Runtime110.34s. No KS received, no dispatch, no token/G5 pass. See result.json and run.log. The requested budget was11000cycles; the assertion stopped the actual run early. The original834ps successor remains build-only and was never run.

Read-only observation of the unchanged protected library identified writer/reader reset-origin skew of six edges. The exact chronology and a smallest scoped repair are recorded in ../ds_land_epoch_1106. The default-zero reader parameter is reviewable separately; no nonzero bound adoption, hierarchy cache mutation, or assertion waiver has occurred.
