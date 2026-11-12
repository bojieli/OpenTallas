# DIE-LAYOUT-HBM 11-12: option C for the q_b1xx seam-hop lanes, done at 0 cycles (d54 step, base d53b)

Base: d53b ad080c302a2b (hbm-cut-1111/compose/t33). Result: plan 33a1b3df8d76 (object-equal to
d53b + optc_delta_on_d53b.json.gz; the ladder_delta re-apply writes 367a3ff78348, same object, different serialization).

Finding: on d53b, seam_hop.py (main 9446d18f5d) reports 8 hops over 405 um on 6 lanes, 5 of them q_b1xx lanes:
L5072 (1262, 908), L5073 (1254, 1090), L7501 (726), L7000 (726), L5069 (701), plus L8101 (673, the q_su30 item).
The long legs are not seam legs. They run inside the source slot, from a station chain parked in the macro-free strip
(y > 1080) down to a face window that sits in the macro rows (y 36-238 / 413-828). path_respace.py cannot fix them:
it slides stations along the slot route, and there the binding stage is the S0 at the input face.

Form (resite.py): the slot stations move onto clear sites inside the macro field, i.e. the vertical macro channels
(4.7-22 um wide in q_b111, 10.7 um in q_b103) and the pocket under q_b102's middle column (x 235-465, y < 155).
Wires cross the cores on M6/M7, above the M5 core ceilings.
- S0 stays at the input face (regs_um[0] unchanged).
- Every hop is <= 360 um (0.9 x 405 = 364 is the reach WARN), measured from the worst input-window bit and to the worst output-window bit.
- Clock keepouts and a 2-um core halo are excluded.
- The minimum station count found is <= the current count in all 12 slots, so 0 cycles: no stations, latency or latency-table change.

Slots (type: slot k, min needed, max hop):

| type | slots |
|---|---|
| q_b111__physical_v1 | L5072x2 8 (3) 358; L5073x2 6 (5) 360; L7501x3 7 (5) 359; L5069x1 5 (5) 359 |
| q_b102__physical_v1 | L5072x3 6 (6) 359; L5073x3 6 (3) 359 |
| q_b103__physical_v1 | L5072x1 8 (5) 356; L5073x1 6 (3) 359; L7501x2 4 (3) 356; L5069x2 6 (3) 329 |
| q_b103 | L7000x2 4 (3) 344 |
| q_b111 | L7000x3 7 (5) 360 |

Lane max hop (check.lane_pin_hops): L5072 1372 -> 359, L5073 1254 -> 359, L7501 774 -> 359, L7000 774 -> 359, L5069 703 -> 359.

Gates:
- G0 (src_hbm_main_fe0002fac6) vs d53b: ERROR 548 -> 536, 0 new, 12 cleared (hops 5, stations 7). WARN 1833 -> 1828, 0 new, 5 reach cleared.
- seam_hop over 405: 8 -> 1 (L8101 only).
- Strict two-pass bind (private copy): BIND_OK, 92 partitions, 420 crossings, 0 errors, stale 0, pad_flops 945214 (receipt.txt).

Changed types (re-kit): q_b102__physical_v1, q_b103, q_b103__physical_v1, q_b111, q_b111__physical_v1.
Risk: up to 1615-bit stations sit in 5-22-um channels between SRAMs; the station flops spread along the channel.
route_supply / place density is proven by the type builds (KW-FIX-45 wave), not by this paper form.
Renders: after_*.png (type frame, hard cores grey, re-sited chains coloured).
