# HBM generic die (R25GQ) die-level iteration

Lead: hbm-die-iter (log /home/ubuntu/claude-takeover-20261007/el1011-hbmdie.log, prefix [hbm-die-iter]).
Contract: results/arch/hier_contract_1011/r25gq.json. Floorplan generator: tools/hbm_accel_die_fp.py (variant r25gqn_pr).
Die checklist (academic validation): legal floorplan from real abstracts, full-die GRT 0 overflow, die TT setup / FF hold
STA on GRT parasitics over register-bounded relay links, CTS skew plan, IR, representative-region DRT only (no flat DRT).

## Real-view share (contract v6, 2026-10-12 00:40 PT)

| class | slots | area mm2 | share |
|---|---|---|---|
| real closed view (svc x34, hgi_mtp, loader, quant, idx hslice x128, su12_sfu x64) | 229 | 23.8 | 6.0 % |
| real closed tiles counted by area (hfd_hc_tile_xl x352, cons B CLOSED TT +35.41 / FF +13.39, child_lint PASS) | 352 | 7.5 | 1.9 % |
| hard IP / reservation (HBM PHY x4, SerDes x9, host PHY, slabs) | 17 | 73.5 | 18.6 % |
| budget placeholder (SM 116.4, attn halves 111.1, SU 22.7, lk_ep 19.4, hc_eng 6.9, hgi_vm 4.3, ...) | 152 | 290.4 | 73.5 % |

Real views: 581 of 750 slots (77 %) but 7.9 % of placed area; SM and attention halves (57 % of area) have no closed view.
In the generator's die model (tools/hbm_die_views.py index, r25gqn_pr) only 6 station masters are installed closed, and
26 are interim/MISMATCH. The die GRT therefore still runs on generated pins at element level (tile views are not yet
bound to element masters).

## Iterations

| iter | date | contract / variant | case | host / dir | result | classification / action |
|---|---|---|---|---|---|---|
| 0 | 10-11 | v3-era, r25gqn (pre-physical-relay), c07156bbc | full-die GRT, k=16 bundled, 50 iters, generator masters | epyc2 hbmdie-1011/grt/grt_r25gqn_v10 (~14 h) | total overflow 1,374,522 (usage 11.29 %): M4 32k, M5 357k, M6 453k, M7 285k, M8 121k, M9 125k. 77 % of overflow in x 12-18 mm / y 10-16 mm (hub spine + hc_eng) | floorplan class: lane-group chains (lgE/lgW ~17.8 kb) + spine faces; M5 overflow = pin access on M4/M5 pins with die M2-M5 adjustment 1.0 (channels unusable on M4/M5). Fed to rf2 -> r25gqn_pr |
| 1 | 10-12 00:02 | v5, r25gqn_pr (physical relays, data segments > 504 um = 0), main d07883c70 | full-die GRT of record, k=16, generator masters, 33,036 instances, 365,260 bundle nets | epyc1tb hbmdie-1011/grt/grt_r25gqn_pr (ETA ~14:00 PT) | RUNNING | compare with iter 0 by layer and 2 mm bin when it ends |
| - | 10-12 01:20 | v7 | contract only | - | D19 SM.MATVEC x load = lgE slot 0 (cmdproc f_lgEcp_rdn / t_lgEcp_rup), no new die pins | element (smmv) implements |
