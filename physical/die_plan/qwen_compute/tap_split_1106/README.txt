QC measured tap-density proposal, 2026-11-06, codex/qc-tapsplit-1106.

The existing plan already requests density, max1200 sinks, target960, radius200um, but has no complete placed sink inventory. Actual soft clock sinks pile on individual taps because the plan inventory underestimates them and the cap pass has no nearby tap with room. This event supplies actual placed clk-domain sink density through the existing sink_bins_file mechanism; target900 leaves headroom. No clock window, uncertainty, insertion target, RTL, data latency, hard-core placement or default POR changes.

Retained 3_place soft-sink models, with the exact nearest+capacity assignment (taps.assign mirrors clock_taps.tcl):
                         sinks  old/new taps   old/new maxload  old/new maxreach um
SUc cl19bb38ef            36622     30/74          5390/1026         485.038/193.184
CBN cldbcda913            52809     28/97          4968/1049         378.124/197.148
CBF q00_s2               59574     28/121         4226/924          413.980/170.612
ST_A cl9f076a5c           72232     32/125         7981/1078         329.686/185.086
ST_A clf4365a62           72166     32/125         7767/1200         329.956/185.086
New actual soft loads are <=1200 and actual reaches <200um. Input bins are8.64um squares, maximum Manhattan quantization8.64um. Model reports use the original actual points for the final load/reach checks, not just bin centers. SUc's one root-connected hard clock pin is excluded from the soft inventory because the pre-CTS hook correctly moves it to declared early core tap clk_c8; the other8 core taps were already connected. Existing early-core metadata is unchanged.

REVIEW: tap_split_geometry.png actually viewed. New endpoints follow dense legal channels, clear existing hard macro bodies/halos; existing macro geometry and PDN unchanged. PASS-COND FOR PLAN ESTIMATE ONLY. Clock pins/routes/PG access must be checked in the fresh generated kit, and the die provider must deliver the larger tap set under unchanged budgets.

QUALIFICATION LIMITS: no new CTS/STA/P&R; no hold or G5 claim. Source windows100/160ps remain. Re-splitting reduces tree depth/reach but does not itself prove zero-logic cross-tap chains safe. Candidate B needs short per-bit chain affinity or explicit hold-safe staging/padding; whole-station grouping is not enabled (can exceed1200 and regress). New tap ports require a coherent native parent/reset/START/profile event before physical adoption. Do not put a new clock grid beside an old bound-reset/clock identity or overwrite current approved sidecars. Do not blindly compose these measured soft-ring profiles with the CBN hardened-ring event; its sink inventory and obstacles differ and the guarded apply correctly rejects a changed type.

apply_event.py changes only the five studied types' clocks after exact base-type hash checks. plan_qc52 POR remains untouched. Input profiles carry source paths; source artifacts/probes remain at their recorded locations. model.json records actual results and proposed tap rows. No shared algorithm or source module changed.
