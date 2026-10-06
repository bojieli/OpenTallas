# Actual held W1 frame leaf: exact PASS

Default-off source: `rtl/rom/qwen_vm_active_frame_20261005/ot_qwen_rom_w1_frame_leaf.sv`.
Exact bench: `rtl/test/qwen_vm_active_frame_20261005/tb_qwen_rom_w1_frame_leaf.sv`.
Existing EPYC2 job `/srv/opentallas-scratch2/codex/boole-w1-frame-leaf-r1`
finished exit0. No restart or component replay.

Actual unchanged full16 checked VM service:64 reads,48 postverified write ACKs,
2048 old-read checks,768 real VM output readbacks. Held frame service took6434
cycles including validation, six coded read stages, seven coded pack stages,
and deliberate destination/pack stalls. Unsupported address phase and
cross-family writer alias both returned fallback; a double-bit response error
held outputs closed. Signed zero, NaN/Inf and subnormal payload bits preserved.
This is exact routing/service evidence, not a numerical engine/token result.
No physical closure or adoption is claimed; ENABLE defaults0.

Arendt integration uses only the immutable captured decoded frame:
`ren[2255:0]`, `raddr[2256*24]`, `wen[864:0]`, `waddr[865*24]`,
`wdata[865*32]` and existing `frame_ue`. Pulse `frame_start` when `frame_ready`.
Keep ALL borrowed frame pins unchanged through leaf outputs and bank debts.
`w1_valid` qualifies the literal PC20 first k0/j0/round0 pattern: only VX seats
208..2255 active at4096+(port%128)*32; ME768 scalars at
(5175+(seat/16)*8)*16+seat%16, all other writers inactive. Every other pattern
returns `fallback_v` before emitting a broadcast or pack; the enclosing adapter
runs its original ordered walker. No unconditional map for later phases.

The adapter owns every bank command, existing227-bit owner allocation/echo,
acceptance, rotation/fault checks, read-before-all-writes, XVM and native release.
Reserve `window_ready` before issuing a checked old read. Feed a validated
aligned bank response through `window_v/window_base/window_words`, then consume
`read_put_v/read_put_mask/read_put_data` into the existing encoded read seats.
The leaf holds those outputs until `read_put_ready`. Drain every old-read
broadcast before beginning writes. There is no cache or cross-edge lease.

Pulse `select_v/select_group` for a supported native ME group0..47 only when
`select_ready`. `pack_v/pack_word/pack_mask/pack_data` supplies that actual
masked512-bit writer; it holds until `pack_ready`. The adapter retains its real
postverified owner/address/mask ACK and release rules. After both payload pipes
and all enclosing bank debts drain, `frame_clear` resets the leaf's phase state.
It is not a bank reset, VM ACK, XVM advance or native admission.

Reproduce ONLY when a changed source warrants a run, on admitted remote hosts:

```
iverilog -g2012 -s tb_qwen_rom_w1_frame_leaf -o sim \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv \
 rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv \
 rtl/rom/qwen_vm_active_frame_20261005/ot_qwen_rom_w1_frame_leaf.sv \
 rtl/test/qwen_vm_active_frame_20261005/tb_qwen_rom_w1_frame_leaf.sv
vvp sim
```

The bench uses actual bank acceptance/readback/ACK, with `$fatal(1)` on mismatch.
Its source-derived cycle guard detects protocol deadlock, not a wall/resource
cap. EPYC2 admission8GiB, NUM_CORES16, NVMe temporary files, unlimited wall/AS/file/RAM.
No adapter/provider/clock-interface source edits, whole-array run or new model.
