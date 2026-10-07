# Default-off checked-bank four-state diagnostic

All eight minimum Icarus diagnostic cases pass. The new test-only module is a source-preserving copy of the checked bank with `SIM_FAIL_CLOSED=0` by default. Its additional unknown-observation guard is active only in simulation; under SYNTHESIS the predicate is constantzero. The predecessor file and default production paths remain byte-identical. Removing the added guard and restoring the module header reconstructs the original file exactly, checked in `source_preservation.json`.

The guard prevents advancement and sets stickyfault when an active raw read/ACK identity is unknown, postverify compares unknown decoded or merged data, publication identity is unknown, or FSM state is unknown. Known corrupt postverify data continues to fail through the original checker. This does not replace `!=` with `!==` or claim added physical protection. The diagnostic emits no silicon fault-detection hardware and does not repair the underlying four-state bank-OR propagation issue.

| Injected observation | Diagnostic off | Diagnostic on |
| --- | --- | --- |
| Known matching decoded payload | One checkedACK | One checkedACK |
| Unknown decoded payload | One checkedACK: retained predecessor escape | Fault, zero checkedACKs |
| Known one-bit corrupt decoded payload | Fault, zero checkedACKs | Fault, zero checkedACKs |
| Unknown rawACK owner | One checkedACK: retained predecessor escape | Fault, zero checkedACKs |

Every case submits one actual write to the unchanged full16 raw backend and observes its actual raw physical ACK. The test then deliberately injects a known, unknown or corrupt VERIFY observation, or an unknown rawACK owner. These explicit injections isolate the diagnostic mechanism: the known injection is **not evidence that actual SRAM readback passed**, and no result upgrades the earlier two-state protocol gate or four-state failure verdict. No postverified ACK is invented by the testbench; ACK observation comes from the actual checker state machine.

The protocol bound derives from the existing28-edge write service and a second56-edge observation interval, with startup/alignment allowance. It is a simulation deadlock assertion, not a wall-time or build-resource limit. The benchmark is the same fixedfull16 backend:256 data macros and32 check macros. It is not a complete native source, numerical, finiteVM capacity or physical qualification.

Reproduce all cases:

```sh
python3 tools/qwen_vm_postverify_diagnostic.py --root . --out /tmp/qwen-postverify-diag-new
```

The runner requires a new directory, verifies provider pins, records copied source inventory and checks every expected outcome. Actual delayed reducer/other-unit traffic, hardware mutable-state protection and clock-domain source containment remain independent obligations.
