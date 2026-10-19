# XDIE-S81-2: S81 cross-die co-sim on the current die RTL + multi-user (10-19)

Bench `rtl/test/xdie_s81_2/tb_xdie_s81_2.sv`. It simulates a 4-die TP4 group: 16 end-slice endpoints, each with an rstop, a lep, 4 lane tiles, lane legs and the PHY digital. Sources are pinned by commit in `SOURCES.txt`: G8R2 0e6b9b710 die RTL, HF-3 lane ed9d570ad, and the MU lep from origin/main. Every lk lane goes through the die's lane leg, which is 3 `dsfd_dvrlyh` half-cycle relays plus a `dsfd_dvland` landing with k = 3. The only modelled part is the fabric: a static-circuit switch, 453 cycles per crossing. Simulator: Verilator 5.050, the closure daemon's version. The fleet jobs c/a/m/w ran on ot-epyc5 (gate script `tools/xdie_s81_2/gate.sh`, collector `tools/xdie_s81_2/collect.sh`).

## Verdicts vs expected (`gate/*.txt`, fixed-latency check `gate/lfix.txt`)
| run | build / golden | expected | got | note |
|---|---|---|---|---|
| min | cur / g564 | PASS | PASS | 12096 beats bit-exact, maxlate 0, L_first 563 |
| min_err | cur / g564 +ERRP=7 | PASS | PASS | FEC corrects the pad errors |
| chb0 | cur / g564 +CHB=0 | FAIL | FAIL | late 7452 (ch_b strap 0 -> 400 board budget) |
| late | cur / gm564 +LATE=40 | FAIL | FAIL | late 68 |
| asbound | asb (G8R2 lane file as bound) / g564 | FAIL | FAIL | FINDING confirmed: late 1212; the die must take the HF-3 lane file (CH_BOARD 700) |
| noleg | cur LEG=0 / g556 | PASS | PASS | the gate_g5 form; first-beat latency 553 (lane legs add +10 cycles a crossing, not +8; still within the 564 deadlines) |
| landsel | cur +OT_S81_LAND_MUT_SEL / gm564 | FAIL | PASS on bench, FAIL on lfix | see finding 2 |
| mu_real / mu_dense / mu_dense_err | mu / mr, md | PASS | first run (fmt0) FAIL, 14184 mismatches; re-run m2 pending | see finding 1 |
| wrongcopy | mu +WRONGCOPY / mm | FAIL | FAIL | extra 1280 (pair-B beats on pair A) |
| tagdrop | mu +TAGDROP / mm | FAIL | FAIL | tags 0/2560 |

## Findings
1. **MU runs, bench stimulus format (not an RTL datapath error).** On receive, the MU lep (`ot_s81sl_slice_lep.mu.sv` g_rxm) clears its tag field [1077:1045] on every delivered beat: `rid <= strip(db) >> 1`. The tag itself only goes out on mu_rt when the beat is tagged XB/XQ. In every real XB/XQ beat these bits are spare (zero), so real traffic is not affected. The bench's TP-collective beats (`beat_word`, kind CTL) put 1024 bits of random payload at [1087:64], so payload bits landed in the tag field. Result: 14184 of 18132 beats mismatched in exactly bits [1077:1045]. Tags, ordering, deadlines and faults were all clean (tag_errors 0, late 0). The mm runs passed on data only because their 24 CTL beats carry no payload there.
   - Bench fix: `gen_golden.py` MU_SPARE keeps [1077:1045] zero on untagged beats in MU goldens. The single-user goldens are byte-identical (g564 checked).
   - Re-run: job m2 runs the same bM binary on the regenerated mr/md goldens. The fmt0 goldens and logs are kept as `*_fmt0` / `*.fmt0.*`.
   - Note for MU-S81: the comment says a *tagged* beat is delivered with its tag cleared, but the RTL strips every beat. Any future non-XB/XQ beat that carries data in [1077:1045] would be corrupted. Either strip only when `tagd(db)`, or write the contract down.
2. **landsel mutant not caught by the bench (bench weakness).** `OT_S81_LAND_MUT_SEL` reads the landing slot one cycle early, so beats land 2 cycles early per crossing (one landing at each end): first-beat latency 561 instead of 563. Data stays bit-exact, and the bench bounds a landing only from above (by its deadline), so it reports PASS. Under the static schedule the crossing latency is a fixed constant, so `tools/xdie_s81_2/lfix_check.py` now requires min(land - issue) == 563 (553 for LEG=0). With that check landsel FAILs (32 early beats) and every other LEG=1 run passes it.
3. asbound confirms the binding finding from the lane file: G8R2 0e6b9b710 binds the old lane file.

## Token composition
`record.json` (token_compose, 527 terms, built from `min`) feeds `results/arch/token_path_1018`. `tools/token_compose_xdie.py --check` passes. ds_rom AR goes from 1224.1 to 1219.4 tok/s (10.5% of token cycles now measured on current RTL), and ds_rom MTP is 3700.6 tok/s. The `multi_user` block in this record.json still comes from the fmt0 MU runs; collect.sh rewrites it once m2 is done.

## Codex canonical MU pickup, 10-19

Canonical m2 real-calendar, dense-calendar, and dense+FEC replays PASS on the existing binary. Each real/dense run lands 18,132 beats with no data errors, missed deadlines, tag errors, faults or link timeouts. All 3,840 expected tagged beats arrive. First idle-stream crossing is 563 cycles; no early landing. The earlier random-spare stimulus failure is preserved as fmt0 history.

Scope is three tagged users across the A/B/A endpoint copies and all eight TP4 collectives, not a full 46-user/10-MTP token. Per-user phase changes yield 1–2-cycle measured differences, so the record explicitly retains `all_users_equal_user0=false` and `user0_equals_single_user=false`; deadline/correctness passes do not certify unchanged single-user latency. The landing-select mutant passes the upper-deadline bench but FAILS the committed fixed-latency checker. Head, draft and native layer/producer integration remain open.
