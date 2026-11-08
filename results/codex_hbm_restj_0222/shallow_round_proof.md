# RESTJ same-cycle arithmetic and local-chain component proofs

A4 actual PLACE WNS -469.32ps;1281.70ps path from input-face VM drain_data[481] to lane0 write_q[69]. It passes through the two full32-bit additions x+32767+x[16], then VM write selection. Reset recovery remains positive33.59ps. Actual density image shows sparse9% fill, E edge63% clump and N edge68.8% strip, with reset relay7590sinks spread790.4um and M5 N/S pin windows.502. HOLD before CTS.

`shallow_round.py` changes exactly64 final assignments (16 drain slices x4 copies), retains all32 result bits, and adds no cycles. `round32_miter.sv` proves the full-width replacement against modulo32 x+32767+x[16] for allx. Native Yosys SAT PASS0.04s; omitting the ties carry is caught at x59ff8000. E4 own root has round32_clean.log and round32_mutant.log.

`clone_selectors.py --local-reset` expands selected source FFs sink-to-source: four drain selectors, io_r452, resetrelay, sync_q1, sync_q0. Keeps source FF wiring and all other original logic. Every new FF has the exact source cell/function/clock; D/R may use only inductively equal upstream copies. Same-cycle relation established by asyncreset and existing64-edge boot; no added stages. Asyncreset FF miter PASS; wrong-D mutant caught. External io_word and rst_n port obligations remain. Fanout<=8 alone does not prove physical locality.

Actual shallowB1 whole-graph certificate:69842 original cells,3361 copies,23533 original input rewires; wrong-D graph mutant caught. All selected source+copy Q loads measured<=8:4x499 selectors,249 io_r452,979 resetrelay,122 sync_q1,15 sync_q0. E4 shallowB1/clone_chain_certificate.json and replication_chain.json. Native B kit LEC must run fresh; A4 EQ is not inherited. CompactB actual physical view required before CTS.
