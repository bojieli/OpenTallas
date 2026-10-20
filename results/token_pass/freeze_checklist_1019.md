# TOK.FREEZE checklist: token pass of record (TOKEN-REC, 2026-10-19)

The token pass of record runs ONCE per design, after that design's release die passes its die gates (strict bind,
die GRT overflow 0, real-view die STA TT setup / FF hold >= 0, die clock check). Until then every run is a regression
pilot. Tracker: results/token_pass/status_1019.md (tools/token_pass_status.py).

## 1. Freeze preconditions (all designs)
- [ ] One pinned main commit for all four designs. Runs happen in a source-bound worktree (no dirty tree) and every
      record names the commit and the die netlist SHA it simulated.
- [ ] Verilator 5.050 (the closure daemon's version). Each bench spec lists every file it reads. Real memory is declared.
- [ ] The compiler/static schedule of record is regenerated on the frozen die. It absorbs every priced die edge
      (landings, relays, ctlm, CALR). A collision, overflow or underflow is a FAIL. No credits or backpressure.
- [ ] Each layer bench: bit-exact vs golden, static-schedule assertions clean, exact commit cycles, and mutants that
      FAIL with committed fail witnesses.
- [ ] Every record carries a `token_compose` block. `python3 tools/token_compose_xdie.py --page-data
      tools/fleet_viz/explorer/token/data` is run, then `--check` PASSes (it also checks that the page is not stale).
- [ ] Release grade: >= 90% of token cycles measured on the release die. The rest may only be PHY/off-chip vendor
      legs (modelled-PHY) or priced link legs that have a stage bench. The layer loss vs price goes in the accepted-cost
      ledger (<= 5% per unit, <= 15% per design).

## 2. Die builds of record (fill in the SHA at freeze)
| design | die build(s) | status 10-19 | freeze trigger |
|---|---|---|---|
| DS ROM S81 | S81 p4l-MU, 520 dies (GEN of record + die.v SHA) | die gates est. 10-22..24 | S81.STA PASS |
| Qwen ROM | compute dv2f19g3 (GEN3) + KV/system kvs14 GEN9 | est. 10-23..25 / 10-21..23 | Q.STA + K.STA PASS |
| HBM-DS | d4g GEN2e4 (GEN2 / GEN2d are diagnostic only) | est. 10-23..25 | H.STA PASS |
| HBM-Qwen | d4g GEN2e4 (same die as HBM-DS) | est. 10-23..25 | H.STA PASS |

Old single-user dies (S81 p4l-SU, dv2f14*, kvs14c, GEN2) are diagnostic only. Runs on them never count as records.

## 3. Goldens of record (pin a hash for each)
- [ ] DS ROM: per-layer DV fixtures and goldens for L0 / L2 / L14 / L20 / head / MTP draft, from the LEAD2-S81/TOK2
      DV layer-programme compiler. Plus the TP4 calendar golden beats (xdie_s81). Plus the 46-user AR / 10-user MTP
      calendars (results/arch/mu_s81_1018/calendar_{ar,mtp}*.json, brute-force lemma PASS).
- [ ] Qwen ROM: the canonical TP4 36-layer + head golden (QW-TOK3 canonical gold run, 148 ROM stage images
      SHA-matched). Plus gold4 (3 independent contexts + the latency user) for the 4-user pass.
- [ ] HBM-DS: HGI-1 sim exact goldens on the d4g price5 programme (hgi_sim d4g_price5_1018 e680e506; priced_layers.json
      = assertion targets).
- [ ] HBM-Qwen: HGI-1 TP8 exact goldens (8 dies at P8191: L0 160/160, L0->L1 320/320, head 9/9). The naive TP8
      down_proj split is forbidden.

## 4. Runs of record (one record.json each, under results/rtl/<design>_tokpass_<date>/)
| design | 1-user runs | multi-user runs |
|---|---|---|
| DS ROM S81 | layer benches L0, L2, L14, L20 (k=6 split), head, MTP draft, cut from the p4l-MU GEN netlist; TP4 collectives + hops (xdie_s81) on the same die RTL | 46-user AR + 10-user MTP calendar on the die: per-user layer benches + xdie-s81-mu (all users tagged) + host plane SEQHOST_MU N outstanding |
| Qwen ROM | compute die L0 + Lc + head layer bench (GEN3 netlist slices); KV die attention u1; compute<->KV D2D pair on GEN3 + GEN9; TP8 all-reduce windows | 4-user: KV attention u4, compute<->KV pair 4u, NU4 sequencer full token vs gold4 |
| HBM-DS | quadrant (SW) bench on GEN2e4: L0, L1, L2, L3 MoE, L14, L20-class, head; cross-die COLL (AG / RS144 / AR) on GEN2e4 COLL ROWS256 / AR_ITER | not in this release (owner 10-18) |
| HBM-Qwen | quadrant bench on GEN2e4: L0, Lk, head; TP8 all-reduce on GEN2e4 | not in this release |

## 5. After the runs
- [ ] Re-export the token page (compose + tools/token_pass_status.py --page-data). Remove the PRICED label from MU.CURVE
      points that are now measured.
- [ ] Update the HANDOFF, then tick TOK.REC / TOK.FREEZE / MU.CURVE in RELEASE_TREE_DONE.md.
