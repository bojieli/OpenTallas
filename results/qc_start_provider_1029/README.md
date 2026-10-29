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
