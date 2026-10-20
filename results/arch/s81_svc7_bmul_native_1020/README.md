# MODEL INTEGRITY HOLD

COORD01:13: Liberty-to-Verilog DFFASRHQN functional model may be wrong; canonical QN/normal/clear/preset/both-active truth coupon is pending ROOT /root/kv_takeover. ALL native-cell simulation PASS/negative witnesses and unfinished SAT evidence below are PROVISIONAL and cannot qualify adoption. Exact own SAT YosysPID2342269 ep7 terminated by SIGTERM after preserving its incomplete log. No other process was stopped. Native area/fanout results remain valid. Rerun native graph exact/mutant/SAT with verified canonical cell models before adoption. Source-RTL versus golden bench separately launched, independent of native models.

# SVC7 BF16 multiply bounded native leaf (candidate only)

From 4347ce78d with SCC-aware helper cf32860cf (dependency; not duplicated in this source commit). No production caller changes. Preserve four heads, four chunks of eight and the original accumulation order.

Model precedes source. Input pin capture adds one edge: original ML6 -> LAT7, II1, +0.833333ns at1.2GHz. The 128 product paths/group gain one common edge, not128 serial edges. Area is measured actual mapped cells, not a buffer estimate:173.58948um2 retained versus170.73180um2 wrapper baseline;305FF versus294. Eleven additional real primitive cells. Golden full8x8 product simulation on Verilator5.050 PASS19991 comparisons, including single-edge and repeated multi-edge in-flight resets. No output-valid port exists. External consumer must ignore the initial pipeline contents for9 edges (two reset landing + seven arithmetic). Subsequent reset pulses never mask output comparisons; reset injects PAD only before the original operand cut and retains arithmetic output timing.

The graph ledger's generic statement that clones agree after one clock is insufficient when upstream clones begin independently. This candidate requires the committed unconditional-output SAT miter, with every initial FF free, only initial reset steps1..3 assumed, reset unconstrained thereafter, and assertions atsteps10..18. Proof was pending when this README was first written. This is bounded proof evidence, not an induction claim.

Checklist before layout:
- Pins: actual33 data input FFs; output FFs inherited; rst_n drives first of2 real landing FFs. Native census has no tied functional outputs.
- Reach: UNPROVEN without geometry; no layout gate authorized.
- Fanout: direct and post-keep mapped audit PASS zero drivers>32 including reset/raw ports; graph targets24.
- Depth: estimated406.7ps/12levels, no routed timing qualification.
- Storage:305 FF bits total, below2kb; no runtime-indexed storage.
- Floorplan: pending measured-area sizing and pin map; no macros.
- Clock:305 sinks; insertion/spread unmeasured; TT/FF CTS required.
- Schedule: fixed II1, +1 edge priced; not adopted in parent/compiler.

`probe/native.v` is technology-specific proposed source. `probe/mapped.json` and retained netlists, exact Liberty functional models, input SHA receipts and all stdout logs retain provenance. The original failed attempts (missing staged prefix/lint file) remain in remote out_graph/out_graph2/retention_missing_lint; they are tooling failures, not a native qualification result. No gate, submit or performance claim.

Negative control `BMUL_RESET_MUT=1` bypasses reset at candidate boundary, caught5 mismatches and BMUL_FAIL (exit1); witness in probe/verify_mut/run.log.

Source RTL-only wrapper vs original full8x8 golden (no Liberty models) PASS19991 comparisons Verilator5.050, including all reset pulses; rtl_verify/run.log. Actual candidate sequential inventory only DFFHQNx1_ASAP7_75t_R (305), whose generated model QN<=~D appears consistent; no DFFASRHQN instance occurs. Await ROOT truth coupon before removing native-model HOLD. SAT process ignored SIGTERM; exact KILL of2342269 completed exit137 and no output assertion verdict.
