# TileIO actual compare-cone diagnosis and finite successor

The existing TileIO source already selects CV=1, A_INPUT_STAGES=1, MERGE_HOP=1 and CMP_STAGES=3 in rtl/ot_s81hd_tile_p.sv:673. Its native compare registers are an operand hop, registered16-bit half comparisons plus row comparison, then the combined comparison. These cycles already belong to the selected ABI. No stage or source change is proposed.

The retained final report's actual worst path is `u_core.c_rb[31]$_DFF_P_`→`u_core.kh_gt$_DFF_P_`, slack−1089.30ps. Launch clock arrival441.70ps, data arrival2350.85ps and required1261.55ps give1909.15ps from launch clock pin to capture D (the displayed rounded per-row increments sum1909.14ps). The delay is wire721.35ps, buffers/inverters598.90ps, non-buffer combinational cells498.64ps and launchCQ90.25ps. Wire plus buffer burden is69.2% of the observed data delay. The source key transform canonicalizes−0, maps signed FP32 bit patterns to the declared order key and then compares each16-bit half. Its sign/zero normalization shares operand fanout across halves; it must not be replaced by an unproved unsigned comparison or split into independent16-bit source keys.

I personally VIEWED `final_worst_path.webp`. It shows a path looping around the upper macro despite nearby endpoints. Exact native DEF poses explain it:

| Actual cell | Native lower-leftµm |
|---|---|
| launch c_rb[31], DFFHQNx2 | 375.624,704.160 |
| capture kh_gt, DFFHQNx1 | 261.846,704.430 |
| XOR _48038_ | 503.280,943.110 |
| OAI _48039_ | 299.484,711.720 |
| AO _48040_ | 304.506,1031.670 |
| NOR _48211_ | 44.766,723.870 |
| OA _48213_ | 212.706,867.510 |

The mapped logical closure of all five existing compare captures (kh_gt, kh_eq, kl_gt, kl_eq, rl_q) is568combinational cells and98distinct operand/row boundary FFs. The **actual final** closure has726combinational cells:271buffers/inverters and455other cells, with the same98FF boundaries and no unresolved fanin nets. Every one of the98boundaryFFs is fixed on y704.160, x253.260..414.612; all five captureFFs are also fixed nearby. Yet503/726comb cells lie outside the native horizontal street y699.852..734.412 between the A macros' tops and B macro's bottom. The actual comb-origin extent is x5.670..702.216/y377.730..1031.940. These are actual poses, not estimated wirelengths. `physical_poses.json` joins every physical cone object to the final DEF with zero missing names. The original mapped cone intentionally has58objects absent after physical optimization; it is not aliased to the current physical graph.

This is a concrete combinational placement and repeater problem. It does not justify changing the clock/parent contract or adding pipeline cycles. Simply relocating one path gate while preserving the598.90ps old buffer chain is insufficient: even zero wire delay leaves about1187.79ps of original CQ/buffer/logic delay against the observed819.85ps launch-to-required window. A successful placement must avoid recreating the long-route repeater burden. No promised timing improvement follows from these arithmetic bounds.

The smallest useful physical successor is one **private PLACE-only compare-cone affinity event** on the retained same-source pre-CTS placement, using the exact original mapped closure as a membership seed and explicitly joining its actual checkpoint objects before mutation. Keep the98operand/rowFFs, five captureFFs, all other FFs, macros, TAPs, ports, reset policy, graph, primitive masters, status/DNT, clock topology and PG frozen. Restrict only the existing compare combinational cells to a reviewed legal street region near those registers. First dump native full-body/TAP/PG occupancy to size that region; the34.56um street is an actual gap, not proof of enough remaining placement capacity. Do not cram cells into a guessed rectangle, move closed macros or reuse old route buffers as the logical membership list.

Render and personally LOOK at the proposed affinity region against all native bodies and registered data flow before a placement launch. After separately authorized native placement/legal/PG/contact checks, save a new honest checkpoint and render/LOOK again. Preserve both the old failure and the source/register ABI. Fresh CTS, full CLOCK+SIGNAL routing and TT/FF qualification are separate scoped events; no old guides/RC, component clock proof, parent hold receipt or ETM expansion credit transfers. An RTL rewrite is unnecessary for this first discriminating placement event. If the local cone remains logic-bound after native placement, then any proposed exact key/comparator rewrite needs its own smallest bit-exact miter and mutant before adoption.

No native job, source or physical change was performed for this diagnosis. Existing route/finish files were read only. The foreign v1pb/v1route producer remains active in its existing signoff phase (PID1901672 observed); its current output must be collected by its owner rather than overwritten. The archived signoff had TT−1089.30/1023, FF−45.57/482, slew1790/984, cap37 and18unconstrained; a current signoff writer exists, so these are retained values until its terminal result is collected. Existing UNEXPANDED_CHILD_ETM and real-parent holds remain separate blockers.
