Correct opposite-edge CPPR for a partial fall-range map (shared existing model).

Actual KVevent28w_c START-loaded proof had1528stage clocks,1920core taps and ONLY
cppr_node_range_ps[__source__@fall]=0 from the emitter. Its measured tree-node
fall arrivals existed separately. ca_pair_interval used `if fr` globally, then
looked up another common node in that partial map: missing key implied0credit.
Example actual hg_EN_1 clk -> firststage: commonnode130levels,674.915ps raw
rise range; riseinterval[-139.55,-75.11], oldfall[-806.12,613.17] solelybecause
commoncredit was discarded. This produced EDGE63/1 and CELL269/96 STARTfailures
(TT/FF) after actual fall measurements. Original failures retained below.

Fix: clock_cppr_ranges derives measured common-fall late-minus-early ranges from
already-calibrated arrays; planner and gate consume the same helper. Calibration
outputs stay byte-identical. ca_pair_interval limits credit by the fall range
ONLYwhen that SAME common node has a measured fall entry; a different node's
entry cannot disable documented rise fallback. When both exist, credit remains
min(rise,fall,launchspread,capturefallspread). True commonfall0 remains0.
Lookup is constant-time per pair. No SDC, clock target, derate, latency, RTL or
physical geometry changes; this restores the already-documented CPPR rule.

53focusedtestsPASS (6new plus inv/buf/cell/components/CPPR controls). Oldsource
negative partialmap testFAILs with [-10,190] instead of[90,90] (caught). Newtest
also preserves a real measured0range as[-10,190], so it does not invent credit.
Actual old/fixed twinSTA source runs in intel1 codex-kv-2249, same measured clocks.
Old source complete: sta_fall_spice_{edge,cell}. Fixed: sta_cpprfix_spice_{edge,cell}
(outcome receipt follows on completion, not assumed). Hold release remains
BLOCKED(kits), 56types without signed kit views; CA3595stillminCELLFF101.3ps.

Both-edge data source: existing DIE-KV42 stgrt die_TT/FF.sdf, read-only OpenROAD
annotation on SAME combo netlist (no repeated GRT). All3448risingtap arrivals agree
with original to max0.0142psTT; fall/node fields merged through existing shared
`tap_fall_merge --tree` and `start_stage_emit proof`. 15424nodes + source root0.
