# TOK-14 (2026-10-30 18:5x PDT): plan-of-record re-pricing (INFO only, OWNER 12.21)

HBM plan of record d41v (die_plan 3bccac4b3860, DIE-HBM-43 READY 18:27): price_tok14.py / price.log / tok14_price.json.
Same DS S2 model + traps as TOK-13 (base 576702.4178, record 1799.79 asserted; TOK-13 POR row reproduced 1671.81).
d41v built lanes (va_build_d41v.log): L730 b113->b112 42 (V-A est 46), L731 b113->su20 17, L732..L736 12/10/20/35/20.
SFU per SU.sfu record = tap read 42 + tap write 42 (b113<->su11, unbuilt V-A est) + broadcast max 44 (b113->b110 est)
+ gather max 46 (b112->b113 est), each -2 = 166 (TOK-13: 168). IDX 80 unchanged (b100->b102 / b103->b101 unbuilt).
- d41v POR: 1672.85 tok/s (+1.0 vs TOK-13 1671.81). Sensitivity broadcast max 42: 1673.90.
The unbuilt SFU tap/gather pairs stay at V-A estimates (UNCHECKED; d41v found no station chain for them).

S81 station-form v2 (claude/die-s81-36-stform2-1030@36c4765544b, plan 0c11b13a4387, base b6c0953effd plan a2c105604e3c):
s81_stform2_terms.py (TOK-13 method unchanged) -> composer terms identical to TOK-13 v1 pricing: field_round 152->153,
svc_to_hub 30->31, link_end 70->73, ring_link/leaf_hub_rt unchanged; 106 lanes changed. Price = TOK-13: 3653.8 MTP /
1258.9 AR tok/s (-0.04 / -0.06 %). Current main plan 2c0c7ab1028c: same terms as base (no change).
