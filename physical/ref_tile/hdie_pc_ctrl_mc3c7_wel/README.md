# hdie_pc_ctrl_mc3c7_wel -- MC3c timing fix (HBM-MC3D 10-20), parallel to the bound h9c fallback

Failure: route hdie_pc_ctrl_mc3c6_t242-mc3c6_t242-712f808fd NEEDS_RTL TT -160.9 ps (1041 D pins, TNS -27.2 ns) / FF hold -29.67 ps (29 pins).
Classification (route 6_finish.rpt + 4_1_cts/5_1_grt logs; ODB released):
- CLOCK SKEW (dominant): worst path launch clock 590 ps vs capture 404 ps (186 ps); report_clock_skew source 694 / target 402 ps.
  CTS log planned the pre-placed SPINE at 28.7 ps leaf spread; post-route it degrades (clock wire on M2-M5 vs the M6/M7 RC
  the spine is calibrated with). Same class as h9b -> h9c (closed with local TritonCTS).
- HIGH FANOUT / LONG WIRE (secondary): metadata_wp[0][0] -> j -> we -> 20 regional mf_valid D pins: 734 ps clk->D with only
  3 logic gates (164 ps INVx4 + 4 wire buffers = one we/wa net across 20 META_SELECT regions); +23 ps even at zero skew.
- MACRO INPUT: GRT worst was u_write_payload r_addr_in (-98 -> -46 after repair); clock-side (macro leaves on the spine).
- HOLD: 29 reg->reg pins -29.67 ps after route, same spine skew; input->reg hold +16 ps.
Fix:
- clock = cts (TritonCTS; leaf tile, no hard children, 241.92 x 272.16, ~9k sinks), spine dropped. Outline/macros/pins unchanged.
- RTL WE_LOCAL=1: 4 region groups x 4 banks own KEPT metadata_wp copies (same D, same reset) computing j/(j<length)/wa
  locally; each META_SELECT region captures accepted (acc_r) and (j<length) (jlt_q) in kept flops, mf_valid = acc_r & jlt_q.
  Same values on the same edges: NO added cycle, nothing to price. Ports unchanged.
Benches (Verilator 5.050, ot-epyc9, results/rtl/hbm_mc3d_1020/): positive face_txn PASS reqs=6000 beats=12944 wcols=759
edges_safe=100230 for WE_LOCAL=1 and WE_LOCAL=0 (identical to MC3c: bit- and cycle-exact). Mutants FAIL: ID_TAG errors=12944,
NO_ACT_HEAD errors=3, WE_NOACC (mf_valid without accepted) errors=400122.
Safe-design checklist: 1 pins PASS (RTL pin flops, 2-stage face reset landing, unchanged); 2 reach: gate placed-reach check;
3 fanout: kept copies, census in gate (max<=32 required); 4 depth: we cone now 1 compare per region group, accepted ends at flops;
5 storage PASS (23 SRAM macros unchanged); 6 floorplan = t242 (lattice WARN waived by LEAD rule-freeze 10-20);
7 clock: TritonCTS centre tree, spread <=80 TT/FF from gate, io_hold_margin 0.03; 8 schedule PASS: 0 added edges.

UPDATE (gate r1 19:35, PRE_GATE_NATIVE_CENSUS_REFUSED on BOTH kits, incl. the unchanged MC3c logic): accepted 34/52 loads
(22 K-region count_q next-count muxes + META copies), length[0] 35, AQ wr_ok_h 43 (head capture muxes). Fix (no added edge):
WE_LOCAL>=1 -> each K region count_q selects queue_count_acc/idle with its OWN pop_regions[r] (== accepted, asserted);
metadata_wp / unposted_aq take regional pops; AQ WROK_COPIES=2 adds a second wr_ok_h cone (head_bank_h2) for head regions 2,3.
WE_LOCAL=1 (mc3c7_wel) additionally: 4 per-bank kept wp copies -> jlt/wa from flops; per-region acc_r(pop) & jlt_q = mf_valid.
WE_LOCAL=2 (mc3c7_cts) keeps the original META forward path. Benches r2 (Verilator 5.050): WE_LOCAL=0/1/2 positives PASS
edges_safe=100230 (bit/cycle-exact vs MC3c), no copy-mismatch assertion; mutants idtag/noacthead (1,2) + noacc (1) FAIL.
