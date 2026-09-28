# Adopted V4.1x die physical preflight

Source baseline: `84585806` (2026-09-28). The reduced die token record
`results/rtl/hdc_v41x_die_top_smoke.json` is `pass`, and all 86 recorded RTL
source hashes still match this baseline. Its token is exact through the core
tile and HBM-backed attention KV prefetch. The package controller, router,
collective and external links are only elaborated in that record.

## Physical boundary today

`ot_chip_v41x_die` is the adopted connectivity top, but it cannot yet be used
as a whole-die route netlist. `tools/chip_assembly/floorplans.py:tile_profile`
and `tools/chip_assembly/assemble.py:die_spec` explicitly reject `v41_rom`:
their old tile floorplan and port lists predate `ot_hdc_core_v41x` and its
four-stack HBM interface. `docs/FULL_CHIP_IMPLEMENTATION.md` lists the same
port-level floorplan and memory replacement as prerequisites.

The tile's default behavioural arrays are large even though this is a reduced
vehicle. The values below follow the declarations in
`rtl/chip/ot_chip_v41x_tile.sv:192-202`, with default parameters; MiB is 2^20
bytes. They are logical capacities, not placed macro area.

| array | logical MiB | physical interface issue |
| --- | ---: | --- |
| `prog` | 3.000 | 1,536-bit synchronous instruction read |
| `wrom` | 64.000 | matrix and eight embedding reads, plus vector element reads |
| `hrom` | 6.000 | HE and vector reads |
| `hbank` | 16.000 | eight parallel HC banks |
| `mbank` | 32.000 | eight parallel ME banks with two-cycle read |
| `erom` | 16.500 | Engram read |
| `crom` | 0.250 | 32 stream reads plus auxiliary and vector reads |
| `qlist` | 0.0625 | QE fetch-list read |
| **ROM total** | **137.8125** | macro banking and exact read-port arbitration needed |
| `qwin` | 0.53125 | 17 QE HBM window banks |
| `vm` | 0.250 | core, package-controller and collective-DMA ports |

The die adds `u_kv.stg`, two 2,048-word × 512-bit prefetch slots (0.250 MiB),
plus its address tags and sector write queues. `ot_chip_v41x_hbm3e_phy` is a
behavioural model around `ot_hdc_v41x_idx_hbm` and `ot_hdc_hbm_model`, with
simulation array contents and protocol timing. Its physical replacement needs
the four PHY/controller macro views and a registered, timed interface; a route
of the behavioural model would not measure the HBM PHY.

The committed ASAP7 macro library does contain single-port ROM views, but not
drop-in views for the wide and multi-read tile arrays. In particular,
`ot_rom_16384x266_m16` has a TT minimum period of **1,024.5 ps**, already
above the adopted **920 ps** clock, while `ot_rom_8192x266_m8` has a TT minimum
period of **770.4 ps**. Any tiling into the latter still needs explicit
bank selection, ECC handling, an output register, and a cycle-exact replay of
the reduced token. These values are from
`physical/asap7_memory_macros/index.json`; they do not constitute a die timing
result. The floorplan budget's 2.714 GB per die is also much larger than the
reduced RTL tile's 137.8125 MiB, so placement of the reduced vehicle alone
cannot validate the adopted capacity/area envelope.

## First route boundary and closure sequence

The first independent physical route is the die's 32-pseudo-channel
`ot_chip_v41x_hbm_karb`, which arbitrates pooled index keys and attention KV
against one HBM stack. This is real die-side control RTL with no behavioural
memory array. Route at 920 ps with a 20% I/O delay allocation; record the
source commit, setup/hold, congestion, DRC and area in
`results/physical_abi3/asap7/chip/v41x_hbm_karb/physical.json`. It tests one
stack's arbitration only. It does not validate the four-stack HBM PHY,
cross-die wires, die clock or whole-chip power.

The route dependency order is:

1. Replace the tile's behavioural ROM, VM and QE window arrays with explicit
   banked macro adapters and prove the same reduced exact-token record with
   those adapters. Freeze the read latency and all shared-port arbitration.
2. Replace each simulation HBM stack with a hard PHY/controller abstract and
   timed K/W bus boundaries. Route the HBM arbiter-to-PHY boundary with actual
   pin positions, then the KV prefetch and pooled-key paths.
3. Build a new 48-tile physical partition from the adopted `ot_chip_v41x_die`
   port list. Place the vector/HC/select spine, banks, four HBM PHY strips and
   links against the 31.8 × 25.63 mm die envelope in
   `results/arch/v41_die_assembly.json`. Import Claude's completed block
   abstracts; register every long traversal charged in the latency DAG.
4. Run hierarchical placement, CTS, global and detailed route, extracted
   multi-corner timing and PDN/IR. Only then can the 1.087 GHz, 805.8 mm² and
   7,049 tok/s model inputs be promoted from conditional evidence.

The reduced die smoke is a correctness gate for step 1. The analytical
floorplan is a budget for step 3. Neither supplies a valid routed die today.
