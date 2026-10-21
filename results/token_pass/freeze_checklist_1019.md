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

## 2. Die builds of record (fill in the SHA at freeze; selected release updated 10-21)
| design | die build(s) | current status | freeze trigger |
|---|---|---|---|
| DS ROM S81 | 72-frame release die; 241-stage map 483869b91 and G4 calendar 6f8bbf5c4 (GEN and die.v SHA to pin) | RTL-functional source assembly in progress; no full-token verdict | S81.STA PASS |
| Qwen ROM | selected compute and KV/system release successors (GEN and die.v SHAs to pin) | RTL-functional assembly 02e04473c; component results pending | Q.STA + K.STA PASS |
| HBM-DS | selected d4g release successor (r14 source component pilot retained) | SW slice and unit programmes; full layer coverage incomplete | H.STA PASS |
| HBM-Qwen | same selected d4g release die as HBM-DS | SW slice and unit programmes; full layer coverage incomplete | H.STA PASS |

Old single-user dies (S81 p4l-SU, dv2f14*, kvs14c, GEN2) are diagnostic only. Runs on them never count as records.

## 3. Goldens of record (pin a hash for each)
- [ ] DS ROM: per-layer DV fixtures and goldens for L0 / L2 / L14 / L20 / head / MTP draft, from the LEAD2-S81/TOK2
      DV layer-programme compiler. Plus the TP4 calendar golden beats (xdie_s81). Plus the selected 50-user AR / 10-user MTP
      241-stage G4 calendar 6f8bbf5c4. Earlier 81-stage and 46-user calendars are historical.
      The compiled aggregate model figures are AR 47,642 (50 users, rounded per-user 952.8) and
      MTP 29,634 (10 users, per-user 2,963.4); these are not measured token rates. Retain exact
      unrounded compiler values in the final record.
- [ ] Qwen ROM: the canonical TP4 36-layer + head golden (QW-TOK3 canonical gold run, 148 ROM stage images
      SHA-matched). Plus gold4 (3 independent contexts + the latency user) for the 4-user pass.
- [ ] HBM-DS: HGI-1 sim exact goldens on the d4g price5 programme (hgi_sim d4g_price5_1018 e680e506; priced_layers.json
      = assertion targets).
- [ ] HBM-Qwen: HGI-1 TP8 exact goldens (8 dies at P8191: L0 160/160, L0->L1 320/320, head 9/9). The naive TP8
      down_proj split is forbidden.

## 4. Runs of record (one record.json each, under results/rtl/<design>_tokpass_<date>/)
| design | 1-user runs | multi-user runs |
|---|---|---|
| DS ROM S81 | layer benches L0, L2, L14, L20 (k=6 split), head, MTP draft, cut from the selected 72-frame GEN netlist; TP4 collectives + hops (xdie_s81) on the same die RTL | 50-user AR + 10-user MTP selected 241-stage calendar on the die: per-user layer benches + xdie-s81-mu (all users tagged) + host plane SEQHOST_MU N outstanding |
| Qwen ROM | compute die L0 + Lc + head layer bench (GEN3 netlist slices); KV die attention u1; compute<->KV D2D pair on GEN3 + GEN9; TP8 all-reduce windows | 4-user: KV attention u4, compute<->KV pair 4u, NU4 sequencer full token vs gold4 |
| HBM-DS | quadrant (SW) bench on the selected release GEN: L0, L1, L2, L3 MoE, L14, L20-class, head; cross-die COLL (AG / RS144 / AR) on the actual selected COLL source and programme capacity | not in this release (owner 10-18) |
| HBM-Qwen | quadrant bench on the selected release GEN: L0, Lk, head; TP8 all-reduce on the selected release GEN | not in this release |

## 5. After the runs
- [ ] Re-export the token page (compose + tools/token_pass_status.py --page-data). Remove the PRICED label from MU.CURVE
      points that are now measured.
- [ ] Update the HANDOFF, then tick TOK.REC / TOK.FREEZE / MU.CURVE in RELEASE_TREE_DONE.md.


## 6. Rerun the current RTL-functional scripts at closure (owner 10-21)

Current source runs are graded "RTL-functional (source assembly)" and report incomplete coverage
or failing mechanisms explicitly. Component cycles compose a model; they do not establish a full-token
bit-exact pass. Keep the source run receipts and failure logs when rerunning the same scripts at closure.
A GEN wrapper simulated with source children is "RTL-functional (GEN composition; source children)";
it is not mapped die-netlist evidence. Only actual simulated netlist coverage earns that grade.

- [ ] Qwen ROM: `tools/qwen_tokfunc/run_tok_func_qw.sh --asm <frozen-commit>`;
      current source recipe is `tools/qwen_tokfunc/asm_recipe.json` (02e04473c).
      Closure invocation adds `--die-netlist <compute-GEN-out/case>:<KV-GEN-out/case>`.
      This hook remains unproven: source-only STG/XDIE must not be relabelled, the KV attention carve
      needs its actual `sources.txt`, and source stand-ins such as OVL4u remain diagnostic.
      Check stage-specific coverage in `tools/qwen_tokfunc/README.md` and keep incomplete grades
      until those stages actually execute against the frozen hierarchy. The inherited composition
      base is 272,641 cycles; the interim head-adjusted source composition is 272,675 cycles,
      pending STG/XT1/TP8/KV results. Neither is a final token verdict.
- [ ] S81 ROM: `tools/s81_dv/tokfunc/run_tokfunc_s81.sh --ref <frozen-commit>
      --work <fleet-dir> --fixtures <fixture-dir>`; closure adds `--die-v <die.v>
      --port-bind <port_bind.json> --plan <plan.json> --land <land.json>`.
      Run the selected 72-frame, 241-stage G4 assembly and its 50-user AR / 10-user MTP calendar.
      The closure hook remains pending actual replay/head coverage; a source PASS cannot be relabelled.
- [ ] HBM (both models): `tools/hbm_layer_vehicle/tok_func_hbm.sh` with `MODE=source`,
      pinned `SRC_REV` and the current contract; existing source pilot uses the r14 SW slice.
      At GEN use the SAME script with `MODE=gen_rtl`, `DIE_V=<GEN-die.v>`,
      `CONTRACT=<post-relay-contract>` and `SRC_REV=<exact-commit>`.
      That mode rebuilds source children and retains the GEN-composition grade. `MODE=netlist`
      must fail closed until the frozen mapped hierarchy and libraries can actually be simulated.
      SU-only programmes and format-open/unsupported operations leave layer/token coverage incomplete.
