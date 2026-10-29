# DIE-KV-33-SD: kv3_sys_SD/_v1 reset taps + landing bands re-composed around the x6 SerDes PHY macro (2026-10-29)

Fix-only plan delta (KV FROZEN, COORD RULINGS [DIE-KV-32-PARK] (4)). No new gates. Existing tools only:
`apply_serdes_phys.py` (DIE-KV-32), `clock_landing_plan._storage_band` in ring_ff mode (DIE-HEAD-11 reserve, the call
`resize_undersized_bands` makes), `s81_head/head_reset_local_taps.cover_sites` (DIE-HEAD-5), `reset_tree.for_type`.

## Root cause (DIE-KV-32-KITS 12:33, CHECKED)
The event26 compose placed all 12 sys_SD reset `local_taps_um` and both landing bands inside the PHY abstract
(origin [17.28,54], 1866.24 x 972 of the 1900.8 x 1036.8 outline): it was composed without the macro.
`gen.py phys` fails closed: `type kv3_sys_SD: local reset tap [388.8, 596.16] is blocked`.

## Estimate (before build)
Free area with the event27 abstract (macro halo = reset_tree.CLEAR_UM 4.32, band outline margin 17.28):

| rim | width | usable for bands | usable for relay sites |
|---|---|---|---|
| W | 17.28 | 0 (margin) | x 4.32-8.64 |
| E | 17.28 | **0** (macro halo 1887.84 > margin 1883.52) | x 1887.84-1896.48 |
| N | 10.8 | 0 | ~2 um |
| S | 54 | y 17.28-49.68 (32.4 deep, 1866 long) | yes |

Bands (ring_ff reserve = (5 rw + 160) x 1.4166 x 1.05 um2): i_host_fdi W523 -> 4521.6; i_host_link_rst_n W1 -> 713.9.
Area is not the limit (S rim 60.5k um2); **reach** is (every band corner <= 402.84 um from its E-face bus pin):
* i_host_fdi pin (1898.66, 219.2): S-rim band [1708.56,21.6,1883.52,47.52], hop 390.1 -- fits, 12.7 um margin.
* i_host_link_rst_n pin (1898.66, 433.1): the S rim top (49.68) is >= 383 um below and the E rim has 0 band width ->
  min corner distance 416 > 402.84 -> **no legal band** (tool: "no macro-free clock landing storage band").

Reset: the 5 clock-tap terminals sit at y 21.6 (x 190-1711). The E-side sinks (macro rst_n at (1883.5, 433), E-face
fstart/fclk flops at y 219-869) are up to 1027 um from clk_t4 -> local taps are needed in the E channel; covering every
free point within 300 um of a local site (DIE-HEAD-5 rule) also needs W-rim sites (sinks there are possible since std-cell
rows exist in the 17.28-um supply strip).

Fallbacks for link_rst_n:
1. relay chain along the rim: adds an unpriced stage in front of a count-aligned landing ring (OWNER 12.16 CA safe by
   design; `_storage_band` refuses an unpriced relay) -> rejected.
2. bands outside the core in the parent: die plan change on a FROZEN die -> rejected.
3. **smaller abstract (chosen)**: trim the modeled abstract 17.28 um on its E (digital) side, 1866.24 -> 1848.96. Opens a
   12.96-um column x 1870.56-1883.52 between the macro halo and the band margin (E digital channel 34.56 um). Pins keep
   their y (x = new E edge), parent/die pins untouched, PG domain rect shrinks by 17.28 (still on the 8.64 grid), W
   supply strip unchanged. Area 1.7972 mm2 = 0.9907 x the half-x12 basis 1.8138 mm2 (modeled, no vendor GDS).
   A 34.56 trim gives the same bands (the tool picks the minimum-hop box), so 17.28 is the minimum.

## Result (CHECKED, intel1 /srv/opentallas-scratch2/claude/die-kv-33-1029/sd)
* views: results/kv_serdes_pg_event33 (gen_model.py, B=1848.96); LEF identical to event27 modulo B, lib area only.
* bands (both types): i_host_fdi [1872.72,17.28,1883.52,436.32] 10.8 x 419.0 = 4525.6 >= 4521.6, hop 245.0;
  i_host_link_rst_n [1874.88,438.48,1883.52,522.72] 8.64 x 84.24 = 727.8 >= 713.9, hop 115.6.
* local reset taps: 10 (was 12, all inside the macro), cover worst 298.1 um <= 300 (4.32 grid, bands excluded as
  sites); reset tree depth 5 (= event26 depth with the old taps), max hop 376.2 <= 405, 15 terminals, 69 relays.
* strict re-bind with the bind plan (event27f + new local taps): errors 0, unbound 0 (4:05, 8.7 GB); bound RTL diff =
  kv3_sys_SD_part.sv / kv3_sys_SD_v1_part.sv only (reset relay tree; start_tap 6 -> 2).
* kit-rtl + specialize_serdes_phy rc=0 (W522 -> _w522, W521 -> _w521, expected u_bound.u_core.u_phy.g_native.u_macro,
  0 added cycles/state); gen.py phys rc=0 both; kit_preflight PASS issues 0 both.
* render: sd33_floorplan.png / sd33_floorplan_E.png (viewed).

## Open (UNCHECKED)
* i_host_fdi band is a thin 10.8 x 419 column at the ring_ff reserve density: congestion risk (DIE-HEAD-12) until place/GRT.
* 2 reset tree wire relays are planned inside the i_host_fdi band (ff_put_near places them at the nearest free site).
* die clock islands: 151/152 (sys_SD) and 151/167 (sys_SD_v1) overlap the macro footprint -- the die clock plan (plan_straps die_islands_um) was
  composed without the PHY; die-level clock cells cannot sit on the macro. Die owner item, not changed here.
* kit_contract advisory macro_channels / clock_entry_clear / macro_pin_grid cannot resolve the physical_inst alias
  (advisory, non-binding).
* post-synth physical instance == u_bound.u_core.u_phy.g_native.u_macro: from the place runs' 1_2_yosys.v.
