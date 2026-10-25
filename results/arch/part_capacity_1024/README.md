PART-CAP capacity findings, updated 2026-10-25

The measured runs do not show a memory or router wall at 400k cells. Keep the existing 400k release cap while finishing timing closure; this measurement does not authorize changing it. For new replicated physical work, prefer ~250k cells when the microarchitecture permits: repair stages are largely serial and can dominate a multi-million-cell run.

| Vehicle | Placed cells | DRC | TT setup ps | FF hold ps | Container peak GB | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| N1 | 77.7k | 0 | +214.5 | +3.6 | 13.1 | Legacy timing clean |
| N4 | 304.7k | 0 | +164.0 | +1.55 | 38 | Legacy timing clean |
| N7 | 535k | 0 | +184.2 | -19.52 | 44.8 | FAIL boundary hold |
| N14 | 1,067,746 | 0 | +66.33 | -25.29 | 57.8 | FAIL boundary hold |
| N27 TT/TNS10 | ~1.86M synthesized | — | — | — | 22.9 | FAIL missing source include before GRT |
| N27 old WC/TNS100 | ~1.86M synthesized | — | — | — | 35.8 | Running GRT |
| N44 old WC/TNS100 | ~3.04M synthesized | — | — | — | 33.9 | Running CTS |
| N44 TT/TNS10 | ~3.04M synthesized | — | — | — | 32.9 | Running CTS |

These are historical capacity vehicles, not SIGNED release blocks. The original WC routing / SS sensitivity is retained only as old measurement evidence; use TT setup and FF hold, 60/25 ps uncertainty and 833 ps for new work.

N14 hold is dominated by input-to-register paths (-25.29 ps, 117 violating D pins); register-to-register is -0.18 ps and outputs +80.23 ps. N7 similarly has input hold -19.52 ps, versus register-to-register +3.18 ps and output +45.55 ps. This is a boundary/reset repair problem, not evidence for a capacity threshold. No constraints are waived.

The N27 TT/TNS10 GRT failure is an omitted source file: physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl. Missing final SDC is a downstream symptom. Preserve completed CTS and resume from a separate checkpoint copy with the complete source include.

Runtime is limited mainly by serial repair. N27 CTS used 13,382 s wall / 20,110 s CPU (1.50 mean threads), N44 TT placement resize used 4,623 s wall / 10,085 s CPU (2.18 threads), and N44 TT DPL used 5,515 s wall / 10,126 s CPU (1.84 threads). More requested threads do not accelerate those stages. Large old WC floorplan repair with TNS100 took hours; TT/TNS10 reduces the repair workload. New flows should use the owner's 0..5 ps in-flow hold margin, structural hold stopping gate, and current reset/face contracts rather than cloning these old kits.

Raw fresh snapshots are in runs/collected_1025/. Original failed verdicts and completed jobs are preserved.
