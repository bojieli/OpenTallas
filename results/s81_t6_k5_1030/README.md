# Private T6 five-stage source preparation

Only s_0S_x07 / slice_station__t6__cl54a9ceeb normal FT0 and FT1 are proposed to grow from four to five stages. Both carry 1104 payload bits plus epoch. The two new stations add 2210 FFs and one cycle to each selected path. The other eleven chains, all landed chains, clock roles, reset roles, outline and ports remain unchanged in this preparation.

original_plan.json is the immutable 0428e13f7f3 plan. candidate_type.json changes only those two stations counts. candidate_bound.sv is a surgical private preparation from the actual historical native body, with no adoption claim. Current approved-main exporter integration and a new exact native mapped inventory are still required before any physical build. actual_old_ff_matrix.json records all eight existing 1105-FF banks and their real master/footprint; older final-stage sizing must not be assumed for the new native build.

proof.py extracts the two actual old and candidate RTL chains and uses the actual ot_dp_st definition. The candidate is compared to the old chain plus the declared extra reset-aware stage. Across 600 clocks, repeated cold/warm resets and random full-width data, 1186 output checks pass. The omitted-stage negative control differs in 593 cycles. This is the smallest exact changed vehicle, not a full block signoff.

TOK cb1962a28's copied token_price.json prices x_W2_out 59→60 with stations44→45 and fixed1 unchanged; x_W2_in24→25 with stations16→17 and fixed0 unchanged. Each exposed use adds833ps, a serial both-use adds1666ps. The current coarse token maximum is dominated by E3/out/p6 at152, so its scoped token term delta is0. No new throughput/signoff claim follows.

No P&R, route, clock qualification, adoption or owner-freeze change is authorized by this packet. The expected five-bank centre span is about1391um /4≈348um, but real per-bit rows/TAP/clock/reach remain to be generated and reviewed.
