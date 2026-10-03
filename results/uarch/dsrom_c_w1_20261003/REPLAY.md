W1 implementation and measured rejection, source parent `4a18e3cc0b4c04f75a2e76e4535d9560cdc730c6`.

New successor modules and generator only; existing callers remain on the legacy return network. No ROM ECC was added. The generator exposes a return-only handshake boundary: the real nonstallable element needs a finite producer buffer and actual stop authority before system integration. That join was not fabricated.

Actual host: ot-agidock128 (`vm-xry57mhfyn`). Before admission: 23 GiB MemAvailable, load16.32,659GiB free disk; no live W1 job. Both small runs used `~/bin/admit.sh 1`; measured simulation RSS nodes8572KiB, root7912KiB. Supervisor427265 and subsequent ragged supervisor428605 both terminated with exit0. No duplicate full build, P&R, inference or L0/L20 program run was launched.

Reproduce in an empty output directory on the VM (the admission script waits against actual host capacity; there is no time or address-space limit):

```bash
TASK_W1_RUN=/home/ubuntu/dsrom-w1-replay-unique
~/bin/admit.sh 1 -- python3 tools/dsrom_credit_return_gate.py --out "$TASK_W1_RUN"
iverilog -g2012 -s tb_dsrom_credit_ragged -o "$TASK_W1_RUN/ragged_golden" \
  rtl/ot_fp32_rne_pkg.sv rtl/v41rom/ot_v41_ret.sv \
  rtl/v41rom/ot_v41_ret_credit.sv rtl/v41die/ot_v41_retn_credit.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv \
  "$TASK_W1_RUN/ragged5.sv" rtl/test/tb_dsrom_credit_ragged.sv
~/bin/admit.sh 1 -- vvp "$TASK_W1_RUN/ragged_golden"
python3 tests/test_dsrom_credit_topology.py -v
python3 tools/gen_dsrom_credit_return.py --active-pairs 2682 --regions 128 --out /home/ubuntu/dsrom-w1-generated-unique
```

`actual_r1/raw_logs.tar.gz` retains all compile/runtime/resource logs, terminal exit files and exact original launch scripts. `actual_r1/result.json` is the unmodified original runner output. The separate ragged test ran against the same original RTL export, without repeating passed node/root tests. `pins.json` lists input and artifact SHA256. Initial prebuild ledger is retained, followed by a successor final model using both unified and Scenario C reservation cells.

Measured:256 summed rows exact vs RD64,582 vs267completion cycles, peak node side4/4,315credit-stall cycles, launch-to-parent-pop7cycles, saturated slot-reuse9cycles. Full ROOT128 directed case129rows drains at394cycles, peak held128, peak queue63,1blockedcycle. Actual NP5/R2 ragged tree64rows exact against the scalar RNE golden,305cycles; nseg3/5, non-sibling physical neighbors, cancellation, positions0..5. Topology coverage tests pass for NP1/5/17/2682/4096 with no padding leaves. An initial broad unittest discovery also attempted an unrelated ABI3 package absent in the sparse checkout; direct own-test invocation passes and is the reported topology gate.

REJECTED: this RD4 launch-reservation implementation has9cycle saturated reuse versus the requested4. Its54.12% saturated-fixture rate loss is not a L0/L20 measurement. No rescue loop, deeper-RD hardware or physical run followed. Analytical RD16 pricing is a sensitivity only; not built. L0/L20 exactness/occupancy, busiest-stage loss<=1%, synthesized area<=7mm2, hub routing and SS60ps/FF25ps remain unqualified. W2/W4 must not credit this implementation's area saving.

MODEL: Scenario C storage reservation6.82475mm2 plus unified adders3.15821mm2 already gives9.98296mm2 before credit control, root queue-compare array, muxes, pipeline alignment, CTS and routing. This is not synthesized area. The initial generic unified DFF proxy5.24981mm2 is also not hardware credit. No measured tok/s, kW or die-count delta is available.
