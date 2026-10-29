# QC takeover: landed failure diagnosis

The g24 landed TT setup value -806.86 ps is the synchronous single-cycle INFO column, not the count-aligned crossing gate. Its worst pair is sl_E2_st_a clk_t4 -> sl_E2_fw clk_t2; the routed clock damage is 1349.03 ps with 58.03 ps CPPR. g24 used ev_qc23pg (ad01d656b2b5), which still carried the obsolete st_a fault hop. DIE-QC24 removed that lane in ev_qc24; trial25 uses ev_qc25 (f72264b77b08) with the removal. The release RTL collects this fault locally through u_r0.fault -> u_ctl.stn_fault -> status, and fw has no such fault input.

The same g24 artifact has summary.landed.form=count_aligned and verdict PASS: 2537 crossings, TT lower margin105.6 / FF105.1ps, zero failing crossings. die_sta_related.py explicitly retains single-cycle slacks and half-period results as INFO while gating count-aligned crossings. No threshold or failed artifact was changed.

Source artifact: intel2:/srv/opentallas-scratch2/claude/die-qc24-1028/g24/sta_gate/die_sta_related.json. Extracted receipt g24_diagnosis.json retains its hash. collect_gate.py reads the actual summary so this distinction is preserved for trial25.

Actual remaining work: 780 early A0 taps have no real parent view; QC-A0-KITS owns child/parent closure. Real-view intra FF hold is -79.58ps (685 negative pairs); both-real FF is -3.91ps on two pairs. trial25 replaces the E crh lineage and replans with the fitted stage model; its gate is running, so no new numeric result is claimed. Full signal GRT with clock is still required. QC die owner owns these failures.

Baseline G0 has24 orphan infrastructure-pin findings because ev_qc25 carries stale landing composition. TOK-QC recomposition has already completed on ev_qc25 and owns the replacement contract; do not hand-prune its derived pins.
