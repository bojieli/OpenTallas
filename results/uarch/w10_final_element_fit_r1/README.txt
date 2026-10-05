W10 actual-q / fullmapped-final-element fit prerequisite r1.
Base1c8ae00ad; isolated codex/w10-final-element-fit, /home/ubuntu/w10-allport-audit.
Verdict ACTUAL_Q_FOOTPRINT_UNBOUND_FULL_ELEMENT_FIT_HOLD. No adoption/build.

Replay:
 python3 tools/w10_final_element_fit.py --output /tmp/w10-final-fit-review.json
 cmp /tmp/w10-final-fit-review.json results/uarch/w10_final_element_fit_r1/fit.json
 python3 -m pytest -q tests/test_w10_final_element_fit.py tests/test_w10_clock_site_budget.py tests/test_w10_fullmap_slot_fit.py
No synthesis/P&R, restored checkpoint, external worker or scalar/expert replay.
All normal replay inputs are committed. Tool uses unchanged unified model APIs;
ephemeral pitch entries are removed. Model source SHA2da5b6d9...260c45 unchanged.

Dependencies already in base: published0cdd/a458 fixed625-row clock-site budget;
883075491 fullmap slot API; cfa564/bc1cc local capture source area already included;
584168 fullmap structure and synth evidence; historical q p12q9 terminal/preflight;
W18 p5 actual nonclosing abstract and its source-pinned LEF; Ram2118b293 integer
expert-only residency summary. No RTL/source pins, current plan, main/TASKS edits.

Coordinate boundary: Ram0fb46 owns expert-stage allocation and conditional q
transfer; Godel owns actual scalar capacity. This tool does not rerun their
allocators/interpreters or supply guessed scalar area. The coordination record
/tmp/claude-1000/queue/W10-final-q-fit-owner.json requests their eventual bindings;
no reply/agreement is claimed. Confucius spatial clock/PG remains disjoint. No
power/activity calculation or wire-baseline subtraction duplicates Ramcap/a820.

Actual geometry classes retained separately:
1) failed p12q9 requested510.84x126.9um, density0.6, source d417de73: not a final
   abstract. Its actual q standard-cell/geometry metrics ARE recovered below.
2) historical p5 measured LEF513.756x131.76um matches committed abstract SHA.
   It is routed but NOT closed (setup-209ps,1DRC), not current FAST/PP4096 q.
3) W18 head q_tile_1p2 synthetic476x126.9um placeholder: not actual q.
The q preflight lacks6_final ODB/SDC/SPEF/V and final corner abstracts. Geometry
metadata, passing terminal markers or unpinned/empty files cannot confer binding.
The exact logical capacity2*8192*274 equals4*4096*274=4489216bits. Actual four
4096 LEF macros occupy31525.4592um2. This storage-capacity identity does not price
or qualify mux/capture/control/clock/pin channels. Preserve the model's subtraction
of two8192 baseline macro footprints,30004.94016um2, and its149.6/142.4 storage
density conversion; do not replace it blindly with four4096 LEF areas.

Recovered actual failed q areas from the preserved retirement archive:
 /home/ubuntu/w10-w18-retirement/w10qjobs_legacy_light.tgz
 SHAe20f2641bff90d379520d0ba01f2d25b8d4f82ab795748da4b5425dff1213bc3
Only config.mk and1_synth/2_1_floorplan/4_1_cts/5_1_grt JSON members copied verbatim
to legacy_q_metrics; origin.json pins every member. No source/checkpoint restored.
The original failed archive and all terminal records remain unchanged.
Synth stdcells21809.9um2; CTS24192.8um2; GRT24297.8um2; four macros31525.5um2.
Observed die64825.6um2/core64549.7um2; GRT macro-excluded utilization0.735754.
Even synth+macros at50% needs75145.3um2 before escape/halo,10595.6um2 more than
the observed core. This refutes uniform50% area fit for that legacy mapped q;
it does not establish a new-source q synthesis result or full routing failure.

Necessary site projection at the same510.84um width, using unchanged macro,
eight escape and top/bottom halo site reserves from883, density50%:
 - legacy synth area:612rows, outline510.84x165.78um; model53layer stages
 - legacy GRT area:648rows, outline510.84x175.50um; model55layer stages
Original q record supplies zeroX border and0.54um totalY border, retained exactly;
the BF16 slot's4.32um outerY frame is not transferred to these q projections.
Historical GRT already contains CTS/repair cells; do not add the separate BF16
3873-buffer reserve to it. Extra current-q wake/capture/clock/hold/site/PG costs
remain unknown. These projected heights/stages are arithmetic witnesses, NOT
proposed q replacements, retry/tuning or qualified pack pitches. q transfer FALSE.

Fullmapped BF16 element stays91733FF/8ICG/4macros,62705.9um2 stdcell plus existing
903.49344um2 clock reserve,625rows/50%density,1002.89x173.07um outline and39.46534
um2 spare standard-cell capacity. It is a complete model column, not a measured
current q area. The13case/240exact-row XF8 projection and retained clock-duty
traces do not supply final SS/FF, q area or wire-power-baseline subtraction.

Composed q-footprint ceilings with that BF16 outline in the unchanged analytical
storage model (no added scalar reserve, fractional stage plan only):
 stages41:56924.903um2;44:63671.402;45:65974.626;46:68316.417;
 stages47:70700.654;49:75540.755 (full precision in fit.json).
At45 stages requested q64825.596um2 leaves3.8201355mm2 usable-field headroom.
Max q width at126.9um height519.894606um; max height at510.84um width129.149294um.
These are numerical ceilings, not coordinate searches or dimensions for a build.
Every additional1mm2 beyond the existing scalar/hub charge lowers this q ceiling
by300.782408um2/pair. Actual incremental scalar reserve is null until Godel binds
it. The symbolic dependency lets owners compose their result without duplicate
scalar sizing. Requested q gives45stages; historical p5 geometry46; historical
p5 tiling522.72x140.4 gives49. None receives actual-q transfer or rate credit.

Ram expert-only integer plan remains46stages,341experts/stage,3749historical q
pairs,1023maximum expert phase entries,184320expected slices; its actual q strip
reconciliation and historical q transfer remain FALSE. It is not the45stage
fractional whole-field area plan. Dense/HC/constants, integer full-stage packing,
descriptor/phase service and actual scalar capacity are still owner prerequisites.

Next admissible input: current-source fullmapped q footprint/component proof
meeting the composed ceilings plus actual scalar reserve and integer stage map;
legal final element/PG and source-bound SS/FF/exactness are required for adoption.
No new build or failed lever tuning follows from these sensitivities. Element,
interface and full-token latencies remain null; clock1.2GHz, SS60ps/FF25ps and
serial0.9GHz inherited model unchanged. Originalp12q9,c8,FRONT_PAR,bankmap failures
retained. No model generator, RTL, spatial-clock, main/TASKS or push changes.
