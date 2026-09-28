# Qwen O4 per-group scale-ingress physical probe

The adopted Qwen O4 core has 6,144 groups of 16 INT8 MAC lanes per die. A
weight cycle presents 786,432 code bits; a post-K-split scale read presents
one 256-bit BF16 scale word per requesting group. The emitted real-checkpoint
layer-0 resource manifest at `6b4f4550` reports 1,472 active scale-group
reads versus 1,179,648 unmasked requests per die. The core's group read mask
is required to make that access pattern physical; a full all-group scale read
on every result would be a different design.

This probe places **one** 16-lane post-tree scale cluster. Both arms have the
same 16 FP32 row-scale multipliers, 256-bit source-capture register, 512-bit
completed-sum register, 240 × 240 µm outline, 0.92 ns clock, 184 ps external
input delay and 184 ps output delay. The ROM arm includes one analytical
ASAP7 `ot_rom_8192x266_m8` macro, of which 256 output bits are useful. The
HBM arm starts at an already-registered local 256-bit scale word. Therefore
downstream logic area and timing have exactly the same scope, while the ROM
macro area is reported separately. The HBM controller, HBM PHY, stack,
prefetch storage and the wider iso-area comparator are outside this local
cut; the HBM input-arrival constraint is a stated test condition, not a
measurement of them. These two arms cannot by themselves establish a ROM/HBM
token-rate or energy ratio.

The probe connects a `scale_group_re` activity signal to the ROM chip enable
and the common source capture. The scale read schedule, bit-exact token,
full-bank address translation and all 6,144 clusters remain with the E2E RTL
owner. The ROM compiler LEF/Liberty are analytical views: their bitcell was
laid out, while periphery dimensions and current were assumed. OpenROAD
results using them are a physical feasibility diagnostic, not silicon
signoff. This direct flow has no PDN, DFT, antenna repair or formal
equivalence.

The source-pinned direct cut reached placement, clock-tree synthesis and
global routing in both arms. At the 0.92 ns target, the ROM source-to-capture
path is **−314.67 ps** with placement parasitics; the staged HBM boundary is
**+425.47 ps** under its stated 184 ps input arrival. Those figures isolate
the scale source. The overall cut is further blocked by the group-read enable:
global-route setup is **−1590.34 ps** for ROM and **−982.41 ps** for HBM.
Reset recovery is also violated under this input-delay constraint. Thus even the HBM arm does not
meet the clock; the two source slacks are not comparable token rates. The
first physical repair is a registered, locally fanned-out enable; the ROM
output needs a direct capture register or an additional stage before the
held scale register. Both require an exact latency check in the real core;
reset needs a real distribution and deassertion constraint.
Detailed route is still running separately; `physical.json` records only the
reached stages, with no routed timing or DRC claim.

An exploratory rebuffer from the placed ROM database inserted 977 buffers
over 577 nets and removed the enable from the worst reported path. It left
157 cells illegally placed, and its remaining core setup path was −928.65 ps.
The rebuffered result is recorded as an **invalid placement diagnostic** in
`rom/repair_probe.log`; it cannot be used as a timing or area result. A valid
repair needs buffering before placement, plus a short register-to-register
arithmetic path.

The selected full-shape layer-0 image has 50,616 addressable 32-byte scale
words per die, but only 1,488 words in its active address range and 1,472
active group reads. The one-bank 8,192-word probe does not implement that
full address map. A bank-local remap or several banks must be specified and
tested before scale storage area can be claimed at the die level.

## Reproduction

The remote source bundle contains this directory, the `ot_hdc_fmul` RTL and
its dependencies, and the macro views. Mount it at `/work` in the pinned
`openroad/orfs:latest` image (image SHA recorded in the physical result), then
run the two arms with the same command:

```bash
python3 physical/qwen_o4_scale_ingress/run_physical.py --arm rom
python3 physical/qwen_o4_scale_ingress/run_physical.py --arm hbm
```

`--stage synth`, `--stage place` and `--stage route` replay individual stages.
The campaign records source hashes, tool output, exact reached stages and
timing/DRC limitations separately for each arm.
