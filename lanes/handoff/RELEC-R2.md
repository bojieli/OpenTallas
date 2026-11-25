# RELEC-R2 handoff (11-25)
Done: fixed-lec (3b9462e9eba, PYTHONHASHSEED=0) reruns of RECHECK rows + uncounted-15. Evidence: epyc10/epyc8 /srv/opentallas-scratch2/claude/RELEC-R2/r/<tag>/lec/lec.json, epyc2 RELEC-R2b; lanes/handoff/RELEC-R2-FAILSETS.md.
EQUIVALENT: slw_fe_v1 cldb4efe33 newer view (3ca367c1), sle_hc1 pv97423966.
Stable non-EQ, owners to find the cone:
- coll_s (7 runs, 20 differs+1 undecided): cone u_dut.u_bound.u_g_face_4_u_face.g_codec.u_codec.u_ctl (epoch_abort, fault_cause[1], rx_v; undecided fault_cause[0], p_tx_flit[556..579]; re[0] removed by synthesis though not constant). Mapped netlist (1_2_yosys.v) shows the same cone as 3 undecided in face_3 (UNPROVEN), so the cause is already in synthesis, not routing. Relay hints (guard on re[0], e3 eq) did not change the set. Owner: QC-ALLFIX (RTL/synth root cause on u_ctl re/ev/epoch capture).
- hc3 (pvcca, pv6c2c33ed, pv39aac7a1; 51 differs each): cone u_dut.u_bound.u_u_xl3_{2,5,7}.u_leaf q[48..63]+q_bad, the 3 of 8 identical leaves; select-replica / mux_rep16 last level. Owner: QC-ALLFIX + FAM-QC-HCST-R3.
- t40: 4943 differs on po:ft0_o pins. hd_mesh: 8957+2023 in FIFO SRAM black boxes (HEAD-R18).
Blocked: 7 R4A4 types UNRECOVERABLE-REF (plan zz_s29_qc103_s4q9n46r4_final_preview.json survives on epyc2/epyc8 but the generated RTL/sidecar and kit_rtl_paths of the counted kit exist only in AGIdock; bind dir has bind_report.json only; eb1e73448b git has no plan). cl08d14f0d: ODB bbef4a64 on no host store; only AGIdock.
