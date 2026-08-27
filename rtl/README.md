# Technology-independent RTL

This directory is an executable contract for the architecture, not a taped-out
macro or a claim about density/timing.

- `via_mask_rom.sv` has no write path and implements interleaved expert storage
  with a wordline mask. A physical implementation replaces its behavioral memory
  with a via-programmed macro.
- `expert_mask_controller.sv` maps dynamic top-k expert IDs to static ROM
  wordlines, testing the central claim that MoE selection need not become dynamic
  packet routing.
- `rom_mac_tile.sv` performs signed parallel MAC/reduction.
- `static_timeslot_switch.sv` is a stateless compile-time-scheduled local switch.
- `opentallas_tile.sv` composes the mask, ROM read, and MAC into a two-stage
  pipeline.

The repository now contains both the original inspectable tile demo and a
requirement-traceable public-reference hierarchy.  The `ot_*` blocks implement
the digital contracts in `spec/MICROARCHITECTURE.md`: integrity, CDC buffering,
route/context validation, immutable-ROM repair translation, deterministic
integer-DV arithmetic, schedule epochs, credits, sessions, host commands, HBM
tags, stage-link retry, RAS/telemetry, and power/reset sequencing.  They are
deliberately parameterized so unit proofs can use tiny instances while the
architectural limits remain explicit.

`make verify` runs the legacy tile test, reference-unit tests, Verilator lint,
and a Yosys technology-independent synthesis/check.  The serious verification
campaign is driven by `tools/rtl_campaign.py` and records tool versions, source
hashes, seeds, logs, and evidence class under `results/rtl/`; it is a public
proxy and does not claim qualified ROM/HBM/PHY silicon behavior.

Scaling results require target-node SRAM/ROM macros, standard cells, timing
constraints, and physical design.  Behavioral macro initialization is allowed
only in DV; product-like builds must select an explicitly declared black-box
macro configuration.
