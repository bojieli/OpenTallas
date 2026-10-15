# Static HBM host configuration ingress component

This is an opt-in replacement component for the retired dynamic CP's **configuration and launch role**. It is not a new runtime record interpreter. The frontend accepts finite AXI-lite writes at the variable-latency host boundary, assembles programme words, and emits registered configuration frames to real local programme stores. A launch is a single registered event; no per-cycle execution credits or ready negotiation exist.

`tools.uarch_model.hbm_host_static_ingress_model()` sizes this component before implementation. The nominal H-DIE slot is 432 x 432 micrometres. The ingress itself contains no SRAM. Existing local programme stores own their actual macro capacity, and the existing host landing FIFO owns its two 256 x 256 SRAMs. Neither is hidden inside the ingress area.

## Register ABI

All writes use full four-byte strobes. AW and W may arrive together, address first, or data first; one holding register per direction joins them. Responses remain stable until accepted. A protocol fault is sticky until cold reset and returns SLVERR for the rejected write.

| Address | Write value | Meaning |
|---|---|---|
| F20 | bits 7:0 target, 19:8 row, 31:20 zero | Select a target and starting 256-bit row. Partial frames cannot change target. TARGET_MASK must explicitly include the actual target. Default is only target 48. |
| F24 | next 32-bit piece | Eight little-endian pieces produce one registered target8/address12/data256 frame. Row increments; row4095 terminates the selection instead of wrapping. |
| F28 | base12 in 11:0, exclusive limit13 in24:12, upper7 zero | Stage a nonempty range, maximum4096 rows. Each real target enforces its own smaller capacity. |
| F2c | loops16, upper16 zero | Send the target descriptor. Zero loops and partial words are refused. |
| F30 | exactly1 | Launch only when actual local block-ready aggregate is true, no active/faulted engine exists, no word is partial, and the fixed transport guard has expired. |

Reading F30 returns bit0 frontend fault, bit1 block-ready, bit2 active, bit3 target fault, bit4 partial word, bit5 transport guard. Other reads return FFFFFFFF. Writing other addresses faults; there is no passthrough into the retired CP.

Configuration-frame and descriptor output guards are four cycles. Launch guard is seven cycles, covering the existing target collar and native programme's start/active pipeline. Ready outputs and incoming status have dedicated pin flops; an accepted launch locks host write admission until the real active interval completes. This admission lock never gates execution. All sources and destinations must use the same defined synchronous clock family; CDC is not implied by these ports.

## Genuine local readiness

The existing `ot_static_program_target` configured flag validates descriptor bounds, but does not prove that every programme row was loaded. `ot_hbm_program_block_ready` supplies this missing control mechanism beside a real target: it observes that target's actual programme write port, retains a finite loaded-row bitmap, and scans every row of the proposed descriptor range before asserting readiness. Missing rows fault before launch. Later configuration invalidates readiness until a new descriptor is checked. A two-edge commit guard accounts for the native programme's input capture and actual macro write.

PCW10 uses1024 control bits and scans up to1024 rows during configuration. These bits are control flops, not replacement payload storage. The payload remains in the actual32KiB 1024 x256 SRAM. Per-target validators belong beside their local programme memories; do not broadcast every bitmap from the host corner. Parent logic must aggregate the actual participating targets' validated readiness and faults. Validation latency precedes launch and adds no cycles to the running programme.

## Evidence and remaining integration

The bench writes all1024 rows through this frontend, the actual target48 collar, and `ot_vms_calendar_static` using the repository's native1024x256 SRAM model. Two loops emit2048 exact, consecutive calendar beats with checked ordinals. It checks all three independent AW/W arrival orders, held response stability, new requests asserted during response clear, and seven protocol failures including launch before installation, partial-frame launch, missing-row readiness, bad strobes, unbound target, unselected data and empty range. The data-bit, premature-launch and loaded-row-bypass mutants must fail. External testbench values are host input stimulus and expected calendar outputs; no expected-answer memory replaces DUT storage.

Run from the repository root:

```sh
bash rtl/hbm_accel/host_static_20261015/run.sh /tmp/host-static-proof physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
```

**Open:** actual host UCIe/packet/landing composition; all participating target IDs and local validation/ready reduction; adapters for each heterogeneous programme layout; SU's16-bit bank +7-bit row interface (not representable by the existing12-bit row ABI); die-assigned pins/clock roots; CTS, routed native launch/capture timing and die-level integration; production-model programme installation frequency and end-to-end token cost. The full-shape proof qualifies this component mechanism only, not a complete host_cp replacement or a physically closed HBM die. Existing macros and closed masters remain unchanged.

Current native compact programme join (2026-10-15)

The source-pinned native composition in `hfd_host_static_native_qdq_program.sv` connects the actual digital UCIe/retry endpoint, two-macro landing buffer, packet controller with true BRESP, ingress, downstream-write readiness and COMPACT1 target48 programme. It passed1024 installed records,4096 exact gapless commands per launch, two launches with no SRAM rewrite, first command13edges after public launch, and six protocol/error negatives. The measured installation took1,017,144 controller edges before launch (847.62us at1200MHz). This is a component initialization measurement; installation frequency and whole-token cost remain open.

`evidence/native_qdq_receipt.json` pins the positive and rejecting controls. `native_qdq_source_contract.json` lists source dependencies and the two new native-programme monitor outputs (11bits). The ingress has one input landing and one output payload stage. Physical kits/views are excluded here: routed native launch/capture, local readiness placement, every heterogeneous target, actual parent reset/clock binding and fullhost qualification remain required. The existing generic2048-beat proof and this compact4096-command proof have different programme formats and scope.
