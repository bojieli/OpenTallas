KV-PLAN-DELTA-7 (2026-10-27) -- root cause of the hub_Wi / hgi_WN_7(v8) M6 FT-coupon overflow.
Runs: intel2:/srv/opentallas-scratch2/claude/kv-plan-d7-1027/<variant>/grt/route.log (+route.seg). Inputs = KV-PLAN-DELTA-6 coupons
(ft_station_probe --segmented, 50 it, signal max M7, layer adjustment 0.75 = die ft_track_frac 0.25). Table: coupons.tsv.

ROOT CAUSE (after the ft5/ft6 and ft4 removal): NOT a capacity shortfall and NOT at the W face.
 - The overflow sits on the FT bundle runs between stations in the horizontal channels (hub_Wi: bottom band y 0-120 and
   top band y 1560-1676; v8: bottom band y 0-170 (ft26, 1057 b) and y 1200-1280 (ft27)), see ovf_*_fastroute.png (VIEWED).
 - In the 1207 (hub_Wi) / 1232 (v8) gcells with M6 overflow, M4 (the other horizontal FT layer) is EMPTY: median M4 use 0 of
   56 tracks, 54,019 / 63,325 spare M4 track-gcells there, layer-summed (2D) H overflow only 163 / 818. FastRoute's 2D
   solution fits; its 3D layer assignment stacks whole bundles on M6 (cap 42/gcell, 21 over cores) and leaves M4 idle.
   Own capacity model (gcell 10.8, pitch, 0.25 keep, core OBS, transition-layer halving above M5 OBS) reproduces the log:
   M6 25,859 vs 25,179 (max 55 = 55) and 26,050 vs 25,082 (max 70 = 70).
 - Contributing: FT station abstract pins are stacked M4+M5 squares (no layer preference) while face pins alternate M4/M6.
 - Proof by 3D router: CUGR on the SAME inputs gives M6 99 / 128 (vs 25,179 / 25,082).
 - Genuine shortfall exists only BEFORE the move: base_Wi 2D (layer-summed) overflow H 20,786 + V 19,314, base_v8 2,784 + 2,275.
   After the move: 79 / 496. So the approved 3,280-bit move IS sufficient on capacity; the 25k residual is a router artefact.
   (Corrects KV-PLAN-DELTA-6 "W-face hotspot": the W/E face columns hold only the small 2D residual, 62 / 319.)
 - Residual true 2D overflow after the move: face windows of FT buses packed at 10.5-12.5 b/um (ft4 257 b/22 um, ft26
   1057 b/84 um, ft9/ft17/ft23 ~550 b/48 um) vs 9.1 b/um derated M4+M6; and 17-um slit stations between hub_Wi core rows.

STRUCTURAL FIX (proposed, tool-level, needs COORD ruling -- shared die_trial/ft_station_probe abstract writer):
 F1 planned FT layer split: each FT bit gets ONE pin layer end-to-end (even bit M4, odd bit M6 on E/W runs; M5/M7 on N/S),
    the same at faces and station pins. Coupon (parity_pins.py): M6 25,179 -> 2,975 (hub_Wi), 25,082 -> 2,164 (v8).
 F2 FT face windows <= 8 b/um on BOTH abutting sides (same fix that closed hgi_v5/v7), station keep-out >= 1 gcell from
    core OBS where the channel allows. Coupon what-ifs: totals 4,515 -> 4,005 (hub_Wi), 2,650 -> 2,847 (v8): small.
 F3 the remaining ~2-4k is FastRoute 3D assignment again (2D residual 129 / 602). Options: die GRT gate with layer-split
    honoured per layer (F1 in the die abstract), or CUGR for FT coupons (CUGR on F1+F2 inputs: 619+12 / 3,427+42) -- neither is 0.
NOT ACHIEVED: GRT overflow 0 on either tile. Outline growth NOT justified by these data (after the move, M4+M6 2D fits).
