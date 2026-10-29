# DIE-QC-34 / A0 (sub-agent DIE-QC-34-A0), 2026-10-29

Base: `claude/die-qc-33-a0rst-1029@58ecae91a94` (ICG_RRST relay RTL on Codex 68204ac61). Results only; no RTL change here.
Scratch root: `intel2:/srv/opentallas-scratch2/claude/die-qc34-a0`. AUTO-GEOM = origin/main `tools/autopilot` geom tools (byte-identical copy, main c0c65228405).

## 1. NK place, ICG=2 + ICG_RRST=1 + DIE-QC-33 graph homes (kit `qfd_tile_nk_a0c_a0nk14icg2rr1`)
- Kit = copy of the r2 probe kit; RTL `qfd_tile_nk_a0c.sv` from 58ecae91a94 + `rtl/lib/ot_rst_relay.sv`; config `VERILOG_TOP_PARAMS ... ICG 2 ICG_RRST 1`. Fresh synth (unit oth-ubuntu-1658071), place (unit oth-ubuntu-1737626, exit 0, GPL `-overflow 0.21` 1020 s, DPL legal, no DPL-0033).
- Homes: the 12,811 DIE-QC-33 graph homes (all names present in the new netlist, 0 missing) + 3 relay FFs: `sync_q[0]` (449,663) E column at the rst_n pin, `sync_q[1]` (320,663) and relay `rst_n` (225,690) in the y~663 H-street / x 193-321 opening, toward the hop/dr cluster. `GRAPH_HOMES placed 12814 cells FIRM`.
- AUTO-GEOM on 3_place.odb (`nk/auto_geom.json`, PNG `nk/auto_geom.png` VIEWED) CHECKED:

| item | r2 probe (raw rst_n) | **rr1 (ICG_RRST=1)** |
|---|---|---|
| r2r captures > 405 / max | 0 / 402.95 | **0 / 401.65** |
| relay_collapse | 0 | **0** |
| pin_reg_max (p90) | 139.83 (8.17) | **13.77 (8.17)** |
| rst_n direct flop loads (`nk/rstn_census.json`) | 73, max 358.45, 72 > 150 | **4** (sync_q[0] 13.77, native entry 141.66, sync_q[1] 144.94, relay async clear 251.77) |
| ICG enable legs (`nk/icg_reach.json`, 36 ICG / 104 legs) | max 395.55 | **max 395.60, 0 > 405** |
| remaining FAIL | aspect 2.528, partial_face 2, channel_h 0.8 / v 1.72 / col_v 1.91, clock_reach 748.53 | aspect 2.528, partial_face 2, channel_h 0.8 / v 1.725 / col_v 1.908, clock_reach 748.37 |

- The raw-rst_n class is resolved: rst_n now drives only the relay (2 sync + relay async clear) + the native reset sample; the one leg > 150 is the relay's async clear (251.77 um, < 405, inherent to the ot_rst_relay form; release is synchronous).
- Remaining FAILs are the same floorplan/CTS classes GEOM-59 accepted for the r2 probe (aspect / partial_face / channel = V1L parent plan items; clock_reach = CTS item). The K=0 enable paths (go/n_b_q -> node/fa2/fa3/ck ICG, ~395 um) are geometry-legal; their ~590 ps enable timing is UNCHECKED until CTS/STA.
