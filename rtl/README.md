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

`make verify` runs a self-checking Icarus simulation, Verilator lint, and a Yosys
technology-independent synthesis/check. The tiny test configuration is chosen so
the behavior is inspectable. Scaling results require target-node SRAM/ROM macros,
standard cells, timing constraints, and physical design.
