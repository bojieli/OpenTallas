# TYPE-HDEPC handoff (2026-11-14 22:3x PST)
- Premise of FABLE-HARD-QCHEAD (u_epc inputs clocked early inside the core) is false for the signed core: input flops 422-488 ps, output flops 400-422 ps after the core pin (epyc2 type-hdepc/diag/ffclk.tsv).
- Root cause of -395: hd_host_e kits bundle stale u_epc lib 8aad8716ff84; signed lib is f663e343abd8 (hepc_south eco99_south_g2/i1/views). Re-time with the signed libs: TT -173.45 (221 viol), FF hold -10.24 unchanged.
- Bounds (TT): in setup -173.4, in hold +113.7, out setup -85.0, out hold +93.4. No tap value fits; see RESULT 22:3x in COORD-REVIEW-QUEUE.md. Fix = parent routing of SRAM->u_epc data path (about 130 ps) and pricing outputs with the signed lib.
- FF hold -10.24 class: 27 core reg2reg (u_ski.d_q -> u_head.mwd) + 152 from output ports coll_o1/l1_rx_o.
- Artifacts: epyc2 /srv/opentallas-scratch2/claude/type-hdepc/{diag,retime}; epyc7 copy of diag; kit copy epyc2 head-97/hepc_south/eco99_south_g2/i1 (rsync of signed kit, safe to delete). Scripts: retime.sh, exp.sh, mkexp.py, clkdiag.tcl.
- No u_epc rebuild, no archive (already indexed). Open: HEAD-REMAP-1 to decide rp21z20 treatment; KIT-OPS-6 stale-lib audit.
