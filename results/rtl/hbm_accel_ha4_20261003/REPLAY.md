# HA4 first implementation milestone

Parent: `8564e79eaf906c820aec5eb92bfda1cca80ee43d`.
Branch: `codex/ha4-hbm-service-20261003`.

This is a default-off **clock-repair candidate**, not adopted hardware or an accelerator rate result. The model was committed before RTL (d20eadabe, cbd5ae48d). The 458 MHz placed KV lifecycle ceiling is historical evidence from 2078c269c; the successor has no timing verdict yet.

The new `ot_hbm_accel_kv_lifecycle` keeps the canonical interface. It registers the accepted command's 72-bit row selection, snapshots the actual row, registers eight admission flags, then dispatches. This adds two dispatch edges. It leaves the payload sector FSM, K byte RMW, V packed bytes, WRITE visibility/reverse fence, identity/sequence fields, quiesce/run-enable retained debt, and actual all-copy drain machinery intact. The wire-only `ot_hbm_accel_kv_native_lifecycle` attaches the existing protected native consumer/drain bridge. Enclosing STATE/Nash/Euclid authorities are not changed or installed by this milestone.

The provider successor differs from the original only by its module name and the default-off `commit_ready` typo changed to `commit_r`. Enabled provider behavior is unchanged; this milestone does not qualify that whole backend.

Replay the directed original/successor RTL comparison from this checkout:

```sh
python3 tools/hbm_accel_service_model.py
python3 tools/hbm_accel_service_gate.py --out /tmp/ha4-new-exclusive-evidence
```

The output directory must not exist. The fixture is read from the pinned parent and its hash checked. The runner executes actual Icarus RTL; there is no Python lifecycle simulation or model inference. It reuses the original fixture's finite simulation watchdog and imposes no process wall-time, RAM or file-size cap. Fixture SRAM and held endpoint ACKs are test authorities, not a production backend. The extra all-row hydration test uses one actual acceptance edge per fixture checkpoint record. The previous test stimulus that accidentally offered duplicate hydration is preserved as a failure, including its baseline failure.

Terminal PVE1 run: source `6e30dc4f7956e5122216bafb78e68f72c498faa1`, supervisor PID `2379659`, `/tmp/ha4-pve1-6e30-r1`, exit 0, 15 cases against both original and successor (30 RTL runs), 5.256 s. See `pve1_6e30_r1/evidence/record.json`; raw source fixture benches and logs are in `raw_fixture_logs.tar.gz`. Admission reserved 1 GB against measured 46 GiB available memory. No progressing peer job was restarted.

All compared response identities and sector orders match. Exposed dispatch costs +2 cycles, priced as 1.666 ns **at the unqualified 833 ps target**. The behavioral fixture clock is 10 ns. Every compared payload sector issue interval is unchanged; no sector II was doubled. Async event waits can hide the two dispatch cycles. All 72 retained reader rows were acquired and retired through actual fixture consumer, metadata and drain handshakes. Tests include mutated live command ports with a held response, paused accepted writer/staging debt, stale owner/address, readback corruption, and incomplete visibility/drain conditions.

Added sequential state: 245 bits (72 row-select + 164 snapshot + 8 flags + 1 extra FSM bit). `selected_word` adds 164 bits declared as combinational `reg`, with no sequential storage. The shared model's storage area is a proxy only; snapshot/protection logic, physical area, routed corridor and loaded clock qualification remain unknown. New control-state protection must be qualified before adoption.

Enabled native/drain composition elaborates with:

```sh
iverilog -g2012 -s ot_hbm_accel_kv_native_lifecycle \
  -P ot_hbm_accel_kv_native_lifecycle.ENABLE=1 -o /tmp/ha4-native.vvp \
  rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
  rtl/hbm_accel/service/ot_hbm_accel_kv_native_lifecycle.sv \
  rtl/hbm_accel/service/ot_hbm_accel_kv_lifecycle.sv \
  rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_native_consumer_drain.sv
```

The causal provider default-off C++ gate checks 64 input patterns, including `commit_r == 0`; `provider_default_off/build.log` has the exact build inputs. Replay with Verilator `-cc --exe --build -Wno-fatal --top-module ot_hbm_accel_causal_command_provider`, the original r14 package/PC/tag-owner, source SRAM models, the successor and `tools/hbm_accel_service_provider_off.cpp`. The 64x512 macro view used in that build is the byte-identical parent file `physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v`, exported with `git show`. No SS/FF constraint is changed by lint warning handling.

Remaining HA4 work: actual CK/2 expert service using 52ce3e9c1 with saved owners, finite tags and consumer ACK credits; the c52 fetch byte mapping; the existing Cicero per-stack scorer attachment; measured wire/CDC/credits/refresh critical path; real-program exactness; protection/area/corridor; SS60/FF25 in context; composed gain of at least 1%. The stream reference is 1.024 ns / 976.5625 MHz, not 1.2 GHz. The <=140 ns first-access target is **unmeasured**. No P&R, inference or token-rate claim was made here.
