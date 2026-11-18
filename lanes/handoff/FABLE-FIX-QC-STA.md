# FABLE-FIX-QC-STA handoff (QC st_a / st_b / tail closure; took the N4.1 kit from QC-N-OPUS 11-18 09:2x)

## 11-18 10:2x PST
- Work dir: intel2 (hub) /srv/opentallas-scratch2/claude/fable-fix-qc-sta (W). Run logs: intel2 /srv/opentallas-scratch3/claude/fable-fix-qc-sta-runlogs.
- Inputs copied there (read-only use): W/n41/tree + W/n41/bind/bind_n41d = QC-N-OPUS n41 tree and clean bind n41d (epyc2 fable-fix-qc-n/n41).
  The legacy absolute path is kept by ONE symlink: intel2 and intel1 /srv/opentallas-scratch3/claude/fable-fix-qc-n/n41 -> W/n41 (bind.f and the
  manifest name that path). Do not delete W/n41 through the symlink path; readlink first.
- W/n4view = published N4 plan 488b62fe + views_n4 (33 views), the 24 cland views CLOSED with landing_evidence/ (hard_landing.close_view on
  intel1, where the child build dirs die-qc-103/rk2/* exist). The live N4 tree views are NOT closed (0 landing_evidence dirs).
- Scripts in W: kit_sta.sh TYPE TAG (overlay + kit-rtl + topology), gen_route.sh TYPE TAG MEM CPUS [GOAL] (launch tree = rt/current tools +
  n41 tree data via tools/autopilot/rt_launch_tree.sh, gen, run_kit.sh route incl sign-off), census2.sh KIT OUT [ODB SDC [grt]] (end census by group).
- Kits: k3 sle_st_a_v1__cl67389ecd, k4 slw_st_a_v2__clf4365a62 (W/kit/<tag>/gen/<type>), ot-run --hosts localhost 64 GB / 16 thr.
- Why not epyc2 / intel1: epyc2 disks full (ot-run refuses); intel1 holds jobs on its measured-CPU thread gate (26 waiters).
- Recipe lessons: (1) plan_n41*.json carry an empty latency.note that the schema refuses (k2 stop) -> dropped in the overlay;
  (2) gen straight from rt/<sha>/tools reads tap sink bins inside rt and stops on "collector_tree differs from captured bound reset identity"
  -> gen must run from a launch tree; (3) cland views need landing_evidence or the child build dir on the gen host.
- Family facts (real reports): st_b has no design blocker on N3 (CTS TT +21.9 / +6.9 / -4.1 / -67.7; sle_st_b_v2__clfde1249e after GRT: setup +10.5,
  hold +5.05, vclk measured band PASS); its only fails were the old vclk file. st_a on N3: CTS TT -236 / -242 / -461.5, GRT -109 (stations missing).
