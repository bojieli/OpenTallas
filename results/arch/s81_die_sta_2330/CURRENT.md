S81 current diagnostic timing and closure priorities

Collected 2026-10-15T23:53:19.318792-07:00. Vehicle: inherited c19b, old narrow-column hub, 80,654 instances, 10.05 million net bits. Source is mixed and PORT_BIND failed; this result cannot qualify a die. GRT reports zero overflow but also missing global routes. SPEF was read by all three STA runs. Setup is judged at TT; hold at FF. SS is sensitivity only.

TT WNS -319.0 ps, TNS -229185.5 ps; FF WNS -417.9 ps, TNS -3511200 ps; SS setup WNS -525.2 ps. The endpoint reports each contain 8,903,954 checked endpoints. TT has 3,750 violations and FF has 64,845 (including 7,479 violations rounded to zero). Every violation involves at least one interim model. All 1,192,199 endpoints classified as fully closed-view relay pairs pass: minimum TT slack +51.7 ps and FF +131.4 ps. This does not prove the remaining model coverage.

| Priority | Cause and example | Evidence | Owner action |
| --- | --- | --- | --- |
| 1 | Missing current views / clock delivery on gather return interfaces | TT 3,002 gather capture failures; worst -291.5 ps | S-DIE bind actual current views and phi-R; network/gather owner fixes native parent as needed |
| 2 | Overlong return relay leg | rly63_EW interim -> rly63_WS closed; TT 734 failures, -311.4 ps, maximum pin-centre distance 735.9 um | S-DIE place another actual relay on native reach; preserve current closed leaves |
| 3 | Gather to PQ/capture parent phase and reach | FF worst -417.9 ps; gather launches 1,557 failing endpoints; PQ legs 652-795 um | S-DIE/PQ correct actual parents, pin registers and static cycles; no constraint relaxation |
| 4 | Interim HC ingress and return parents | FF y_d 8,192 endpoints, -224.5 ps; f_tr2 2,164/-119.3 ps; f_tr1 2,164/-115.3 ps | HC owner actual literal NT parent plus clock leaves; tower reservation fits pending full proof |
| 5 | Interim BF and node hold models | BF front c0/c1 -> col: 35,204 failures, worst -1.4 ps; node two main classes: 7,547 failures, worst -0.8 ps | Bind current exact native views first; no reroute of closed tiles based on these old models |
| 6 | Interim forwarded stations | TT 761 pair -319 ps (2 endpoints), 3056 pair -207.9 ps (10 endpoints) | Network owner bind standard native masters and review actual phases |

Current successor is vmc2 on p1973s89h: 89 stages, 356 rank dies, 408 total dies from the current knee study. Geometry and view coverage remain conditional. Complete incident audit found stale VM capture pins, crowded access corridors and an illegal raster join. Current corrections assign capture pins bit-for-bit from the real source, widen the VM access corridor to 259.2 um, and validate raster connectors. The actual VM internal screen still exceeds 0.60 locally and the S-VM owner is correcting it. Current full-chain source snapshot 891c35041 is being byte-verified before use. The preserved c21h GRT continues independently.

Machine class inputs are the inherited clock/model.json.gz instance and bus graph, kit/clock_delivery.json and grt_p/end_{tt,ff}.rpt. Driver mapping is by actual bus endpoints; lengths in these tables are geometric pin-centre distances, not extracted routed wirelengths. Raw source reports remain on EPYC4 at /srv/opentallas-scratch/claude/s81-die-iter/c19b/grt_p. No old source or route verdict was overwritten.
