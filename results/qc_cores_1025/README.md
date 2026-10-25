QC core harvest 2026-10-25

harvest.json collects the existing signoff.py verdicts without altering failed records. Of 23 completed routes, the two su8 hold variants are SIGNED. The winning su8_b views and contract are in results/qc_cores_1024/qfd_dv_s5_su8_rst3.

The CRH warm candidate starts from the DRV-clean crh_bd route, whose remaining problems are FF hold -2.36 ps (7 endpoints) and the old fixed 250-ps insertion reference. It applies the coordinator's core-latency contract (METHODOLOGY.md 9.7), I_TT=290.93 ps and requested early tap=max(0,I-250)=40.93 ps, with FF hold repair margin5. Candidate SDC and lint context use the same I. It remains a candidate until signoff.py says SIGNED; no cycles, RTL, clock period or uncertainty changed.

crh_rp1 and vmr are blocked by related-pair skew between SRAM and register branches. More hold-buffer insertion cannot close that gate. Existing btab/prog variants remain live. Failed GRT runs show physical congestion and require a channel/placement fix, not another unchanged route.
