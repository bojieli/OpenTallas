# HA2 first concrete milestone: priced 20-port snapshot endpoints

Base: `8564e79eaf906c820aec5eb92bfda1cca80ee43d`. Build source: `045cc74114fcdbaa1576f27fa6fe3537a7890ee4`. All files are additive. The GPU-organised ablation, ROM collective sources and DS ROM PAR2 physical files are unchanged. This is an experimental, default-off snapshot transport, not an adopted accelerator rung.

`tools/hbm_accel_direct_links_model.py` reads the pinned unified model's DFF area constant without loading its unrelated physical inventories. Its price records precede the RTL bench. The model charges 20 bidirectional ports, 40 SerDes lane pairs, 551 bits/record, four serialization cycles, two 33-stage wire legs/hop, finite storage, 15 six-source relay muxes, fanout, routing tracks and the proposed exact tree. SerDes area/power are transferred estimates, not measured PHY data. The 130 ns FEC service is explicitly an estimate. Corridor capacity, mux/add/clock/repeater power and full area remain unknown. The original r1 two-hop estimate omitted local-port contention. The preserved r3 correction charges own + five relays behind returning single-flight credits: 2,595 cycles / 2,162.5 ns. This snapshot architecture misses the model target before any system qualification; no RTL tuning is performed.

`ot_hbm_accel_gather_die` provides one 512-bit word/rank/transaction. It broadcasts locally and to equal-lane counterparts in the other five groups, which relay to their local peers. Local outputs send the captured own word, then remote groups in fixed order; backpressure cannot change a held output. Replies appear in rank order and hold their transaction tag. Identity, route source, bounds and duplicates fail closed with a sticky fault. **The caller must coordinate transaction start across all ranks and retain the lease until every rank's response is consumed.** Independent early next-epoch issue is not supported by this snapshot interface.

The separate snapshot reducer implements an adjacent-pair FP32 RNE tree with a delayed odd tail, without zero padding. The compiler API emits W19's eight separate eight-contributor trees and its final BF16 rounding contract. This does not establish the real W19 program/head gate. The reducer has no output ready input: its caller must reserve output capacity before launch and retain the captured snapshot. The arithmetic bench checks a one-lane 96-leaf pipeline against existing `hdc_golden.add`; it is not a whole-collective measurement or a 16-lane integration gate.

`ot_hbm_accel_link_stage_model` is a simulation boundary: explicit endpoint wire registers, estimated PHY/FEC delay, serialization and a single returning credit. It is **not** a synthesizable qualified PHY, a CDC test, an implemented FEC/CRC checker or a mutable-state protection qualification. There is no HBM/refresh model in this bench. These missing system gates exclude adoption.

The 96-rank run is `ot-agidock128:/tmp/ha2-direct-links-045cc7411`, supervisor PID 419075. `run_045cc7411.sh` captures the exact commands. It builds once under the admission guard and preserves objects, logs, terminal exit files and input hashes. No deadline or per-process limit is imposed. The initial 8 GiB admission estimate was too small: four compiler workers grew to about 41 GiB RSS, so this inventory belongs on the large-build host for future runs. The progressing run is retained.

The additional endpoint fault gate uses unchanged gather RTL at `a4d53ea7a`: 44 directed checks, zero mismatches, Icarus exit 0. Five graph/compiler/price tests passed. The 96-rank gate completed without a rerun: compile and runtime exit 0, 27,648 packet comparisons / 442,368 FP32 bit lanes, zero mismatches, and all source/fixture hashes unchanged. Snapshot issue-to-last-result cycles are 2,588 (first, unstalled), 2,732 (downstream backpressure), and 2,700 (next unstalled epoch, retaining returning-credit debt). At the simulator's 0.834 ns period these are 2,158.392 / 2,278.488 / 2,251.800 ns. One-picosecond timing precision rounds the intended 416.667 ps half-period to 417 ps. This is conditional RTL simulation, not a qualified silicon clock or full-context latency.

**Verdict: REJECT_SNAPSHOT_CANDIDATE, default-off.** The first-word latency alone is 2,493 cycles / 2,079.162 ns. This misses the candidate gate well before adding real system CDC or refresh. The fixed intercept and payload slope are not separately fitted, so the W15 fixed 777/824 ns references are not a matched slope comparison. No candidate tuning or physical run follows this rejection.

The queued reducer did not run: its original Icarus elaboration exited 95 because the launcher omitted the existing `ot_hdc_lzc32` dependency. This is a launcher omission, not a numerical verdict. The complete failed log is preserved, and the gate is not repeated. Whole-collective all-reduce, the real W19 golden/head and 96×512 top-k remain unmeasured.

The runtime used 80,556 KiB peak RSS and 77.34 seconds wall time. The compiler group exceeded the initial 8 GiB admission estimate; a sample of its four workers totalled about 45.3 GiB RSS. This is an observed sample, not a full-build peak measurement. Future builds of this inventory require the large-build host's admission guard. Original remote objects remain intact.

`terminal_045cc7411.json` records the measured candidate and every failure. The measured composition adopts no HA2 rung and has no measured per-user gain. Collect existing artifacts without any execution with:

```sh
python3 tools/hbm_accel_direct_links_collect.py \
  --run results/rtl/hbm_accel_ha2_20261003/run_045cc7411 \
  --faults results/rtl/hbm_accel_ha2_20261003/faults_a4d53ea7a \
  --price results/uarch/hbm_accel_direct_links_20261003/price_r1.json \
  --out results/rtl/hbm_accel_ha2_20261003/terminal_045cc7411.json
```

The collector refuses to overwrite evidence and performs no build, simulation or inference. A failed latency candidate is rejected without tuning around its verdict. No P&R, routed corridor, SS/FF closure, whole-collective slope, 96×512 select, or composed single-user gain is claimed by this milestone. The main model and all defaults remain unchanged; HA0 can consume these additive price records.
