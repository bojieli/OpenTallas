# FABLE-DIE-S81 2026-11-16 08:3x PST: S81 whole-die verdict on B6gF2s2 (v2 tree), and the die event

Owner of S81 die-level PD quality. MEASURED = my runs or files I read. INFERENCE is marked.
Run: epyc9 `/srv/opentallas-scratch2/claude/fable-die-s81/s81/F2s2` (plan B6gF2s2 a623deec2d38, tools v2 tree
src_s81_pin_eb1e73448bd0, chain `run_base.sh`: r98 spt feed + region DME clock kit -> combo die GRT TT/FF 50 it -> tap
arrivals -> die_sta_related; 21 min). Render: intel2 `~/fable-die-s81/die_F2s2.png` (floorplan / clock arrival / GRT
density). Census: `s81/F2s2/dieana.json` (script `dieana.py`). Earlier kit read for comparison: B6gsh (epyc7 die-clk-s81-b6).

## 0. Verdict

The die routes (GRT 0 overflow) and related-pair setup passes (+390 intra, +312 seam). The die is NOT closed on four
structures: the clock cells sit unreserved inside types and on landing bands, the feed is 11.7 ns deep with the K
table still from the B6gsh kit, seam skew is 310 ps against a 40 ps seam contract, and reset fan-out crosses whole col
types in one cycle.

## 1. Numbers (MEASURED, F2s2)

| item | value |
|---|---|
| die | 32.24 x 25.98 mm, 398 partitions / 395 types, 0 overlaps, partition area 798.1 of 837.7 mm2 |
| die GRT TT/FF | overflow 0 / 0 / 0; usage M4 2.6 %, M5 4.1 %, M6 4.4 %, M7 2.2 %, M8 0.9 %, M9 0.8 %; 18.7 GB |
| die STA TT setup | intra +390.05 (0 of 1,333,766 pairs), plain seam +312.48 (0 of 2,040,620) |
| related-pair skew | intra 253.6, seam 310.3 (FF 244.1 / 290.2) |
| hold | NOT measured on real views (0 signed views fed). Kit contract: intra need 208.4, seam need 290.2 against 40 |
| landed pairs | region-to-region damage 3,639 ps TT (3,264 FF) against 416.5: single-cycle FAIL, as expected; covered only by count-aligned rings with a K table from THIS clock |
| clock tree | 93,530 cells, 21,687 taps, 7.67 m wire, 22..188 stages; tap arrival 1,314..11,682 ps TT; late-early up to 1,359 ps |
| clock legs | 559 over 260 um, 21 over 405 um, max 995 um (kit runs without a reach cap) |
| clock cells vs types | 93,522 inside partitions, 0 in hard cores, 54 in the 2.16 um core halo; 2,586 inside landing band rects (223 types; svc_hi t6 attnh_i0 50, svc_lo_w t1 hbmrd_i0 31); about 4,003 on ft station columns (my 6 um test); 0 of 395 types carry clock.reserved_sites_um |
| glue tap spread per partition | median 64 ps; 24 partitions over 100; 1 over 180: s_7N_x13 slice_station__t51 253.6 |
| region spread | median 140; hard_phy_hbm 748, std_bg_70_0 (bk_sel) 405, std_bg_80_0 360, std_bg_64_0 348 |
| channels | 98 ports (57,930 bits) cross a die-route gap; 56 ports (34,292 bits) cross 414.7..527.0 um, over the 405 reach, with no station (svc band gaps grown by +77.76 and +51.84) |
| lanes | 873 lanes, 14,007 cycles; longest idx svc_14 -> bk_sel 25.3 mm / 17 hops / 102 cycles, xtier seqhost <-> bk_sel 23.4 mm / 108; x_E3_out 16.98 mm against 14.12 for x_W3_out (2.9 mm detour, 1,104 bits) |

Visual: the feed radiates from the centre root (16.1, 12.2 mm); arrival grows smoothly to 11.6 ns in the four corners, so
neighbours stay close but every corner region carries about 10 ns of unshared path against the centre. GRT density is
concentrated in the slice_station rings (x 9-10.5 and 22-23 mm, y 11.5, 19 and 24.5 mm); no bin is near capacity.

## 2. Bad structures and root causes

1. Clock cells over types, unreserved. Every type kit is built without the 93,530 die cells; 2,586 land in ring bands
   that the ring-ff form now fills. Root cause: the kit's site rule knows cores and PHY only, and no type reserves.
2. Feed depth. 188 inverter stages and 11.7 ns to the corners. Count-aligned rings absorb the mean, not the variation:
   the CA strap margin was 105.5 against 100 on the B6gsh kit. The K table of record is from B6gsh; taps moved
   (22,895 -> 21,687), so it is stale.
3. Seam and intra skew 310 / 254 ps. Setup has room; hold does not: a 40 ps seam contract needs 290.
4. 21 clock legs over 405 um (max 995).
5. Channel hops 414..527 um on 34,292 bits without a station.
6. Reset fan-out (col): one flop to 103-155 copies across a 1,443 x 1,227 um type in one cycle (-100..-151 routed on
   r2); on 48 r0 types the driver regex missed, so one flop drives 138-145 loads unreplicated.
7. Start tree: 48 long start hops (435..5,812 um) have no measured delay; 1 stage unplaced (S81-START-CAP).

## 3. Die event (delta rows to DIE-S81-92)

| row set | state |
|---|---|
| R1 col reset-copy chains, 216 types (reset_replicate copy_depth 3, per-instance regions, cf_rs regex) | DELIVERED for F2s3: epyc10 fable-die-s81/rst/rows_col_reset_F2s3.json 7ef9db83e4f5 + overlay; tool claude/fable-die-s81-1116 @f222855b650. Checked on real bound RTL of all 216 types, 0 errors; schema 0 errors on F2s3 preview. Routed timing NOT measured |
| R2 clock site reservation, 395 types | DRAFT only: epyc9 fable-die-s81/ev/rows_clksite_F2s2.json (clksite_reserve.py --tree, 54,417 rects). Not for adoption: it would reserve the 2,586 band sites. Needs R3 first |
| R3 clock kit of record: type keep-outs (bands, ft stations, tap rows) in the site rule, reach cap 405 on legs, then freeze | NOT done |
| R4 K table + strap ties + common latency from the R3 kit (count_align_plan --strap-window, capped start tree) | NOT done; ties only, no type re-key unless a depth changes |
| R5 stations in the 56 channel hops over 405 um (+1 cycle each lane, pre-approved) | NOT done; die STA seam setup on them is positive today, so advisory |
| R6 seam hold: per-port windows from this kit (die_sta_related --kit-window-out, s81/F2s2/kitwin.json) | file exists; rows not cut |

## 4. Not checked

Hold on signed views; PG (psm kit not run); the landed K margins on this kit; start-hop delays; whether die_trial
type keep-outs already cover bands when enabled (test_die_trial_type_keepouts exists, yaml does not set it).
