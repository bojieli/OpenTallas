# KV-OWN-HG-R3 (Sonnet 5.5) 2026-11-25. Owns KV hg/hgi types except the 2 hgi route pilots (KV-ALLFIX keeps) + KV-RSTREACH rows. Coordinate KV-HGI-WGATE, KV-SINKBINS, KV-PC-BANK (pc rows are theirs).
## Row actions (OWNERS-SWEEP 08:48 + ALLFIX-KV; state names as listed there)
- kv3_hg_v1__r889141819, __r88f4bfb40, __r8dffc461a, kv3_hg_v1p2, kv3_hg_v1p3__r81da466fe/__r838481cd7/__r8c662a835, kv3_hg_v1p4: cancelled-superseded -> CLOSE as duplicates of the family types; relaunch only via A5t9 row below.
- kv3_hg, kv3_hg_v3, kv3_hg_v1p5, kv3_hg_v1p6, kv3_hgi, kv3_hgi_v2__cl2862d491, kv3_hgi_v5, kv3_hgi_v7: held by plan event -> A5t9 row (SITE-OFF-OUTLINE pull, HEAD-WLAND-SPLIT, HG-V1P5-CTS-REGRESS); no probe before the row.
- kv3_hgi_v6, kv3_hgi_v8: cancelled-superseded -> A5t9 row (hgi_v6 SINKBIN re-seat 74d75df65ff1 with KV-SINKBINS; v8 HGI8W 84834100f853).
- kv3_hgi_v2__cle0015330: FAILED flow error -> read fail, A5t8 place probe after publish.
- kv3_hgi_v1 x2, v3, v4: running; leave. 2 hgi route pilots stay with KV-ALLFIX.
- RSTREACH leftovers: hgi bin re-seat + WESTLAND5 hgi_v5/v7/v8 taps 1ccdc44bf52f -> A5t9 (mine); hub_Wi/io_cor_v1/pv_v1n -> KV-PV-ESTRIP; PC-SPINE -> KV-PC-BANK.
## Draft: SITE-OFF-OUTLINE hg pull (A5t9), from epyc12 kv-allfix/a5t8/offoutline_k10/fail_list.txt
10 types kv3_hg_v1__r889141819, __r88f4bfb40, __r8dffc461a, kv3_hg_v1p2, kv3_hg_v1p3__r81da466fe, __r838481cd7, __r8c662a835, kv3_hg_v1p4, kv3_hg_v1p5, kv3_hg_v1p6 (outline 1278.72x1520.64): set internal_stations[conn=bus:o_ectl_Q_N_eN].regs_um[8] from (1279.0, 273.9) to (1278.42, 273.9) (0.3 um pull in). Check hops to neighbours <=405 and PRE ADV-SITE-OFF-OUTLINE clean + strict bind. Not yet written as ops JSON/probed. pv_v1e is KV-OWN-PV-R2's.
