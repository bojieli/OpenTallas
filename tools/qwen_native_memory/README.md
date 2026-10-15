# Native Qwen memory providers

`ot_qwen_native_memory_cluster` composes the actual static NOX VM (real SRAM macros), eight TP8 constant-ROM groups (48 mapped mask-ROM macros), and eight TP8 constant-buffer groups (24 mapped SRAM macros). The parent contains wiring only. It exposes all 481 VM clocks and the sixteen constant-ROM/buffer clocks, and preserves actual SU descriptor, row, ME result, attention write, Q-export and X-replica-write interfaces. It adds no storage or fabricated responses.

The compiler must provide the implemented fixed schedule. `row_available`, constant residency, commit masks and fault outputs are observations/assertions; they are not permission to defer production issue. The parent does not gate issue with them.

The legacy LV6 `RomVmAdapter` / `VmReceiver` remains a functional model. Its 3,072 arbitrary X reads and arbitrary 64-lane SU reads at one-edge latency cannot be connected honestly to this memory hierarchy. Native integration must use distributed X delivery and the real SU descriptor ports, with SU latency 15 and row latency 13. Program/weight ROMs, DVM X, native compute and the complete digital split link are separate required providers. This parent and its component tests do not establish a native layer/token or physical timing qualification.

## TP8 layout correction

The historical CROM and buffer defaults decode TP4 addresses. Actual TP8 emitted programs use:

| Region | TP8 value |
|---|---:|
| QK0 | 4096 |
| POST0 | 4736 |
| QSCALE | 8832 |
| ROPE0 | 8833 |
| OSC0 | 533121 |
| DSC0 | 537217 |
| END | 541313 |
| QK rows/layer | 10 |
| Narrow rows/layer | 138 |
| Final-normalization first row | 4968 |

`ot_qfd_crom`, `ot_qfd_crom_gs`, `ot_qfd_crom_gr` and `ot_qfd_crom_lbuf` accept an explicit `TP` parameter; the default remains TP4. The stage-row multiplication now actually uses the configured stride instead of an unconditional TP4 shift-add. The parameter-free `ot_qfd_su_cbuf_g_tp8` is the TP8 physical successor. TP8 ROM physical kits must instantiate `ot_qfd_crom_gr` with `TP=8`. Historical TP4 physical views do not prove these successors closed.

## Verification

Run all build/simulation/lint commands through `ot-run` on a fleet host after staging the source tree.

```bash
bash tools/qwen_native_memory/run_crom.sh /absolute/fresh/positive
bash tools/qwen_native_memory/run_crom.sh /absolute/fresh/wrong_tp4 1
bash tools/qwen_native_memory/run_cbuf.sh /absolute/fresh/buffer_positive
bash tools/qwen_native_memory/run_cbuf.sh /absolute/fresh/buffer_wrong_tp4 1
bash tools/qwen_native_memory/lint_cluster.sh /absolute/fresh/elaboration
```

The component benches use 64 real lanes, all 48 ROM macro functional models, and every decoder layer plus head. The buffer bench additionally instantiates 24 real SRAM macros and the relay-stage ROM (`gr`, eight edges). They check unchanged outputs through edge four and exact results at edge five. Buffer fills use fixed reserved cycle counts, with residency checked at the assigned cycle, never a ready-driven wait. Test fixture via masks are declared ROM contents; the golden functions only compare results and never drive DUT internal values. These deterministic address/data fixtures prove banking, stored format, stage identity and fixed local latency; they are not released-checkpoint numerical or throughput receipts. The wrong-TP4 controls reproduce the historical hardware layout and must fail numerically.
