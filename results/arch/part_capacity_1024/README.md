PART-CAP capacity findings, updated 2026-10-25 05:56 PDT

The measured runs do not show a memory or router wall at 400k cells. Keep the existing 400k release cap while finishing timing closure; this measurement does not authorize changing it. For new replicated physical work, prefer ~250k cells when the microarchitecture permits: repair stages are largely serial and can dominate a multi-million-cell run.

| Vehicle | Placed cells | DRC | TT setup ps | FF hold ps | Container peak GB | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| N1 | 77.7k | 0 | +214.5 | +3.6 | 13.1 | Legacy timing clean |
| N4 | 304.7k | 0 | +164.0 | +1.55 | 38 | Legacy timing clean |
| N7 | 535k | 0 | +184.2 | -19.52 | 44.8 | FAIL boundary hold |
| N14 | 1,067,746 | 0 | +66.33 | -25.29 | 57.8 | FAIL boundary hold |
| N27 TT/TNS10 | ~1.86M synthesized | — | — | — | 22.9 | FAIL missing source include before GRT |
| N27 old WC/TNS100 | ~1.86M synthesized | — | — | — | 35.8 | Retired after structural hold stall; records preserved |
| N44 old WC/TNS100 | ~3.04M synthesized | — | — | — | 33.9 | Retired after structural hold runaway; records preserved |
| N27 TT isolated resume | ~1.86M synthesized | — | — | — | 34.9 current | GRT complete; legacy-reset setup repair still live |
| N44 TT/TNS10 | 3.23M placed components | — | — | — | 53.1 | GRT live after CTS hold runaway |

These are historical capacity vehicles, not SIGNED release blocks. The original WC routing / SS sensitivity is retained only as old measurement evidence; use TT setup and FF hold, 60/25 ps uncertainty and 833 ps for new work.

N14 hold is dominated by input-to-register paths (-25.29 ps, 117 violating D pins); register-to-register is -0.18 ps and outputs +80.23 ps. N7 similarly has input hold -19.52 ps, versus register-to-register +3.18 ps and output +45.55 ps. This is a boundary/reset repair problem, not evidence for a capacity threshold. No constraints are waived.

The N27 TT/TNS10 GRT failure is an omitted source file: physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl. Missing final SDC is a downstream symptom. Preserve completed CTS and resume from a separate checkpoint copy with the complete source include.

Runtime is limited mainly by serial repair. N27 CTS used 13,382 s wall / 20,110 s CPU (1.50 mean threads), N44 TT placement resize used 4,623 s wall / 10,085 s CPU (2.18 threads), and N44 TT DPL used 5,515 s wall / 10,126 s CPU (1.84 threads). More requested threads do not accelerate those stages. Large old WC floorplan repair with TNS100 took hours; TT/TNS10 reduces the repair workload. New flows should use the owner's 0..5 ps in-flow hold margin, structural hold stopping gate, and current reset/face contracts rather than cloning these old kits.

Raw fresh snapshots are in runs/collected_1025/. Original failed verdicts and completed jobs are preserved.

Fresh collection at 05:56 PDT: the N27 isolated resume completed global routing in 3,281 s (54m41s), 1,931,424 routed nets and 10,400,001 um wirelength. It is now in setup repair at WNS -137.923 ps and 995 negative endpoints, with the worst endpoint on the old per-tap asynchronous `rst_n` / `RESETN` path. This is a reset-architecture failure in the legacy vehicle; the production successor must use the current control-only reset wavefront. Its current container footprint is 34.87 GiB and about one CPU. Its copied `5_1_grt.log` is the predecessor's failed attempt; the active resume is `5_1_grt.tmp.log`. Do not mistake the old 422-s record for completion of the fresh run.

N44 TT is still in global-route resource construction after pin access completed in 1,775 s. It has reached 53.1 GiB sampled peak, not its requested 300-GiB reservation. Completed CTS cost 19,260.5 s wall / 32,527.2 s CPU, only 1.69 mean active threads. Neither unfinished run establishes routed capacity or timing closure. These snapshots provide progress and resource data only; their true final runtime/peak memory remain pending.

The old large-vehicle hold loops also lack separate FF-mode boundary timing: the N44 max/min QDM references differ by 233.672 ps, near its frozen -226.761-ps in-flow hold WNS. Correct successors use TT setup plus an actual FF mode, corner-consistent insertion, current boundary contracts, and the structural stop gate; buffering against the old mixed-corner reference cannot qualify the result. No extra capacity route is launched while release designs already exercise the corrected flow.

Fresh snapshots are in `runs/collected_0555/`. No failed record was replaced. Original retired-run evidence remains under the hosts' `part-cap-records/` directories. Leave the two retained jobs intact and harvest final runtime/peak data when they finish.
