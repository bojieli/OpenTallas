# Streaming HBM controller closes 1.2 GHz at SS (r8b, 2026-10-04)

The stream controller (`rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv` and `ot_hbm_r14_stream_stack.sv`, brought in from 52ce3e9c1) now closes sign-off at 0.833 ns. The change adds no cycles: every output is cycle-identical to r6.

## Result (one channel slice, NCH=1, REF_MODE=1; the 52ce3e9c1 REPLAY step-4 recipe, ADDER_MAP_FILE= disabled, 16 threads)

| Rev | Period | SS setup WNS (60 ps) | FF hold WNS (25 ps) | Fmax | Cell area | Record |
|---|---|---|---|---|---|---|
| r6 (52ce3e9c1) | 0.833 ns | -4.7 ps | met | 1.194 GHz | 2,612 um2 | `r6_physical-ss-r6-NOT_MET.json` |
| r8a | 0.833 ns | -20.4 ps | +4.0 ps (ORFS WC,BC) | 1.172 GHz | 2,635 um2 | `physical-ss-r8a-0833-NOT_MET.json` |
| **r8b** | 0.833 ns | **+6.28 ps** | **+5.11 ps** | 1.210 GHz | 2,691 um2 | `physical-ss-r8b-0833-PASS.json`, `corner_sta-r8b-0833.json` (closes_signoff=true) |

DRC is 0, and there are no slew, cap or fanout violations. The setup margin is thin (+6 ps), so a re-route at a different floorplan or utilisation can move it by about +/-20 ps.

## RTL changes (exact; r6 sha256 7489b12b... becomes r8b 72c9ee6f...; the stack is unchanged at 109133bf...)

1. **Zero flags are registered.** `aok`, `rcd`, `rrdl`, `faw` and `ccdl` each get a registered `== 0` flag. The flag is computed from the same event priority as its counter, so it equals `(counter == 0)` on every cycle. This removes the reduce-OR from the start of the r6 worst path (`rrdl -> act eligibility -> c_oh`).
2. **Set selection is an AND-OR.** The current set `k = j[9:7]` is held as a registered one-hot `koh`, and `k+1 <= last` as a registered flag `k1v`. Both are updated with `j` and `last`. The ACT group selection becomes an AND-OR instead of a k-decoded mux. This was the r7 and r8a worst path.
3. **RD bank is a registered one-hot.** The RD bank is held as `rd_oh`/`rd_bgoh`, and `credit != 0` as `cred_nz`. Both are updated with `j` and `credit`. `rd_ok` is then an AND-OR of flops, with no `j`-decoded 32:1 mux. This was r8a's new worst path, the `j -> rd_ok -> j` RD loop.

## Exactness

- **Lockstep (`tb_stream_pc_lockstep.sv`).** The bench runs the r6 PC (`ot_hbm_r14_stream_pc_r6_ref.sv`, a renamed copy) against r8b. It covers REF_MODE 0/1, PC 0/1 and seeds 1-4, 400k cycles each. Every output is compared on every cycle: **0 mismatches**.
- **Bench (`rtl-bench-r8b.json`).** All 28 r6 cases (`bench_cases.txt`: REFpb/REFab, hint, phase, b2b, cred) produce logs **byte-identical to the r6 logs**, apart from runtime lines.
  - The primary case `-GREF_MODE=1 -GHINT=320 -GPHASE=0` gives worst 1,092,608 ps per layer, 0 violations, 0 bad sectors, PASS.
  - Negative controls mut1 (tRCD), mut2 (bit flip) and mut3 (tREFIpb) all FAIL, as they should.

## Cost

- **Cycles:** +0.
- **Area:** +79 um2 per slice routed (+3.0%), which is +1.3 k um2 per stack (16 slices).

Replay: `route.sh <tag> 0.833`, `run_bench_r8.sh` (LOGS=dir) and `tools/w18/corner_sta.py --orfs-dir <keep-workdir>/orfs`, all on ot-epyc1tb under `/srv/opentallas-scratch/claude/hbm-clock-loops/stream/`.
