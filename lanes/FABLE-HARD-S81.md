# FABLE-HARD-S81 2026-11-14: root causes of the S81 types that lanes could not close

Scope: slice_station t29 / t28 / t36 / t27 / t47, ot_s81sl_leaf t73 / t9 / t75 / t34 / t39, col_h9_r0 p1 / p2 / p6, svc hi (rs t1-t6, pvso). Read-and-diagnose from kit logs, congestion reports, plan files and generator source; nothing shared was changed, nothing killed. This adds to FABLE-WAVE-REVIEW (same day) only what is specific to these types.

Status of each statement: MEASURED = read from a log, report, plan or source file; HYPOTHESIS = fits the numbers, not yet proven.

## 0. Two findings that change today's fleet fix 4 (allow-congestion + M9 defaults)

Both MEASURED in `tools/die_plan/gen_phys.py` of the wave source (B3x2b/src) and in kits generated after the change.

1. `OT_CONS_MAX_LAYER=M9` in S81 `die_gen_env` (kit_wave.json, written 18:30 PST) does nothing.
   - Without `OT_CONS_KIT=1` the variable is not read at all (gen_phys.py:316-326).
   - With `OT_CONS_KIT=1` it is clamped to the kit top: "the cap only lowers" (gen_phys.py:396-400). Leaf t44 attempt 11, generated 18:45 with `OT_CONS_MAX_LAYER=M9`: `cons_kit.json` says requested M9, kit_top M8; config.mk has `MAX_ROUTING_LAYER = M8`.
   - The kit top comes from the plan (`P.type_top_layer`, gen_phys.py:4836), M8 with the M8 grant. No wave kit has M9 today. The only M9 builds are private copies with config.mk edited by hand (slice_station t30 form c).
2. M9 inside a partition has no grant. METHODOLOGY 12.1a: partitions route on M7 or lower; M8 only through the leftover grant (`m8_grant.py`, die PG tracks obstructed); M9 carries the die PG and the clock tree.
   - The signed t30 form c holds M9 wire (GRT demand 14,571 of 2.59 M, 0.56 %) on tracks nobody checked against the die M9 grid.
   - M9 was barely used there, so M9 is probably not what closed t30; density 0.35 is the other difference to form b. HYPOTHESIS.
   - Fix: an M9 grant with the same structure as the M8 grant (plan `layer_budget`, `m9_grant` in gen: obstruct die PG and clock tracks, grant the rest), then the plan top becomes M9 for the families that need it (section 2). Until then the M9 default is a private-form setting, not a wave default.
3. Kits generated before 18:30 have neither default. Slice_station t42 attempt 14 (gen 18:25): no allow-congestion, M8. Every attempt older than that repeats the old GRT-0116 stop.

## 1. slice_station

### t29: there is no design failure; three infrastructure ends and one lane typo (MEASURED)

| attempt | host | what happened |
|---|---|---|
| 13 | epyc7 | GRT clean: Total overflow 0 at 3.67 % use; hold -32.13 ps on 1,204 endpoints repaired to 0 in three chunks (847 + 210 + 134 buffers). Died after the repair on `global_route.tcl 194: couldn't read write_ref_sdc.tcl` (container without that script). |
| 14 | epyc10 | Same clean GRT (2:40 h). Detail route killed at 1:55 h, iteration 0 at 50 %, peak 32.6 GB. |
| 16, run 1 | intel1 | New plan kit (die 1442.88 x 1278.72). Congestion fell 9 gcells left at extra iteration 20, then 2 h of hold repair, killed at 4:49 h, 29.3 GB (make Error 241). |
| 16, run 2 | intel1 | Killed after 2 min 22 s at 17 GB (Error 241). |
| forms A, B | epyc7 | Died on `OT_MAX_BUFFER_PERCENT=400` (STA-0576, the lane's own edit). |

- "RSZ-0060 buffer-cap crash" is a label error. The hold guard repairs in chunks with a buffer cap per chunk and catches RSZ-0060 on purpose (`OT_HOLD_GUARD_GRT: chunk buffer caps reached (RSZ-0060 caught per chunk); continuing`). The wave classifier reports the first `[ERROR` line of the log. Four S81 types carried this false label today (t29, serdes t13, iqf t1, slice_station t40).
- Why t29 is exposed: it is the largest slice type. Eleven feed-through buses cross the full 1,443 um, 7,447 pins; max-wire 50 um adds 97,397 repeaters (241,271 to 338,668 cells), 205,034 nets. GRT with hold repair takes 1:42 to 4:49 h at 25-29 GB, detail route needs more than 32.6 GB. Every hour in the queue-saturated hosts is an hour exposed to the memory killer.
- Dead ends: forms A and B (routability off, sparse utilisation 0.05, buffer percent) address nothing that was measured, and both restart from synthesis. Outline growth: 2 % utilisation.
- Fix (no design change):
  1. Route memory 64 GB for this item (`place_mem_gb_by_item` / route equivalent in kit_wave.json), and resume attempt 16 from its `4_cts.odb`, never from synthesis.
  2. `OT_PREGRT_FF_HOLD=1` for t29 (config of attempt 16 has none): hold repair on placement RC took 795 s for 9,619 cells on leaf t29, against 1.5-2.5 h inside GRT here. This halves the GRT window.
  3. Classifier: ignore RSZ-0060 when an `OT_HOLD_GUARD_GRT chunk` line follows; book Error 241 as INFRA (fleet fix 3).
- Proof: attempt 16 resumed with 64 GB reaches `5_2_route` and ends detail route; expected GRT overflow 0 (measured twice on the old plan, 9 gcells at iteration 20 on the new).

### t28, t36, t27: one cause, the landing window is too dense at the pin face (MEASURED)

- All overflow lies within 20 um of the landing face: t28 531 of 531 gcells (N), t36 553 of 553 (N), t27 595 of 595 (S). Totals 1,093 / 958 / 1,367 at 2.8-6.9 % routing use; each gcell is 1 track over a capacity of 26-30.
- t28: the overflow sits only under `u_cland_ft2_i` (x 620-740): 605 bits in a 110-um window, 5.5 bits/um, 3,474 ring flops + 12,147 ring logic cells. The two 513-bit buses of the same kit in 122.88-um windows (4.2 bits/um) have zero overflow. Half of the gcells (262) lie 15-18 um below the face: the line between the flop strip (0-11.88 um) and the band (from 17.28 um) that every ring net crosses, plus the two window ends (177 and 175 gcells).
- t36: overflow only under three abutted 513-bit windows (x 232-565, 4.6-4.7 bits/um, 1.6-um gaps); the two abutted windows at x 908-1128 are clean. Dense windows with no lateral gap leave the ring control nets no way in.
- Class rule from these numbers: a landing window above about 4.5 bits/um of face, or three abutted windows, overflows; 4.2 bits/um with gaps routes.
- The structural fix is already built: S81-LEAF-PLAN event B4L4 (`--densify --per-bit 10`, 143 bands in 44 slice_station types; the type list holds t27, t28, t36, t47). Its strict bind was admitted on epyc7 at 18:34. For t28 ft2_i that means a band of about 55 um instead of 28.
- Dead ends: any further wave attempt or private form of t27 / t28 / t36 on the old bands. Form b of t30 (density 0.4, allow-congestion) passed GRT and failed DRT-0255 on a ring net (`u_cland_ft1_i/u_ring...wcc[5]`): allow-congestion moves the same knot into detail route.
- Proof: first kit of t28 on B4L4: GRT Total overflow 0 without allow-congestion, no gcell within 20 um of the face in the report.
- Hold (t36: -72 to -114 ps before): `OT_PREGRT_FF_HOLD=1`, guard 45, is in the t28 and t36 kits now. Closed, nothing to add.

### t47 (MEASURED)

- Last build (11-07, epyc2): routed, DRC 0, TT setup +86.09 ps, FF hold -4.09 ps on 1 endpoint. No attempt since 11-07 on the current plan; OWNERS.tsv still shows the 11-07 sign-off.
- Not a hard type: it needs one build on B4L4 (it is in the event) with pre-GRT hold on.

## 2. ot_s81sl_leaf t34, t9, t73, t75 (one class), t39

### Root cause: no vertical layer over the ve / vs / vn cores, and feed-through corridors that run through them (MEASURED)

- The ve cores are 172.8 x 345.6 um and sit 34.6-43.3 um off the face, inside the straight N-S (or E-W) corridors of the feed-through slots. Kits route to M8. Over a core the report shows horizontal capacity 5-6 per gcell (M8 only) and vertical capacity 0.
- "34.6 um off the face" is the symptom. A wire that enters over the core on M8 cannot change track or turn until it leaves the core.
- t34 (attempt 14, intel1, `congestion-15.rpt`): ve_m at x 34.6-207.4, y 77.8-423.4 blocks the corridors of ft3, ft0, ft1, ft4, ft2 (1,763 bits). H overflow 22,211, of which 20,536 (92 %) over ve_m. V overflow 15,762: 9,774 in the 34.6-um W slot, 4,986 over ve_m. Second round (`congestion-10`): V 23,284. It does not converge. Plan stations ft0 (25.92, 138.24) and ft3 (25.92, 293.76) sit inside the W slot.
- t9 (intel1, the 125,297 failure): H over ve_m 38,474 of 49,230. ft8 (1,104 bits, S window x 247-485) lands under ve_m (x 337-510); its landing band is a 24-um column (x 306.7-330.5, 5,760 flops) closed in by vs and vsw. t73 has the same pair and band.
- t75 (attempt 5, epyc9, about 9 h in GRT): H 93,413, V 85,484 in the capped report; V over ve_m 47,663. Two 1,104-bit buses cross ve_m and ve_s.
- t39: no design failure on record. Attempt 8 was a stale LEC state (infra), 11-13 was DRT-0073 on a ROM pin (core view). Attempt 9 entered GRT at 16:56; first report V 19,334 / H 1,442, almost none over cores: the N-face landing rings (section 1 class, B4L4) and one channel at x 950-1050. Wait for the result.

### Dead ends

- t34 attempt 14, t75 attempt 5, and the fresh M8 kits of t9 (attempt 2) and t73 (attempt 6): zero vertical capacity over the cores cannot be iterated away.
- t34 form fb (density 0.15): the overflow is over cores and in the slot, not in cell area.
- Moving the ve pair to 86.4 um off the face, and outline growth: four S81-LEAF-PLAN events tried; every legal spot breaks the 412 / 864-um link limits.
- Expecting `OT_CONS_MAX_LAYER=M9` to help: it is clamped to M8 (section 0).

### Fix

1. Plan (S81-LEAF-PLAN, next event B4L5), replacing the core-move search:
   - No station and no landing band in a slot narrower than 86.4 um between a face and an M7-opaque core. t34: stations ft0 / ft3 leave x < 34.6 and go north of ve_m (`core_place --ft-resite`). t9 / t73: the ft8 column band moves to the core-free part of the window, about x 253-330, y 17-120 (7,900 um2 against 5,640).
   - Rule R-LEAF-2b reads "no station or band in the slot", not "move the core".
2. Layer (DIE-S81-92 with gen owner): M9 grant for the leaf family, per section 0. One 172.8-um core gives about 2,160 raw M9 tracks. Whether the die M9 grid leaves enough over leaf partitions is not measured.
3. Order: fix 1 is plan-only and needs no new layer; try it first. Fix 2 is needed only if the proof below leaves overflow.
- Proof: t34 form fa (same placement, config edited to M9) entered GRT at 18:35 on epyc7 `/srv/opentallas-scratch2/claude/tl-leaft34/fa`. Bin its congestion report by core footprint: V over ve_m should fall from 7.2 k to about 0. If the W slot stays above about 5 k, the station move is required as well. For t75 resume the attempt 5 placement at GRT the same way.

## 3. col_h9_r0 p1, p2, p6

### CONS forms fail OT_CLAND: the band has 4 % spare and the CONS kit asks for three strip rows (MEASURED)

- Kit epyc9 `tl-colh9r0p1/fb_f9acce4c`: band ft0_i 21.6 x 240 um = 5,184 um2 for 6,147 ring flops, fill spread 1.041.
- Every CONS kit exports `OT_CLAND_STRIP_ROWS = 3`. `landing_placement.tcl` line 1106 stretches the columns to `min(0.4 * rows, spread)` = 1.041, exactly the band limit, and the last flops find no site. The plain form places the same band at spread 1.0.
- It is not utilisation, M8 or max-wire. Any CONS form of p1 / p3 / p5 fails until the band grows.
- Fix: DIE-S81-92 event B3x2d (`ev/B3x2bd.json`, band fill 1.041 to 0.52) is the structural fix. Tool: cap line 1106 at 0.9 x spread.
- Proof: place-only run of fb_f9acce4c on B3x2bd, about 10 minutes.

### GRT at iteration 21-30 for hours is not congestion (MEASURED)

- Kit epyc10 `tl-colh9r0p2/ff`: 294,448 cells, 197,764 nets, 84 macros. Overflowed gcells at iterations 5 / 10 / 15 / 20: 16 / 9 / 3 / 3, all at x 693-704, y 1192-1237 (NE corner of front_roots `u_e4`, mouth of the 56-um channel).
- Iterations 1-20 took 47 minutes; iteration 21 had run 4.6 h. A profile of the process shows 90 % of the time in `FastRouteCore::mazeRouteMSMDOrder3D`, single-threaded, on a grid of about 2,531 x 2,243 gcells x 6 layers.
- So three gcells of residual overflow start a 3D maze search over 34 M nodes, and the run then ends GRT-0116 anyway (kits older than 18:30 have no allow-congestion).
- The earlier Fable proof on the same family (no resistance-aware, allow-congestion) reached overflow 0 in 14 iterations. HYPOTHESIS: resistance-aware layer assignment is the difference. Col kits have no M8 grant, and gen switches resistance-aware off only for kits with the grant (gen_phys.py:4997).
- Dead ends: waiting on the p1 / p2 routes now at iteration 21-30 (forms ff, fe, fg, fh, fi, fa_697f40c9, fa_f9acce4c); more iterations; utilisation changes.
- Fix (KIT-OPS-5 / gen owner): `ENABLE_RESISTANCE_AWARE = 0` for every kit with hard macros, not only M8-grant kits; allow-congestion from the die default (new kits only).
- Proof: two 1-h GRT runs on the ff `4_cts.odb`, with and without resistance-aware; compare overflow and the time of iteration 21.

### p6: real overflow at one wall (MEASURED)

- Form fa (epyc10 `tl-colh9r0p6/fa`, 4:21 h): Total 62,446, of which M6 60,884 at 9.4 % M6 use. 832 gcells, all horizontal, all at x 600-720, y 1040-1240, owned by `u_ist_frame_int_o0_3` (3,583 hits) and the relay groups.
- The wall macros block M1-M5 (front_roots) or M1-M6 (col3_c); M6 is the only horizontal layer over front_roots under an M7 cap. This is the r1 / r2 class of the fleet review in a milder form.
- Dead end: relay re-siting (R-COL-3 raised the count from 95 to 850).
- Fix (DIE-S81-92, event B4): east-west M8 grant over front_roots and the 43-um top strip for p4-p6, or the frame_int_o0_3 station polyline through the channel (the `relay_polylines` key already requested from FIX-RELAYPOLY).
- Proof: plain GRT of the p6 `3_place.odb` with the M8 grant on; target is the 832 gcells going to 0.

## 4. svc hi (rs t1-t6, pvso t1/t2): synthesis stall

### Root cause (MEASURED)

- `tools/die_plan/bind_native_glue.py` wraps each native memory in its own module with the write enable as a raw per-bit port. The written Verilog then holds one `if (WR_EN[i]) mem[A][i:i] <= D[i]` statement per bit, all in one always block.
- Kit read on epyc8 `/srv/opentallas-scratch2/claude/type-svcmem/{noshare,m2r}_svc_hi_dsdv_svc_rs__t4/gen/.../rtl`:

| instance | shape | write statements |
|---|---|---|
| pbuf | 256 x 40 | 4,096 (16 ports) |
| att wq | 5456 x 3 | 16,368 |
| att sw | 512 x 32 | 512 |
| att qmem | 512 x 16 | 512 |
| att fq | 416 x 2 | 416 |

- These five are about 52 k bits. Each is below `SYNTH_MEMORY_MAX_BITS = 16384`, so yosys keeps them as memories into `opt_mem_priority` (pass 3.16.2), where the no-share copy stopped.
- The three large memories of the handoff (512x512, 640x256, 8x2120) have 0 instances in the current rs t4 and pvso t1 bound files; their .sv files are leftovers and the SRAM mapping already covers them.
- No svc_hi kit finished synthesis today on any host.
- Underlying cause: `dsdv_svc_rs.sv:436-486` and `dsdv_svc_att.sv:664+` already hold a cycle-exact macro form under `OT_SVC_ATT_MEM_MACRO` (pbuf as `ot_sram_1r1w_160x256_m1_r0c0`; sw, wq, qmem as `ot_sram_1r1w_32x128_m1_r0c0`). The S81 bind does not set the define: kit `VERILOG_DEFINES` lacks it and the bound file has 0 `dsdv_svc_mem_*` instances. The kit already ships LEF and lib for both macros.

### Dead end: the mem2reg fix (main ad97a98d1eb)

- MEASURED: pbuf alone, ORFS-image yosys, `(* mem2reg *)` form: 900 s timeout, never past PROC_PRUNE (pass 3.3). wq has four times the statements.
- MEASURED: the lane's equivalence test is 6 x 4 with 2 ports; its real-size copies had not reached yosys at 18:50.
- HYPOTHESIS: a marked memory disappears from `gen_lint_mem.tsv`, so a large native memory would silently become flops (the 64-write threshold has no bit cap).
- Stop: the m2r private copies (rs t4 epyc8, pvso t1 epyc9, rs t2 epyc10) and the pending KIT-OPS-5 mem2reg overlay and re-key. Keep `-noshare`.

### Fix

1. Structural (DIE-S81-92, B4 svc event): add `OT_SVC_ATT_MEM_MACRO` to the S81 svc bind defines. pbuf, sw, wq and qmem leave the native set; fq stays (832 bits). This also takes cells out of a type measured at 507,956 cells (hi u_rsv, HARD-S81-SVC-1, 11-13), which is above anything that has closed.
   - Proof: re-elaborate with the define; the bound file holds `dsdv_svc_mem_*` instances and no pbuf / sw / wq / qmem native memory.
2. Bridge until B4 (TYPE-SVCMEM, `tools/die_plan/native_mem2reg.py`): replace the mem2reg mark with a word-wide flop emit: per port an enable and data vector, per word a fold in port order, one always block per word, read as an indexed slice. Guard: skip when width x depth exceeds `SYNTH_MEMORY_MAX_BITS`, so lint still forces a macro.
   - MEASURED: pbuf at real size passes `proc; opt; memory; opt` in 22 s (40 `$dff`, 640 `$mux`); toy miter with 2 overlapping ports: SUCCESS.
   - Prototype: epyc8 `/srv/opentallas-scratch2/claude/fable-hard-s81/svc3/` (`gen_vec.py`, `result.txt`); mem2reg timing in `../svc/result.txt`.
   - Proof: run `gen_vec.py` on the five modules of the rs t4 kit, delete `run/`, check `1_2_yosys.log` passes 3.16 and kit LEC passes.

## 5. Dead ends, in one list

- slice_station t29 forms A / B; any retry of t27 / t28 / t36 on the pre-B4L4 bands.
- Leaf t34 a14, t75 a5, t9 a2, t73 a6 (M8 kits over M7-opaque cores); t34 fb; ve-pair moves and outline growth.
- col_h9_r0 p1 / p2 routes sitting in GRT iteration 21-30; CONS forms before B3x2d; p6 relay re-siting.
- Counting on `OT_CONS_MAX_LAYER=M9` in `die_gen_env`: no kit changes.
- svc hi: the mem2reg fix and its three private copies.

## 6. Not done

- No A/B run of resistance-aware on one col database.
- Die M9 occupancy over leaf and slice partitions (needed for the M9 grant) not measured.
- Whether density 0.35 or M9 closed slice_station t30 form c not separated.
- t39 attempt 9 result.

Evidence: kit paths as cited; parser `cong.py` (congestion report binned by face distance and net family) was run read-only over ssh, no files left on the hosts except `/tmp/claude-perf-17397.data` on epyc10 (profile sample, can be deleted) and the svc prototype dir on epyc8 `/srv/opentallas-scratch2/claude/fable-hard-s81/`.
