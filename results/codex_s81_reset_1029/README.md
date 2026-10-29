# S81 reset assertion width: release offset is not a hold window

The 02:48 COORD proposal to set an S81 LEC reset contract to the minimum core release offset plus two sync stages is insufficient. Only the root `ot_dp_rsync_s2` has asynchronous assertion. The generated `ot_dp_rrelay` forest carries assertion synchronously, with `always @(posedge clk) q <= d` and no initial state. Its path depth delays the low and high edges together; it does not widen the low pulse.

A minimum mechanism vehicle uses the exact two generated cells copied from `tools/die_plan/gen_rtl.py` at source 6344fa58c and a 12-relay chain. The clock runs at 833 ps. A one-clock asserted reset is tested both at cold boot with unknown relay state and after the forest is fully released. Both produce only three known-low clock edges at the sink, despite 14 clocks of release latency. Consequently neither case establishes a reset assertion window above the default four edges used by `lec.reset_contract_gate`.

Run on intel2 through ot-run, unit `oth-ubuntu-2774618-1793267998`, exit 0:

```
ACTUAL_CELLS relay_depth=12 expected_release_latency=14 root_known_low=3 sink_known_low=3
OFFSET_PLUS_SYNC_IS_NOT_ASSERT_WINDOW: depth12 and sync2 yield only 3 low edges
WARM_RESET root_low=3 sink_low=3
```

Reproduce with `iverilog -g2012 -s tb -o /tmp/reset-width cells.sv counterexample.sv && vvp /tmp/reset-width` on an admitted fleet host. No reset states are assumed or initialized in the forest. This demonstrates the failed inference; it does not claim the selected 12-stage path is an extracted S81 core path. The inference fails for every positive pure relay depth, including the actual S81 forest unless another element explicitly extends the hold.

No reset contract was emitted, no LEC reset window was raised, and no RTL changed. A longer contract needs an implemented hold mechanism or a separately declared and proven external reset protocol. The source root could enforce a fixed hold after every assertion, with the added boot clocks composed into reset/START timing. Core proofs may also close from the existing default window without this change.
