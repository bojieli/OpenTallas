# FABLE-CLOSURE-STRATEGY 2026-11-15 13:55 PST: six levers, DRT-0255 re-read from the route logs, stop list

Read-only review by FABLE-CLOSURE-1310. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 11:55 strategy, FABLE-PD-S81-1200 / KV-1200 / HEAD-1115 / QC-1115 / QC-1245, the queue 11:47-13:40,
`failure_breakdown.py` (13:29), and on the build hosts: every `5_2_route.log` younger than 30 h, one QC kit in full
(intel1 `s29q103S4Q2/items/slw_su_l1__cla2a78701/attempt_19`: route log, GRT log, `pdn.tcl`, `config.mk`, `m8_grant.json`),
epyc7 `s81-b3-clk/run/b/{B6gErr,B6gF1}/elab.log`. MEASURED = read or computed by me today. REPORTED = from a lane post.
INFERENCE is marked. No STA, no route, no database read.

`failure_breakdown.py` 13:29, technical rows: S81 types 36/394 (50 running, 24 held); HEAD 19/26 (6 running, hd_host_e
stopped after CTS); QC 3/127 (51 held, 47 running, 2 detail route error, sle_sc_v3 stopped after CTS); KV 5/56 (31 held,
15 running, kv3_hub_Wo ring band). No signed type was added on any die since 11:18.

## 0. The seven levers of 11:55: what moved

| 11:55 lever | state at 13:40 (source) | moved |
|---|---|---|
| 1 `DRT-0255` | Lane DRT0255-PROOF-1115 live. Probe of 16 kept databases: pin under strap 2, ring-band net 6, boundary / ft net with no pin in the box 7, clock 1 (REPORTED 13:10). 6 proof routes started 13:00-13:05, no route result yet. hd_spn attempt 5 with the die phase: 0 of 1,942 M7 face pins under the strap pair, was 76 (REPORTED). Pin-band key merged, opt-in (edc4df0ed6c). 3 more failures since: slw_su_l1 12:37 and 13:22, kv3_hroot 13:12 | partly; see lever 1, the flags will not cover most of it |
| 2 col3_c view (276 markers) | Given to S81-COLABS-1115. No post of that lane in the queue. col held | no |
| 3 `safe8_ntf` clock pin | Same lane, no post. lepw_mu_LP__t2 failed again 11:50 with `DRT-0073`. lepe_mu_LP__t2 was released from its hold at 12:29 without a new view | no; one type released against the stop list |
| 4 seam reset | pc2 is the reference (recovery 0, removal 579 / -238 on 35 nets). pg, pg2 (111 copies by sink tap) and ph (falling edge) are built; their numbers are not posted. Rows gate B6gErr: G0 68, no bind result | partly |
| 5 QC fe / hc / st_b | sc + fe rows drafted (535 rows, binds running). S4q3c adopted (4 st_a_v2 types). hc: S4q5 (+311 um) built, then FABLE-PD-QC-1245 measured that the hc1 overflow is all at y < 40 um at 12 % utilization, so the height does not help | yes, and the hc fix changed |
| 6 KV hg / hgi | 7u passes all gates (post). 7v = 7u + hg stations, phase 2 to rerun on the pin recipe. pc delta and ectl q2 clock leaves have lanes (r143) | yes |
| 7 die clock sites | HEAD u201: 485 / 1 / 1 / 0, DRC 0 at step 3, 12.1 GB at 8 threads; recipe merged 13:25 (57db4f9d7f6). 12 steps without reaching 0 peaked 56.5 GB, so the step cap is part of the recipe. Native stamp v2 covers all 264 hd_tile | yes |

Also MEASURED: `ELAB_RC=2` on B6gErr and on B6gF1 is the same line in both `elab.log`: `bind: ERROR yosys failed (rc 137)`.
The process was killed; it is not an error of the rows. Neither event has a bind or LATCHECK result for that reason alone.

## 1. Levers, ranked

| # | dies | lever | unblocks | owner | state |
|---|---|---|---|---|---|
| 1 | QC, KV, S81, HEAD | `DRT-0255`: the unreachable terminal is a routed wire end on M4-M8 at the PG strap pair, in the face strip. Geometric probe + two proof routes that test this, not only the cell keep-out | 76 failed route logs in 30 h, 35 today; about 50 types | DRT0255-PROOF-1115, GENBUG-IMPL | NEW evidence, changes the proof set |
| 2 | QC (then KV, S81) | Landing strip depth and density at the faces (budget keys), in place of the hc height | hc0 / hc1 (4 types held), and the 22 logs whose failing net is a landing ring | DIE-QC-103, QC-CB-GEN-1115, KV-102 | hc part reported 13:35, not yet ruled |
| 3 | S81 | Event F part 2 waits on three items; seam reset: per-net table of the 35 removal nets decides pad or falling edge | 216 col types | S81-SEAM-RST-1115, S81-COLABS-1115, S81-TYPEMERGE-IMPL, DIE-S81-92 | BLOCKED on all three |
| 4 | S81 | svc synthesis pilot from B6gE | 16 svc types | S81-SVC-SYNTH-1115 | dispatched 13:09, no result |
| 5 | HEAD, QC | Types stopped after CTS on the setup estimate: hd_host_e -236 ps, hd_host_w, hd_serdes, sle_sc_v3 -204 ps | 3 of the 7 open HEAD types; 9 sc types | HEAD-100, QC-SC-ROWS-1115 | HEAD part has no lane post today |
| 6 | KV | 7u now, 7v on the pin recipe, then pc delta and ectl q2 clock leaves | 31 held KV types | KV-102, KV-PC-DELTA-1115, KV-ECTLK-RL | dispatched r143, not repeated |

### Lever 1. DRT-0255: what the route logs say

Evidence (MEASURED; scripts `d255.py`, `d255b.py`, run on intel1, epyc2, epyc10; epyc7 / epyc8 / epyc9 returned no rows in
170 s and are not counted; data in `lanes/fable-closure-1310/drt0255_errors.tsv` and `drt0255_terminals.tsv`):

- 76 route logs with `DRT-0255` in 30 h (a few are the same run copied to a second host), 192 error blocks, 35 logs from
  today. By die where the path names it: QC 23, KV 10, S81 8, HEAD 5.
- Each error prints the terminal the maze could not reach. In 180 of 192 blocks every such point lies on the edge of the
  route box: it is the end of a wire already routed in the neighbour box, not a cell pin, macro pin or die pin. 11 blocks
  are cell pins (M1 points inside the box), 1 mixed. This is why the probe found "no pin in the box" on 12 of 16 kits.
- Layer of the 212 wire-end points: M4 48, M5 29, M6 38, M7 28, M8 69. None on M2 or M3.
- Position against the PG pairs of `pdn.tcl` (M5 0.312 wide at 2.064, M6 0.672 at 1.968, M7 0.672 at 4.128; pitch 4.32 / 4.32 / 8.64):

| layer of the wire end | count | where |
|---|---|---|
| M4 (horizontal) | 48 | 44 at y mod 4.32 = 2.0-2.75: directly under the M6 pair (1.968-2.64) |
| M8 (horizontal) | 69 | 58 on tracks 24-33 of the 18-track type band (tracks 18-35): directly over the M6 pair, which covers 47 % of that band |
| M6 (horizontal) | 19 with a `pdn.tcl` | 17 on the first track above or below the M6 pair |
| M5 (vertical) | 18 with a `pdn.tcl` | 6 beside the M5 pair, 12 at the phase of the M7 pair |

- 50 of 76 logs have their nearest failing box within 60 um of a type edge, 62 within 100 um. Failing net family (a log can
  have two): landing ring (`u_cland_*`, `u_ring.dch[*].u_dsel`) 22, ft / face output (`u_ft_*`, `rsn_o`) 15, clock 4,
  repair or synthesis nets 27, other 20. 29 logs fail on one net in two or three boxes in a row along one track.
- Violations after iteration 0 in these logs: 3,895 to 142,385, median 60,821. Col kits start at 104,461 and converge,
  so the count does not separate the failing kits.
- slw_su_l1 cla2a78701 (failed 12:37): GRT ends with 0 overflow on every layer, usage M4 9.0 %, M6 4.5 %, M7 5.5 %,
  M8 1.35 %. Iteration 0: 57,822 violations, of them M8 shorts 3,548 and V7 cut spacing 3,433 on 34.6 mm of M8 wire (one
  short per 10 um of M8). `OT_PG_TRACK_TRUTH = 1` was on; `OT_PG_CELL_KEEPOUT = 0`. The same type failed three times today
  (cla2a78701 12:37, clcc9d0155 08:xx and 13:22) at y 709.08, x 22.8-42.75.

Root cause (INFERENCE from the positions; the blocking shape is not identified): horizontal trunks in the face strip are
pushed to M4 and M8 in the gcell rows that hold the M6 PG pair, because the track-truth model removes M6 capacity there
and GRT sees the rows above and below as free. Detail route then cannot legalise the wire end at the box edge next to the
fixed PG metal. It is a property of the upper-layer PG pairs and the M8 type band, not of a cell under a crossing and not
of the M7 face-pin phase. The keep-out and die-phase flags address 2 of the 16 probed kits (REPORTED) and, by this
reading, none of the 180 wire-end blocks. The track-truth flag alone did not prevent it (su_l1).

Fix:
1. DRT0255-PROOF-1115, 10 minutes per kit on the kept `5_1_grt.odb`: for each point in `drt0255_terminals.tsv` (columns:
   host, die, kit, net, layer index, x, y) list the fixed shapes (special wires, obstructions, macro OBS) within one
   spacing of the point on that layer and on the layers above and below. This names the blocking shape and replaces my
   inference by a measurement.
2. Two more proof routes on slw_su_l1 cla2a78701, restart from GRT, alongside the six running:
   A. `MAX_ROUTING_LAYER = M7`. GRT uses 1.35 % of M8 there; if the route passes, M8 is given only to types whose GRT
      needs it (the S81 p6 class), not to every type.
   B. M8 kept, and GRT capacity of M4 and M8 reduced in the gcell rows of the M6 pair (same hook as `pg_track_truth.tcl`,
      which today adjusts the PG layer only). Pass = no `DRT-0255` past iteration 1.
3. Read the six running proof routes with this split: a pass on hd_spn or t49 (pin under strap) says nothing about the
   ring and ft classes. Do not put the three flags into `die_gen_env` of all dies on the hd_spn result alone.
4. S81 B6gE restored M8 on every type below the ceiling (136 keys released 13:35). Watch the first leaf route of that set
   for M8 shorts after iteration 0; if they are of the su_l1 order, apply the outcome of route A to S81 as well.

### Lever 2. Face landing strips: depth and density, not block height

Evidence: REPORTED and MEASURED by FABLE-PD-QC-1245 (13:35): slw_hc1 cl68f9248e at 12 % utilization, overflow 40,527, all
at y < 40 um, 89 % on `u_cland_b_hw_i` (1,573 bits on 405 um of S face); hc0 also 12 %. S4q5 changes 115 numbers and
leaves 62 N-face pins, 1,294 start-tree nodes and the bump field at the old y. MEASURED by me: the same landing rings are
the failing nets of 22 `DRT-0255` logs (sle_hc2 x3, st_b v1 / v2 x3, hc0, kv3_io_cor x6, kv3_hroot x2, kv3_hgi_v2, hd
host_fdi), 16 of them within 60 um of the face. FABLE-PD-QC-1115 found the same clump on cbn_q11 (SW corner).

Root cause: the ring and its `dsel` logic are placed in the first 20-40 um behind the pin face at full density, on every
die that uses the landing generator. It shows as GRT overflow on hc1 and cbn_q11 and as `DRT-0255` where GRT just passes.

Fix:
1. DIE-QC-103: do not adopt S4q5. Set `budgets.cland_strip_rows_types` / `cland_strip_density` for `b_hw_i` on hc0-hc3
   (about 100-120 um deep, cap 0.45) in the rows delta; pilot one hc1 and one hc0 to GRT at 717 um. Keep hc0 / hc1 held
   until that pilot, not until S4q5.
2. QC-CB-GEN-1115: the same keys for st_b (`cland_b_hw_ctl_hc3_i`), fe (`l9_eo_l9_wi_i`) and the cb landings, one delta.
3. KV-102 and TYPES-KV-FAIL-1115: io_cor, io_cor_v1, hroot and hgi fail on `u_cland_ft*_i` / `host_fdi` / `ectl_Q_N` rings
   50-70 um from the face. `band_spread` is already 7.0 (FABLE-PD-KV-1200). The open variable is strip depth; take the
   generator keys of step 1 into the delta after 7v. INFERENCE that it is the same clump: no KV GRT map was read.
4. This lever and lever 1 meet at the face strip. If probe step 1 of lever 1 names PG metal, lever 1 fixes the class and
   this one only lowers the load; if it names nothing fixed, this one is the fix.

### Lever 3. S81 Event F part 2: three open inputs

State (MEASURED from the queue): F part 2 needs seam reset rows, cols tap rows (ready, 217 types), tridx, and the col3_c
view. Open: (a) no passing reset pilot, (b) no post from S81-COLABS-1115, (c) the superset monitor pin (3 new G0 errors).
B6gErr and B6gF1 have no bind because yosys was killed (rc 137): rerun both elaborations at plan priority before reading
anything into `ELAB_RC`.

Seam reset, next step (INFERENCE, arithmetic on pc2): pc2 has recovery clean with +104 ps worst and removal failing on 35
nets (579 endpoints, worst -238). Removal is a hold-type check on 35 copy nets, so:
1. From the pc2 run, one table of the 35 nets: removal deficit, recovery slack of the same endpoints, launch tap, capture
   tap. 10 minutes with `ac5.tcl`.
2. Nets where recovery slack >= deficit + 30 ps: one fixed delay cell on the copy output (a rows key, no RTL).
3. The rest (expected: the copies whose capture tap is the late one, about 240-280 ps): form ph on those copies only.
   A mixed form is legal because each copy is its own stage; `bind_reset` and the `tb_ot_pl_seam` miter cover it.
4. Post pg / pg2 / ph numbers in the pc2 format even if they fail; pg2 with 111 copies is the test of the tap reading.

col3_c and `safe8_ntf` views: S81-COLABS-1115 owes a first post (generator rule or regenerated LEF, and the one-kit
re-route from `5_1_grt.odb`). Until then col runs to CTS / GRT only, and lepe_mu_LP__t2 / lepw_mu_LP__t2 /
lepe_nh_mus_LP__t1 must not route: put lepe_mu_LP__t2 back on hold (released 12:29).

### Lever 4. svc synthesis pilot

Unchanged from FABLE-PD-S81-1200 (r145): 16 svc types, 33 of 33 synthesis logs of the old tree never finish. The pilot from
B6gE (svc_hi rs t3, svc_lo rs t6, stop after `1_2_yosys`) has no result yet. It does not wait for Event G. It is the only
measurement that says whether `OT_SVC_ATT_MEM_MACRO` is enough or the 416 / 512-write native memories still stall.

### Lever 5. Post-CTS setup stops (HEAD host / serdes, QC sc)

Evidence (MEASURED, wave lines): hd_host_e 12:02 `setup_est -235.95`, pin-register mean 449.87 at bound 450; hd_host_w
12:15 and hd_serdes 12:25 the same stop class; sle_sc_v3 13:22 `setup_est -203.88`, pin-register mean 256.71 at bound 250.
REPORTED 11-14 22:2x (TYPE-HDEPC): hd_host_e is timed against a stale `u_epc` view. hd_host_w now has the b64 keep
(LEC equivalent, 12:18). Not examined by me: the failing path families of the three HEAD types.

Fix: HEAD-100 posts, per type, the path family behind the estimate from the kept `4_cts.odb` (one `report_checks` by
group, as KV-102 did for hg_v1) and whether the `u_epc` view in today's kit is the corrected one. These are 3 of the 7
HEAD types still open; the die route work does not close them. sle_sc_v3 belongs to the sc rows (QC-SC-ROWS-1115,
binds running); do not relaunch it before those rows adopt.

### Lever 6. KV

As r143: post 7u (b7156937f334, all gates pass); rerun 7v phase 2 on `run_gate_kv7pin.sh`; pc delta; ectl q2 clock
leaves before any hold buffer. One addition from lever 1: kv3_hroot failed 13:12 on `u_cland_ft10_i/u_ring.g_tag` and was
relaunched 13:24 unchanged (attempt 14). It is on the stop list; hold it with io_cor until the proof routes report.

## 2. Stop list (technical dead ends)

1. Relaunching a `DRT-0255` type unchanged (slw_su_l1 three times today, kv3_hroot attempt 14).
2. Treating a pass of the hd_spn / t49 proof routes as proof for ring, ft and boundary-net failures; rolling the three PG
   flags to all dies on that basis.
3. More cell keep-out under M5 x M6 crossings as the `DRT-0255` fix: 0 of 16 probed kits, 11 of 192 blocks are cell pins.
4. S4q5 as built, and any hc height growth before the `b_hw_i` strip pilot.
5. `band_spread` rows for KV ring bands (already 7.0).
6. Routing col types before the col3_c view; routing the three lep types before the `safe8_ntf` view.
7. Reset forms by grid or regex (pa, pc, pd, pe, pf); timing repair on async reset nets.
8. svc kits from tree `7073a6b4a59`; svc without `-noshare`.
9. Reading `ELAB_RC=2` of B6gErr / B6gF1 as a design error (yosys rc 137).
10. Kept from 11:55: more route iterations on col; `hold_hb4` pads for the KV port contract; cbn_q11 as built; snapping
    a built die clock tree onto a site template; M8 as the fix for leaf y-slots; B6gslcf / B6gshcf, S4x / S4v2,
    KV 7m / 7n / 7g, run_gate_kv7r8, bksel at virtual clock 975.

## 3. Not checked

- Which fixed shape blocks the wire ends (lever 1 step 1). The PG-pair reading is position statistics only.
- Route logs on epyc7, epyc8, epyc9 (scan returned nothing in 170 s). 30 of the 76 logs are private or proof kits whose
  die I did not resolve; 35 M8 points come from kits without a readable `pdn.tcl`.
- Results of the six proof routes, of pg / pg2 / ph, of the svc pilot, of the S81-LEAF-T14 form R GRT (447 -> 71 at
  iteration 10 as given in my brief; no queue line), of S81-COLABS-1115.
- The HEAD host / serdes path families; any KV GRT congestion map; the hc0 mechanism (QC-1245 F1c: not measured).
