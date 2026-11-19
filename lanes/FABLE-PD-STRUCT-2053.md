# FABLE-PD-STRUCT 2053 — structural review of S81 D8g (c4b) and KV D25a

Read-only review, in parallel with the binds. All numbers below are computed from the plan JSON, the core pin files and the bound RTL of the gate tree unless marked INFERRED. No kit was run by this lane; nothing here is a timing result.

Inputs
- S81: epyc8 `/srv/opentallas-scratch2/claude/s81-geom-opus-d8g/plan_d8g_c4b.json` (380ab1ebad64, per COORD update; c4 fec83c0d5ecb was read first). Diff c4 -> c4b: 12 p2 types (hard_cores, internal_stations), 42 p3..p6 types (relay_sites); nothing else. Pins `gate_geom/src/.../inputs/core_pins`, RTL `gate_geom/out/rtl`.
- KV: epyc8 `kv-d23-compose8/build_d25.py`, base D24c plan `kw45/src_kv_pin_eb1e73448bd0_hg9_2862ed5a_tb3e667d_d24c` (plan_c.json), staged tree `kw45/src_kv_pin_eb1e73448bd0_hg10_5801ea96_td6a5a52_d25a` (plan 5801ea964612, asbuilt af17e5ec6215), rows `d25in/`.
- Layer pitches used for capacity: M2/M3 0.036, M4/M5 0.048, M6/M7 0.064, M8 0.080 um (M5 pin pitch and track_offset in the pin files; M8 from the kit obstruction stripes).

## 1. S81 D8g c4b

### What c4b fixed (verified)
- u_cf MX at y 605.88: the 13 M4 pins (lk[0..11], rst) are back on track (phase 0; on c4 they were 0.024 um = half a track off). Origin is on a row (2244 x 0.27). M5 x phase unchanged. Row count 256 is even, so rail parity is kept. Gap to c3_6 unchanged (5.16 um in x, no overlap).
- frame_int_o0 hops 399.5 / 394.1 / 404.0 / 376.5 / 376.5 um (c4: 445.6 first hop). ret_o0 343.7 / 273.6. xo_i0 315.2 / 145.9. All under 405; the third frame hop has 1.0 um left.
- Side benefit of the MX flip that was not claimed: cf.xa -> t0.xai goes from 433..472 um (all 283 bits over 405) to 355..370, and cf.xb -> t0.xbi from 423..475 to 370..396. x2 (536 bits) now faces t0__payload directly.
- Relay sites: none of the 34,944 sites in 42 types lies in a hard core or a 5 um halo.

### Ranked risks
| # | Risk | Measured | Fix | Owner |
|---|---|---|---|---|
| S1 | xa_1_0 / xb_1_0 also drive u_bs0 (dsfd_qbank_S i_x0 / i_x1). The new site moves the relay away from it. | relay -> bs0 pins: xa 927..972 um, xb 918..963 um, all 549 bits, all 42 types (c4: 866..923). bs1 366..411 (16 bits/type over 405 on xa). bs3 already has its own relays (xa_2_bs3_0 / xb_2_bs3_0); bs0 has none. Whether bs0.i_x* is single-cycle is NOT checked (INFERRED from the bs3 precedent). | Read TT at GRT on the p6 DB through u_y_xa_1_0 -> u_bs0/i_x0 first. If timed: a bs0 branch relay of the bs3 form (xa_1_bs0_0 / xb_1_bs0_0), sited near (560, 300); that is a bind row with a cycle on the bs0 branch. | S81-GEOM-OPUS (read), S81-DIE-R3 (row) |
| S2 | t0 -> relay hop is over reach on every bit, and c4b made xb worse. | t0.xa -> xa_1_0: 428..508 um (med 468). t0.xb -> xb_1_0: 484..564 (med 522; c4 434..514). relay -> t1: xa 343..423 (36 bits/type over), xb 287..367. Sum is about 852 um, so no single-stage site gives both hops <= 405; balance is about 426 / 426. xb is now 96 um off balance toward the sink. | 0-cycle: put xb in the lower block (y 469..481) and xa above, or move the xb block east/south toward t0 (free area x 955..1085, y 521..596 gives about 436 / 415; clk_t25 at (980.5, 596.2) is the only plan object there). If the t0 hop is still negative at TT: D 2 on the t0 -> t1 xa/xb link. | S81-GEOM-OPUS; cycle row S81-DIE-R3 |
| S3 | xa_2_0 also drives u_bs2. | relay -> bs2.i_x0 468..484 um, all 283 bits, all 42 types. t1 -> relay 160..238 and relay -> t2 198..227 have slack. | 0-cycle re-site in the same e2/e3 gap: centre y 760 -> about 663. Then bs2 about 371..387, t2 about 295..324, t1 about 65..140. | S81-GEOM-OPUS |
| S4 | p2 clock taps were not moved with the flip (c4 and c4b change only hard_cores, internal_stations, ft_slots). | cf clock pins: cr_s is now at (1402.5, 675.0), 93.3 um from the nearest added tap clk_t22 (1416.96, 596.16); in R0 it was 23 um. cr at (1272.2, 605.9) is 154.6 um from clk_t22. That clk_t22 serves cf is INFERRED from position. | Mirror clk_t22 to about y 684 or confirm the tap table on the first p2 kit (tap -> cr / cr_s wire and post-hook skew). | S81-GEOM-OPUS |
| S5 | ft0 22x51 still loads the station cross-section heavily. | 44x26: 44 nets per 0.54 um = 81.5 nets/um against 76 raw tracks/um on M2+M4+M6+M8, i.e. over 100 % inside each station; this fits the failed kit (M8 43,074 + M6 29,732 of 77,186). 22x51: 40.7 nets/um = 54 % raw, about 87 % of M4+M6+M8 with the 15 % M8 obstruction stripes. Stations do not hit a core (tops <= 1131.84, band 147 um) or another station; block 5 (x 46..92, y 1237.7..1264.7) lies in the frame_int_o0 N-face bank zone (x 6..260, 1,167 bits), less than before (was x 23..117). Worst face -> block-1 hop about 376 um (was about 399). | If the p2 GRT still overflows on M6/M8 at the stations: 11 cols x 101 rows (54.5 um tall, y about 1210..1265, still 78 um above the cores) = 20.4 nets/um, 43 % of M4+M6+M8. Move block 5 east of x 260 or below y 1251 if the N face bank reports "cannot fit". | S81-GEOM-OPUS |
| S6 | New xa/xb pocket is 43.2 um wide (bn1 edge 872.64 to c3_3 edge 915.84). | Cells end at x 911.79: 4.05 um to c3_3, whose W face carries 43 M4 pins (addr 12, ce, clk, rd_out 29). 549 flops at 93 % row use in every 4th row; area use 23 %. bn1 e_r0/e_r1 pins (S edge) are no longer under the blocks. | None needed before a kit; if DRT shows pin-access errors on c3_3 W pins, shift both blocks 3 um west (s3 halo ends at x 834.4). | S81-GEOM-OPUS |
| S7 | Old capacity question (20.5 um street, 25.4 um gap). | Street: M2 569 + M4 427 raw H tracks for 549 nets; M6+ runs over the ROM (obs M5), so it was not the limit; c4b left it anyway. Gap e2/e3: block 18.1 um wide in 25.4 (margins 4.2 / 3.2), V tracks M3 705 + M5 529 for 283 in + 283 out; e2.u_e / e3.u_w have no pins on the facing edges (pins N/S). | OK. | - |

### What fails next in p2..p6 (not in D8g)
- cf.cc -> t0.cci 600 um direct (15 bits, p2; was 669) and t0.so -> cf.st 605 (relay_depth lists the st sink); pre-existing, improved by the flip, still over reach.
- p3..p6 u_y_cc -> u_s0.lc (867 ps unbuffered, from the 1840 review) still has no site row.
- DRT probe on the old p2 GRT DB ended DRT-0352 (guides congested), so p2 needs a clean GRT before any route read.

### S81 stop list
- Do not take a p3..p6 kit as proof of L2 until S1 (bs0) and S2 (t0 hop) are read at TT on GRT; the 5_global_route.rpt is not a TT read.
- Do not widen L2 or L9 to other families from this event.
- Do not read 4_cts_final.rpt on these kits (pre-pad).
- G0 2 errors = control; bind for gate_geom / gate_ctl was still running at the time of this read, 0 error lines so far.

## 2. KV D25a

### Ranked risks
| # | Risk | Measured | Fix | Owner |
|---|---|---|---|---|
| K1 | Section F (F2, writer-start stages 6/7 reset tap) is NOT in D25a. | build_d25.py has no F code. Its rows copy `d25in/FABLE-FIX-KV-HG-rows-d24.json` is the 02:13Z file (10,609 B, sections A..E); the hub file with F is 12,831 B (19:29 PST). F2 is also a rule in the writer-start emitter, i.e. a tools change, not a plan row. So hgi_v4 / v5 / v6 / v7 keep wns -571 / -595 / -802 / -890 (2 ends per type, 2.1 mm reset hop). | Emitter rule on main (stages 6, 7 read the tap of stage 5), then D25b on that tools sha. | FABLE-FIX-KV-HG (rule), KV-D23-COMPOSE (D25b) |
| K2 | kt stations: D25 drops the 16 sited DEMAND rows per type on all 19 hg/hgi types and relies on relay_mid line siting (1/3, 2/3 of source -> sink), which no kit has placed. | kv3_hgi_v1: the straight-line 1/3 or 2/3 point is inside a head eighth core on 12 of 16 rows. The dropped plan sites had hops 150..360 um (e7 -> e0: 360 x 3, total 1,080 um); only 4 rows (e4, e6 of each head, centre line x 185.76 / 807.84) had sites inside a core. The k3 proof (+0.43 TT after repair) used the plan sites, not line siting. If relay_mid snaps into the nearest channel the e7 legs can pass 405. This class is F1 = 95 % of the hgi_v4..v7 tns. | Carry the dropped regs_um as FIRM relay_sites for the kst cells (u_head<h>_g_t_<t>_u_kst0/1), with the 4 in-core rows moved to the channel x 341.28 / 963.36 as the e5 / e7 rows already are. Or prove the line siting on one placed hgi_v1 view before volume. | KV-KT-E0 (sites), KV-D23-COMPOSE (compose) |
| K3 | W1 moves the core, band rect and tap, but one copy of the band stays. | D24c plan: `clock/landing_contract/collector_local_sources[4]/band/rect_um` = [17.28, 760.32, 61.344, 1077.84]; build_d25.py edits only `bands.i_ectl_Q_N_tN.rect_um`, the hard core, the tap and the station. No reset entry names the core (reset tap_um and the spine pin at y 760.32 are unrelated coincidences). | Shift that rect by +336.96 too, or derive it from bands. Check the first strict bind / GEN for a collector mismatch. | KV-D23-COMPOSE |
| K4 | W1 geometry. | New box 17.28..61.34 x 1097.28..1414.8: no core, tap, station, band or ft site inside; core centre 1256 vs face centre 1260. 121 um of its E (q) side faces the head2_e6 W wall across a 16.42 um gap: about 595 of 1,560 q wires leave through that gap (M3 455 + M5 341 raw tracks). | None before the proof kit; read overflow at x 61..78, y 1097..1218 first. | FABLE-FIX-KV-HG |
| K5 | W3 polyline shares the middle channel with ft2. | ft2 (1,056 bits) stations at (348.46, 601.70) and (354.94, 941.09); polyline ends (340, 618) and (340, 950.4) are 16..25 um from them. k4 measured a NEW 12,000 overflow at x 0..400, y 400..600 (t2 fan-out + ft2 station nets) with W2+W3; west band 28,699 -> still 15,441 at y 1000..1200 on k5, which W1 targets. | Move the polyline to x about 312 (channel is 294..388) and end the tail at y about 660, off ft2 station 1 and cl_ft2_i. This is what fails next on hgi_v1 after W1. | FABLE-FIX-KV-HG |
| K6 | W5 pad flops are a 2-hop lane over reach. | Hops 580 + 670 um (owner's numbers) against 405; k5 post-CTS TT -16.95 on 1 end before repair, +0.46 after, on placement RC. Site (45, 560) is free (39.8 um from head2_e2). | Expect a small negative at GRT; fallback is a second pad stage (+1 cycle on the 32-bit eN lane). | FABLE-FIX-KV-HG |
| K7 | W2 with-W1 site is untested. | (133.0, 1270.08) is free (51.8 um above head2_e6, 71.7 um from the moved core). k4 / k5 used the other form (100, 950.4), without W1. | Proof kit only. | FABLE-FIX-KV-HG |
| K8 | W1 covers kv3_hgi_v1 only (2 types). | Landing core y origin on the others: hgi_v8 924.48 (centre 1083, 177 um below the face centre 1260); hgi 1166.4 but at x 172.8; v2 / v5 / v7 1123.2, v4 1149.12, v3 / v6 1166.4 (within 65 um). The station (133, 1164.095) is the same on all 11 types. | hgi_v8: same row, +172.8 um (20 x 8.64), after the hgi_v1 proof. Check on each type whether the station lies on a head core, as it did on hgi_v1. | FABLE-FIX-KV-HG |
| K9 | The event depends on 5 unsigned cores. | kv3_head_eighth_e0 (kst 2) was in GRT; qkd_ectlk_q0..q3 HXK 15 are a new kit lineage (q0 kit-local RTL edits and q3 core_sink_grow not reproduced; HXK 13 synth sanity not finished). | No hg / hgi kit of D25 counts until the 5 cores sign and the token run at D_QK + 2 passes. | KV-KT-E0 |

### What fails next on hg / hgi / pc
- hgi_v4..v7: F2 (K1) sets the wns until the emitter rule lands; then nothing named at CTS if K2 holds.
- hgi_v1: west band at y 1000..1200 should clear with W1; next is x 0..400, y 400..600 (K5) and the 16.4 um gap (K4).
- hg (8 types): section B rows are not in D25: ectl q0 eN -> u_bout_o_ectl_Q_N_eN (-837, 2,540 um, 32 ends), tN (-499), ring dsel -> u_bin (-550, 68 ends), astk ep -> er (-705, 256 ends).
- pc: every pc number is HG6-era and stale; one pc kit on the live tree is needed before any row.
- hub_C at 709k cells is above the largest closed run (517k).

### KV stop list
- Do not present D25a as carrying F2; do not launch hgi_v4..v7 volume to prove it.
- Do not count any D25 hg / hgi kit before the e0 and ectlk cores sign.
- Do not copy W2 / W3 to other hgi types without W5 and a proof.
- Do not write pc rows from HG6-era kits.
