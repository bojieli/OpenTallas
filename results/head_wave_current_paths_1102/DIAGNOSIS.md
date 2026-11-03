# Exact current failed postCTS paths: source context joined

This is the bounded read-only failure diagnosis, with exact saved5_1_grt inputs, actual native library/config digest checks, original SDC/RC/clock/band helper and fresh global-route RC estimation. The actual5GRT images were rendered and personally VIEWED before timing; the previous4CTS images did not substitute. Existing geometry scope remains PASS-COND, no new data/clock geometry failure, no new route/repair/adoption or gate-authority decision.

Native unit1428080-1793626422 completed EshimTTMAX/MIN and exactly reproduced the failed source readout, then exited1 on an unsupported optional report_clocks command. That diagnostic API error is retained in the raw log; it is not a DUT failure. The correction uses the already supported all_clocks/get_property API. Unit1562608-1793626907 then collected only the missing EshimFF/TurnTT/TurnFF reports, exit0, same8GB2T normal admission. No completed TT query was repeated. Native5GRT inputs were mounted read-only throughout; each source readset/hash and native library digest matched before timing.

| Exact original profile | Setup estimate | Hold estimate | Pin-register clock mean |
|---|---:|---:|---:|
| EshimTT | −46.51 | −80.73 (information) | 401.85 |
| EshimFF | +9.05 (information) | −89.35 | 309.17 |
| TurnTT | −340.16 (context defect below) | +12.59 (information) | 421.97 |
| TurnFF | −117.99 (information/context) | +10.01 | 327.65 |

The raw tolerance remains20 and old band policy remains untouched. Declared binding40 versus default20 is a separate source-plumbing proposal, not automatically applied here.

## Turn: concrete missing real-clock propagation

Exact worst TT path is **cland_fstart_in_u1_i → u_cland_u1_i/u_ring.s_d[1][10]**, captured on rising fclk_in_u1_i. The report explicitly has **ideal0ps capture network**, required833−setup7.51=825.49. Data arrival1165.65 is virtual450 +external126.6 +589.05ps post-input delay. This proves that the observed−340.16 uses an incomplete physical clock context; it does not establish a physical DUT timing failure of that magnitude.

The original consumer recognizes real forwarded roots when selecting the virtual IO reference, but propagates only `[get_clocks clk]`. The actual saved native tree has853clock cells, rooted forwarded trees and own-leaf137.86/tree-leg167.43µm. Clock source inventory is5real roots/aliases (clk, fclk_in_d1_i/u1_i, generated fclk_out_d1_o/u1_o) plus one source-less virtual. A separate reviewed **default-OFF** source profile enumerates all source-bearing clocks, excludes the sole virtual and preserves numeric SDC/Lib/RC/band/clk-family insertion census. It is not applied to these A receipts. A separately scoped paired B must retain both signed setup and hold; no predicted PASS, arbitrary450ps capture latency or IO relaxation follows.

The former699.72/416.5 cross-domain hypothesis does **not** govern this exact worst path: it is a full833 capture with external126.6. Those other constraints remain in the SDC and may matter for later paths; they are not removed or waived. The earlier BC/prebalance falling-origin report also does not identify this current path.

There is nevertheless a real589.05ps control tree to assess under a qualified profile: input17 BUFx8 fanout70; load_slew5641 BUFx24 fanout67; INVx2; OR3x4 fanout49; several BUFx24 branches with fanout45/48/52/52; AO21x1 into the ring data mux. It is not a collapsed fanout1 chain. A DATA cloning/rebalance/placement vehicle should only be priced after the actual forwarded capture phase/RC is measured, with graph/register ABI preserved and fresh geometry LOOK before any physical action.

## Eshim: actual two-corner DATA padding tradeoff

Current TT worst is **link_i[560] → u_ft_link_s0/q[560]**, not the stale BC eq565 path. It passes hold1162/HB4xp67 and u_ft_link_s0/hold1163/HB4xp67 plus input517/BUFx2. The two HB4 output sections contribute128.12ps of153.38ps post-input delay. Arrival1273.10 versus required1226.59 gives−46.51. The FF setup on the same bit is only+9.05. A wire-only pose edit is not the primary explanation, and deleting one pad cannot be credited without the corresponding FF minimum.

Actual FF worst **link_i[542] → q[542]** has only input497/BUFx2: vclk342 +input−90 +14.20ps gives266.20arrival, versus331.91capture +12.50inter-clock uncertainty +11.13hold=355.55required, hence−89.35. Many neighboring bits have the same hold class. The original BC GRT repair log already found573hold endpoints, inserted15HB4 cells, plateaued at−89.348 through1700iterations, and issued RSZ-0064 unable-to-repair. An identical generic repair replay is not a useful successor.

The finite smallest DATA vehicle is a paired per-bit delay-window diagnosis for representative bit560 (setup-limited/padded) and542 (hold-limited/unpadded), under the exact qualified clock/frame. Establish TT maximum and FF minimum for each same bit before selecting a mixed hold-cell chain or declaring a window infeasible. Any later physical candidate must preserve clock roots/phases/edges, registered ABI, ports, FF poses/status/DNT, source constraints and cycle count, with real parent contract evidence rather than an assumed sender-min substitute. This packet does not claim the feasibility or acceptance of such a candidate and launches no repair. Eshim's current clock mean TT deviation48.15 also remains outside its declared40; correcting tolerance plumbing alone does not close it.

All native raw reports, signed negative outcomes, source hashes, LOOK release and the reporting-command failure are preserved. GRT data/clock occupancy, PG contact, full routed timing, LEC, real parent and SIGNED status are not established by this read-only source-profile diagnosis.
