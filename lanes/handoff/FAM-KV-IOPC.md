# FAM-KV-IOPC handoff (11-20 23:5x PST)
Work dir epyc8 /srv/opentallas-scratch2/claude/fam-kv-iopc (br1 = bank_reset_delta io_cor_v1 on D27c plan 19af3841ef74; bd.sh/pk.sh scripts; tree_a1 = linked private tree).
Rep: kv3_io_cor_v1. Fix = plan reset.bank_taps 41 rows (br1/plan_out.json, report.json), hop max 165.7 um.
Pipeline: bd.sh a1 (private bind) -> pk.sh a1 kv3_io_cor_v1 <plan> cts (kit-rtl needs green global bind) -> read post-hook CTS.
Then rows to KV-PLAN-R3 (D27/D28), siblings: kv3_io_cor (cancelled), pc rows are KV-PLAN-R3-owned (held until D27 apply).

## CODEX notes 11-21 02:40 PST

- io_cor_v1 has two old independent causes. DRT-0255 pocket at ft11 bank3, then pre-CTS physical reset reach (u_rrl_67 to ft16 output, 2001 μm), not OOM. The 41 reset bank taps are in D27c. Variant B rescopes ft11 bank3 2->12 columns plus ft13 input band [790,17.28,1000,103.68]. epyc7 fam-kv-iopc/gate_d26b failed provenance_bind.json permission despite zero semantic bind errors and RC_LATCHECK 0. File owner write was restored in the private pack, and inherited b2 bind re-run oth-ubuntu-292581-1795254553 is active. Keep variant B independent until representative kit shows the pocket clear.
- pc_v3 and two pc variants: PG VSS on M5 obstructed by M6/M7 at u_bound.u_kvpc0. Proof on fresh D27c merged-obstruction views after r4d bind. pc_v3 67,193 sinks versus 39×1200 sites requires at least 56 sites; cascade alone cannot fit. Current clock-tap density work stays tied to the new place proof.
