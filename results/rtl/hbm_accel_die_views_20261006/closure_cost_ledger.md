# HBM DS die closure-cost ledger (coordinator; base = r16j wire-priced AR 537.376 us on the r13 wire record; CP inside the SU block ADOPTED 2026-10-07 00:15)

| item | cycles/token | AR % | cumulative AR % |
|---|---|---|---|
| r17 budget stage plan (wire stages 430->budget reach) | 1322 | 0.205 | 0.21 |
| stations meso crossings (+3, priced as us) | 3527 | 0.547 | 0.75 |
| stations gather a2 +1 | 343 | 0.053 | 0.81 |
| stations cdist b +2 | 686 | 0.106 | 0.91 |
| barrier view faces +4 | 1372 | 0.213 | 1.12 |
| collective SU faces +6 | 1590 | 0.247 | 1.37 |
| endpoint<->SerDes faces +4 | 1220 | 0.189 | 1.56 |
| VM faces +6 | 1746 | 0.271 | 1.83 |
| router faces W4/E3 +5 | 200 | 0.031 | 1.86 |
| cmdproc issue faces +2 | 686 | 0.106 | 1.97 |
| svc segments +15/expert fetch | 600 | 0.093 | 2.06 |
| index_q keys +10/scan | 80 | 0.012 | 2.07 |
| index_q rows +4/attn step | 160 | 0.025 | 2.10 |
| fwd chain index b5->VM (stages+meso) | 144 | 0.022 | 2.12 |
| fwd chain VM->router (stages+meso) | 680 | 0.105 | 2.23 |
| VM quadrant tiles (+2/x load, +2/barrier) | 1268 | 0.197 | 2.42 |
| cmdproc +3/command | 1029 | 0.160 | 2.58 |
| loader ck/2 (off token path) | 0 | 0 | 2.58 |
| r19b pin-abutting stations (attn roots into index bands, index-key ends; +1 hop each) | 41 | 0.006 | 2.59 |
| SM m2 structural redesign (SM stream: +7.988 us DS 1M AR = +1.816% of ITS 439.9 us base; NOT inside the r16j wire baseline) | 9586 | 1.486 | 4.08 |
| SM m3 over m2 (front strips + tileW macro registers: +0.062% of 439.9 us = 0.273 us) | 328 | 0.051 | 4.13 |
| r21 index b5 t_vm pin stations (+1 hop per index scan, 8 scans) | 8 | 0.001 | 4.13 |
| r22 relay stations abutting every hardened-block pin of a > 100 um die segment (500 relay ends, +1 hop each; OWNER 2026-10-07 rule 1) | 5522 | 0.857 | 4.98 |
| r22 credit handshakes (SM weight_req ready: SM REQ_CREDIT + svc credit FIFO sized to the round trip) | 0 | 0 | 4.98 |
| r23 2x hub area + attention tile 1778.5 x 1350 um + mcast_r6 a/b split + svc SE_s7/s8 split + VM early clock branch (die 30.59 mm wide; r23c GRT i5 wire record) | 8388 | 1.301 | 6.28 |

Cumulative +2.65% vs the r16j wire base (2026-10-07: +r19b pin stages, +SM m3; was +2.58%) [SUPERSEDED by the TOTAL line] (= +2.37% margin over the r17-staged wire base 538.478 us); MTP +1.15%. Pending: SU reducer SAFE ~+4/reduction, HA2 +1 edge, VM quadrant hops (measured), SM 3x3 grid lever (gives back up to the SM interim faces 0.46%). Source: recompose_r19_r13wire__cp_in_su.json

TOTAL HBM DS AR CLOSURE COST vs the pre-closure design (r16j wire-priced AR 537.376 us, before any margin / stage / split /
SM-structure cost): r22 +26.78 us = +4.98% (r21: +22.17 us = +4.13%) (die-level +13.91 us = +2.59%, SM element m2+m3 +8.26 us = +1.54%; CP inside the
SU block).  The SM m2 cost is NOT inside the r16j wire baseline: that baseline prices die wires on the pre-closure
element latencies; the SM stream's +1.816% is relative to its own 439.9 us base and is added here in us.

TOTAL at r23: +33.77 us = +6.28% vs pre-closure (die-level +25.50 us, SM +8.261 us); headline record headline_with_closure_r23.json (AR 1750.9 tok/s, MTP 3626.1 tok/s).

## 2026-10-07 ~07:50 additions
| item | cycles/token | AR % | cumulative AR % |
|---|---|---|---|
| attention tile r23 outline (attn agent: +1 root->quad broadcast, +2 quad->o result per tile on the critical path; +2 per tile chain hop i->o; 40 attention steps x (3 + 2 x 4 row hops)) | 440 | 0.068 | 6.35 |

Conditional (priced, NOT in the total until the variant is the one that closes):
- HA2 half-rate own-partial credit (a916e3f475e4d7ff2): +46 cycles per owner-reduction transaction (DS TP-96 NC8 PF384); x the exposed owner reductions per token (collective terms, 265) = 12,190 cyc = 10.16 us = +1.89 % AR if adopted.
- SU reducer half-rate RHALF (hbm-su): +146 cycles per reduction chain (perf64 301 -> 447) -- only if the SAFE reducer (+4 per reduction) misses.
- su_full DDIV 31: +10 cycles per divide op (DIVB / DIVIMM / SIGM / SILU / softplus / EGATE) -- only if hbm_su_full31 is the route that closes.
