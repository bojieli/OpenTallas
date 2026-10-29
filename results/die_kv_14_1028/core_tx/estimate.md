# DIE-KV-14a core_tx plan delta: estimate before build (METHODOLOGY 12.14b), 2026-10-28 17:2x PDT

Ruling: KV-KITS-14 ASK, COORD 16:33 DEFAULT YES (GEOM-46 (1)-(3)). Generator: `physical/die_plan/qwen_kvsys/cores/core_tx_plan.py`.
Inputs: plan `results/die_kv_13_1028/event_gz/plan.json.gz` (slot kv3_hub_Wi.host__qkd_hr_core_tx), old pins
`qkd_hr_core_tx_pins_r26q9.json` (sha eb72ca64, the pin file the GEOM-46 kit used; copied here from
intel1 wt/die-kv-6 results/die_kv_7_1028/input/cores), and partners from `core_conns.json`.
Number labels: CHECKED-own means my script or arithmetic reproduced the number. Nothing here has an independent NUMBER-CHECK.

## Old slot (GEOM-46 FAIL; kit kv-kits-9-1028/coretx, 3_place)
276.48 x 267.84 um. Pins W 1047 (M4) / S 2539 (M5, 9.3/um) / N 40 / E 0, plus the ck[0] centre entry at (138.264, 133.92).
Logic is 9030.5 um2 in 66,176 cells, 13,045 of them flops (CHECKED-own from geom.tsv, excluding tap/fill/decap). Fill is .122.
r2r is 515.9 um, with 805 captures above 405. Clock reach is 262.8 um. Render viewed: the logic forms an L on the W and S faces.

## Outline
- **150 x 150 does not fit.** The usable perimeter is 4 x (150 - 2 x 2.16) = 583 um. At 6/um that holds 3,496 pins, which is fewer than the 3,626 data pins.
- **155.52 is the smallest 8.64-grid side.** It holds exactly 6.0/um with zero slack, so the 10-um windows would go above 6.
- **Chosen: 164.16 x 164.16** (19 x 8.64). The budget is 5.9/um on the usable 159.84 um per face, which gives 943 pins per face and 3% spare. The core area is 155.52^2 = 24,187 um2, so **fill is .373** (CHECKED-own arithmetic).
- **Origin stays at (725.76, 855.36), the SW corner of the old slot.** The tool searched every 8.64-grid position inside the old slot, and this one had the least partner wire. **The new outline is inside the old slot.** No neighbour, bus, FT station or the die floorplan changes; FT stations keep at least 10.8 um from hard cores, and those distances only grow. About 47,100 um2 goes back to hub_Wi.

## Pins (3,627, same names; ck[0] stays interior M5)
- **Faces:** N 882 / E 858 / S 943 / W 943. The mean is 5.52 / 5.37 / 5.90 / 5.90 per um. The worst 10-um window is 5.6 / 5.4 / 6.0 / 6.0 per um, and the tool fails closed above 6.0 (CHECKED-own).
- **Tracks:** pins sit on the die symmetric tracks, 0.024 + k x 0.048, with a minimum gap of 3 tracks (0.144 um). That is about 1 pin per 3.5 M4/M5 tracks, or 28 % of the pin-layer tracks; the old S face used 45 %.
- **How pins get a face:** each partner group goes to the face with the least mean Manhattan distance to its partner slot, under the cap. The tool uses a greedy pass, then cancels negative cycles until it reaches the exact transportation optimum. Final faces: prompt -> W, rx -> E, peer -> N, guard -> S.
- **Status pins (rule 2):** groups with no core-only partner include the 40 old N-face pins, the resets and the unmapped cmd_hc/seen pins. They go to the face that holds most of their module's partner pins, iterated to a fixed point. u_ctrl -> S, so **37 u_ctrl status pins are on S**, next to u_ctrl's 832 S pins. u_tx's 2 stay on N (u_tx logic face N), and u_axi__rst_n goes to E.

## Clock entry (rule 3)
- The logic centroid is taken as the pin-register centroid (80.16, 80.70); every pin is registered at its face. The **entry ck[0] is at (80.136, 79.92)**, snapped to an M5 track and the 2.16 grid.
- The **clock reach bound** from the entry to the farthest core-area corner is **159.6 um, against a target of <=220** (old 262.8) (CHECKED-own arithmetic).
- The **r2r bound** is the Manhattan diameter of the core area, 2 x 155.52 = **311 um, below 405**. So **0 captures can exceed 405, by construction** (CHECKED-own arithmetic; the placed run confirms it).

## Parent impact (UNCHECKED rough estimate: Manhattan from each pin to its partner's slot rectangle)
| partner | pins | face change | mean um old -> new |
|---|---|---|---|
| core_prompt | 1394 | S->W 927 | 495 -> 498 |
| core_rx | 1076 | S->E 856 | 338 -> 342 |
| core_peer | 815 | W->N 815 | 35 -> 118 |
| core_guard | 169 | W->S 169 | 774 -> 748 |
| cdc_ch+guard | 65 | S->N 65 | 552 -> 540 |
| u_ctrl logic-face (status + unmapped) | 84 | N->S 37, W->S 47 | partition glue, n/a |

- **Total partner wire:** 1,257 mm -> 1,328 mm (**+70.6 mm, +5.6 %**). Most of it comes from peer, +84 um x 815 pins. Every link stays registered at both ends, and the worst mean of 748 um is the guard link, which was 774 um before (the old slot had the same class).
- **Tracks (UNCHECKED):** the 927 W-face prompt pins drop south through the 35-um peer|core_tx gap. The vertical M3/M5/M7/M9 supply there is about 2,700 tracks, so demand is about 35 %. The E-face rx pins use the freed 112-um strip.
- **Parent clock:** the hub_Wi tap `host__qkd_hr_core_tx.ck[0]` moves from (864.024, 989.28) to (805.896, 935.28), a 112 um Manhattan shift. The partition clock leaf must be re-planned at the new tap in the KV PLAN-DELTA event. The insertion budget stays 250 TT / 202.5 FF.
- **Unchanged:** pin names and count, so the bind, RTL, LEC and the hr_face_ports proof are not affected.

## Kit dry-run (CHECKED-own, results in my scratch only, no runs launched)
I ran gen_core_kit_kv.py on the applied plan with the GEOM-46 kit arguments: `--hr-face-ports kv-kits-9-1028/coretx/fp/qkd_hr_core_tx`, `--reset-ports u_ctrl__por_n`, `--util 0.6`, `--sigmax M5`. It returned rc 0.
It wrote kit `qkd_hr_core_tx__164.16x164.16` (hash 9bd3064399b82584) with 3627 pins, 0 added pins and 4 resets. DIE_AREA is 164.16^2 and ck[0] is at (80.136, 79.92) at clock-port size.
The kit is in intel2:/srv/opentallas-scratch2/claude/die-kv-14a-1028/kits.
