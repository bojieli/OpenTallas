# DS HBM-accelerator attention, 1.2 GHz route handoff to Codex (Claude hbm-fmax attn, 2026-10-05)

The RTL is final. Codex takes the SS/FF route loops from here. Change only recipe knobs (utilization, density,
cores, repair margins). If a path is structural, post it to codex_notes with the worst path. Claude owns the RTL.

## Design (default-off successors; pinned files byte-identical)
- `rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv`: the engine. It is the REPL=2 controller of `ot_hdc_v41x_attn.sv` with
  FPL/FML/NBANKP added, plus five options:
  - `NARROW`: block counters.
  - `MFAN`: per-head merge control copies (`merge_x`), +1 cycle on p.v results.
  - `TRX`: decoded, per-element transposer selects (`tr_x`) and per-tile staging-buffer selects.
  - `F12`/`FPLX`: f12 FP32 adds.
  - `TILE_S`.
- `rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv`: the tile, organised as H/HG head groups (`hgrp_s`). Per group it has
  R0, D1 and skew lines. Per head it has load R0 copies.
  - The dequantiser is split across D1 (`deq_a`/`deq_b`).
  - The product is split 8x4+8x4 across the stage-1 register (`bmul_s`).
  - The adds are f12 LAT4 (`qaddf`).
  - Lockstep-exact against `ot_hdc_v41x_attn_tile_l` every cycle (`lockstep/`).
- `rtl/hdc/v41x/ot_hdc_v41x_kreg.sv`: a keep_hierarchy register, so yosys cannot merge duplicated copies.
- `rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s_phys.sv`: the hardening wrappers.
  - `ot_attn_hgrp_m4` is the hardened element: 4 heads, TD32, NBANK5, PW2, FPL4 F12, FML6.
  - `ot_attn_tile_m` is 4 of those elements.
- `rtl/chip/physical/ot_v41_attn_eng_s_ctl_phys.sv`: the controller vehicle. It is the D=64 full-schedule vehicle
  of `w11_attn_eng_ctl`: tile, staging and FP-add are registered stubs; the controller, transposers and merge
  rings are real.

## Routes (recipe: tools/run_abi3_physical.py ... --clock-period-ns 0.833 --clock-uncertainty-ns 0.06
## --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --stages synth,pnr --hold-margin-ns 0.01
## --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --purpose signoff_target; then tools/w18/corner_sta.py)
1. Leaf `ot_attn_hgrp_m4`.
   - Sources: `tile_s_phys`, `kreg`, `tile_s`, `tile_lat`, `tile`, `fastfp`, `fp32_add_lat`, `prefix`, `fp32_f12`.
   - Options: `--io-delay-fraction 0.2 --false-path-io --core-utilization 35 --place-density 0.55`.
   - `--false-path-io` is justified because every input of the element enters an R0 register directly. The one
     exception is the static gid, which is registered before use. Every output is a register.
   - In flight: `ot-agidock128:~/hbm-fmax-attn/routes/hgrp4b_u35` (route.sh there).
   - CTS estimates of the previous RTL:
     - r_ld_w -> ab -156 ps. Fixed by the per-head R0 copies.
     - f12 adder chain y -> u_k1 -154 ps.
     - bmul stage 1 -121 ps.
   - If the f12 LAT4 chain still misses after route, the fallback is LAT5x in the chains: `F12=1 FPL=5`, +2
     cycles per tile pass. Report that to Claude first.
2. Controller vehicle `ot_v41_attn_eng_s_ctl_phys`.
   - Parameters: `BREG=1 REPL=2 NSTAGE=2 D=64 ILV=1 PWORDS=2 FPL=4 FML=6 F12=1 FPLX=5 NARROW=1 MFAN=1 TRX=1`.
   - Options: `--orfs-var SYNTH_HIERARCHICAL=1 --io-delay-fraction 0.2 --false-path-io`. The vehicle ports are
     all boundary registers (BREG) or data-load shifters.
   - Sources: the vehicle, `kreg`, `attn_s`, `attn`.
   - In flight: `ot-epyc1tb:/srv/opentallas-scratch/claude/hbm-fmax-attn/routes/ctl_f12t`.
3. Tile parent `ot_attn_tile_m`. Run it after leaf 1 closes. Export the abstract with
   `python3 tools/hbm_fmax_attn_abstract.py --orfs-dir <leaf>/work/orfs --name ot_attn_hgrp_m4 --out <macro dir in
   source tree>`, then route with `--macro-view ot_attn_hgrp_m4=<dir> --macro-place-halo 5 5`, with IO timed (no
   false path), and run corner_sta with `--macro <dir>`.

## Not closed here (engine-level floorplan items)
- The 64-tile broadcast and distribution tree at D=512.
- The lane trees across 16 tiles per lane.
- The staging SRAM macro placement.

These need the engine floorplan. Their wire-stage cycles are not in the measured tile cycles.
