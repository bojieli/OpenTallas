QC actual START provider integration, 2026-10-29

Mechanics vehicle only: exact old g15 paired table, not QC25/26 adoption.
The original bound top had 313 external pst_* inputs. The successor instantiates
451 existing table stages (1385 flops), drives all 313 inputs, preserves the
remaining public ABI, and exposes the actual stage clock ports for the patched
clock tree. The wire-only join adds no logic/cycles; any regenerated stage graph
has its own existing CA origin/boot price.

Source: epyc2 TOK WT event25/bind_clock_paired.json; matching intel2
/die-qc23-1028/g15/run/clk tree and measured TT/FF arrivals.
Canonical emitted files: intel2 scratch2/claude/codex-qc-start-provider-1029/emitted.
Elaboratable successor filelist: epyc2 scratch2/claude/codex-qc-start-provider-1029/
integrated/bind_start_provider.f (165 files; original live bind3 untouched).

GEOM FAIL: 744/763 registered START links exceed the existing 405 um reach:
449/450 stage-stage, max1647.54; 295/313 stage-partition, max2651.56.
See reach_census.json. Stages individually occupy legal rows with maximum
clock-node to stage offset9.18um; this does not establish link reach or timing.
No P&R or STA was requested for this failed graph. QC owns capture pin placement;
shared optional max-hop retiming preserves/adds clock-node stages and fails closed
when the measured physical graph has no legal intermediate node.

40 focused tests PASS: emitter/export, provider join, sequential lockstep and
swapped-output mutant, optional max-hop retention/retiming, impossible-hop failure,
missing coordinate failure, and existing START previous-plan behavior.

Successor: uniform capture taps and a 400um engineering target (405 gate unchanged)
materialized 2117 stages /8338 FF, 2429 registered links. Conservative complete
flop-row envelopes to each other and to QC's exact chosen capture input pins pass
at maximum403.65um. All2429 START intervals are phase clean on the g15 measured
physical paths. Recomputed origin maximum323cycles, tree depth108; data0fail using
old frozen data intervals (not a regenerated current-die proof). The graph image
was rendered and inspected: long spines now contain regularly spaced providers,
with no long unregistered stage-stage segment. Current26 load/phase/physical gates
remain required; this vehicle is not approved for adoption.

Canonical intel2 scratch2/claude/codex-qc-start-provider-1029/physical_uniform:
plan_providers.json contains actual emitted provider rectangles+registered edges;
plan_providers.provider.json records geometry; plan.json records boot price;
bind.json and emitted/start_stages.{json,sv} are corresponding RTL sources.
The new optional start_provider_plan.py materializes this provider under the
existing landing_network.start_tree contract. landing_contract checks physical
reach, exact stage rectangles and real endpoint pins, complete incoming edges,
parent/tree reachability, registered ends, and equality to all declared pst/rs
boundary uses. Defaults remain unchanged. No ties or unused-input exceptions.
