# FABLE-PD-S81-SVC-0245: structural fix for the S81 svc family (target J6, cut 11-21 14:00 PST)

Written 2026-11-20 03:1x PST. Read-only review. Sources: lanes/posts of S81-DIE-R3, S81-SVC-SPLIT-1119, FLOW-FIX-2045,
FABLE-FIX-S81-SVC2, S81-TYPES-R3; origin/main 150d614de88 (svc RTL and generators); plan_j3b / plan_j3c / plan_j4f and
asbuilt_run.svc_h8.json in intel1+epyc2 `/srv/opentallas-scratch2/claude/s81-die-r3-e8/d8j`; the live wave kits on epyc2
(`kw43-wave-1109n/runs/s81/kit-wave/s81/b05c98f7919/items/svc_*`).

## Verdict

The split into tiles of at most 500k already exists: it is the H8 provider form A (10 provider cores signed 11-19, rows
composed with no growth). What stopped it in J3 r7 is one class of error: the H value lives in five places that do not
follow each other. Fix that class first (lever 1); the rest is a rebind plus a cell census. The flat C6 form that J3c /
J4f went back to cannot close (3.4M to 5.0M instances a type), so the revert only keeps the die bind green.

Ranked levers:

| # | Lever | Owner | Needed for J6 |
|---|---|---|---|
| 1 | One H per plan, generated widths, three checks | S81-SVC-SPLIT-1119 (RTL, generators), S81-DIE-R3 (rows, bind) | yes, blocks all |
| 2 | H8 provider form A re-enters as the split; parent census at most 500k; ring cut for the two largest | S81-SVC-SPLIT-1119 rows, S81-DIE-R3 event | yes |
| 3 | Placement: provider bands as composed, parent logic fenced per band, SRAM-side registers | S81-DIE-R3 | yes (rows exist) |
| 4 | Registered reads in the three svc memory wrappers, +1 | S81-SVC-SPLIT-1119 | if the bench is green by the cut, else J7 |
| 5 | Reach: 300-um stations on the gather / scatter / stream buses from the plan knob, not by hand | S81-DIE-R3 | rides on J5's R1 knob |

## 1. Width parameterisation (b): the bug is wider than the three files named

Measured on origin/main and on the H8 as-built manifest:

1. **The bound does not use the wrappers named in the J3 r7 post.** `asbuilt_run.svc_h8.json` lists, for svc_rs, only
   `rtl/.../svc_rs/dsdv_svc_rs.sv` (parameterised, `H = OT_SVC_HV`, ports `4*(H*132+20)`) plus the two overlay copies
   `physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_fv.sv` and `.../portfix178/dsdv_svc_rs_pvso_entry.sv`.
   Both overlay copies are from 10-25 and are H16 literal: `wire [8527:0] c_gi_d`, per-face slices at 2132 offsets (105
   literal hits in the fv copy; the entry copy has `[4*2132-1:0]`). The rtl copies of the same two files were made
   H-aware on 11-08 (`localparam GW = H*132+20`, `c_gi_d[GW*f +: GW]`), and the generator `tools/s81_dv/svc_rs/svc_rs_faces.py`
   already emits GW. So the overlay is a stale generated file that shadows a correct one. This reproduces the J3 r7
   example exactly: with FM_GI 1100 the stale wrapper drives face 1 (`c_gi_d[4263:2132]`) to zero and face 2 at
   `[6395:4264]`; the H8 core reads `[4303:0]`, so its live faces 2 and 3 (`[2152:4303]`) see zeros in `[2152:4263]`
   (2,112 bits) and the low 40 bits of the wrong face above that.
2. `dsdv_svc_rs_f.sv`, `dsdv_svc_rs_entry_f.sv`, `lp/dsdv_svc_rs_lp.sv`, `lp/dsdv_svc_rs_entry_lp.sv` and the four
   `group72/` files are also H16 literal (`[4*2132-1:0]`; the lp file passes the bus straight into `dsdv_svc_sx`). They
   are not in the H8 as-built file list, so they are the same class but not the cause of the 26,540 bits.
3. **The plan rows are H16 too.** In plan_j3b (the H8 plan) every svc type still has gather buses `attnh_i0 / attnh_o0`
   2133 wide, and its `dead_inputs` rows still carry `"H": "16"` with ranges such as `gi_d [[2132, 8527]]`. The die
   netlist `bind/inputs/die_b178.v` / `die_b178_lfcs.v` instantiates `dsdv_svc_busland_2133` (4-slot ring, W 2133).
4. The only lint, `tools/s81_dv/svc_rs/rs_fv_lint.sh`, runs Verilator with `-Wno-WIDTH -Wno-fatal` and `|| true`, so a
   truncation can never fail it.
5. Column frames: I found no gather width there. The `2132` hits in `frame/col_h9.sv`, `col_h10.sv`, `frame_l4/*` are
   net names (`n2132`), and in `frame_lp/*` and `frame_lp/kit/*` they are reset-leaf indices (`lpr_r1_leaves[(2132) +: 1]`).
   S81-DIE-R3: name the frame line you saw, or drop the frames from the fix list.

Fix (all generated, no hand edits):

- **One source of H.** A plan field per svc type (for example `svc_form: {"H": 8}`) is the only place H is written. The
  event script derives from it: the `OT_SVC_H8*` defines, the regenerated `portfix178` overlays (run `svc_rs_faces.py`
  with the PORTFIX-DEAD option and write both files; never keep a copy the generator did not just write), the
  `dead_inputs` parameters, and the bus `used_width`.
- **Superset pinout at the partition boundary (owner 11-20, superset pinouts yes).** Keep the 2133-bit `attnh` buses, the
  ft slots, the landing bands and `dsdv_svc_busland_2133` exactly as they are in plan_j4f. A bus row gets
  `used_width = H*132+21`: valid stays bit 0, the lane is low-aligned in `[H*132+20:1]`, the bits above are a declared
  pad (driver 0, receiver unconnected, tie listed in `declared_ties`). This means no pin, ft, clock-band or die-netlist
  change in J6. Narrowing the die buses to `busland_1077` (the module exists) is a later clean-up, not J6.
- **Make the remaining literals follow H.** `dsdv_svc_rs_f.sv`, `dsdv_svc_rs_entry_f.sv`: `parameter integer H = OT_SVC_HV`
  and `4*(H*132+20)`. `lp.py` and `gen_service72.py`: take the width from the port declaration of the module they wrap
  (they copy the text today). `svc_rs_faces.py` line 228 keeps a 2132 record for the table; leave it, but label it H16.
- **Three checks, all must be 0 before svc H8 rows enter an event:**
  1. WIDTH: Verilator lint of every bound svc type top at the plan defines with WIDTH warnings as errors
     (`rs_fv_lint.sh` without `-Wno-WIDTH`, without `|| true`), plus a bind check that compares each elaborated port
     width of the type against the plan bus `used_width` and stops on any difference (class `WIDTH-FORM`).
  2. FRESH: for every file under `bind/source_modules` that has a generator, regenerate and compare the sha; a mismatch
     stops the bind. This is the check that would have caught the stale overlay.
  3. LIVE-TIE: the bind's tied-input census must equal the dead-input proof run at the same H as the bound
     (`parameters.H` in the row must equal the elaborated H, else error). S81-DIE-R3 did this by hand for r7
     (83,926 dead, 26,540 live); make it the gate. Neighbouring svc types with different H are an error.
- Also from r7, same event: `declared_ties` for the `ot_s81_svc_attn_s` literals (`job_t {6'd0,..}`, `sc_cr`, `pv_cr`,
  `q_w[511:256]`), `dsdv_svc_mem_ar wa[3]`, and the pvso_entry__t1 hcore `rst_n` path (0 bound leaves: the entry wrapper
  has one more `u_` level, the same naming class as the 31 macro paths reported 11-18 21:00).

## 2. The split (a): H8 provider form A, with a census gate and one more cut

Partition boundary: module boundaries inside the svc type, as composed in `rows_h8_svc16_1119.json` (epyc8
`/srv/opentallas-scratch2/claude/s81-svc-split-1119/`). Per type in plan_j3b:

| Tile | svc_lo count | svc_hi count | Cells each | Outline um | Signed 11-19 (TT setup / FF hold ps) |
|---|---|---|---|---|---|
| ot_s81c_attn_hcore | 32 | 32 | hard | 157.68 x 259.2 | earlier view |
| dsdv_svc_sx_hrow | 8 | 8 | hard | 138.24 x 164.16 | earlier view |
| ot_s81_svc_idx_hslice_fp | 32 | 0 | 59,836 | 77.76 x 276.48 | +104.4 / +7.8 |
| ot_s81_su_sml_fold2 | 8 | 8 | 87,328 | 103.68 x 259.2 | +84.6 / +20.9 |
| ot_s81_svc_merge_h4 | 8 | 8 | 82,680 | 103.68 x 259.2 | +103.8 / +14.3 |
| ot_s81_su_smd_fold2 | 4 | 4 | 52,966 | 69.12 x 259.2 | +97.9 / +22.5 |
| ot_hdc_v41x_attn_tr_x (4 XOFF masters) | 4 | 4 | 27,880 | 60.48 x 259.2 | +129..+151 / +25..+28 |
| ot_s81_su_smc | 1 | 1 | 65,901 | 77.76 x 259.2 | +89.2 / +17.3 |
| ot_s81_su_smr | 1 | 1 | 40,242 | 69.12 x 259.2 | +80.6 / +18.0 |
| parent soft | 1 | 1 | see below | type outline | not built |

Provider cells leave the parent: 3.70M a svc_lo type, 1.79M a svc_hi type (sum of the plan `cells` fields). Every
provider is at most 87k cells.

Parent soft size, which is the real risk:

- Measured 11-09 on the H8 bound: 381,961 (lo) and 228,760 (hi rs t2).
- Estimated for today's RTL (not measured: needs the H8 rebind): H16 shell measured 11-19 with cores black-boxed minus
  the measured H16-to-H8 delta of 204k (hi t2: 432,791 to 228,760): lo rs_w t1 about 393k, **lo t7 about 495k**,
  pvso_entry t1 about 420k, pvso_entry t2 about 302k.
- Gate: after the rebind, read the parent count of all 16 types from the bind census before any kit launches. Limit 450k
  (the largest type ever closed is about 517k, so 500k has no margin).
- Second cut for a type over 450k (expected: lo t7, maybe pvso t1): the clock-landing rings `ot_dp_clk_landing_cas`
  become hard boxes in their own `band_fixed_um` rectangles, which the plan already reserves. Measured 11-19: 8 rings on
  rs_w t1 take the shell from 597,137 to 476,923, about 15k cells a ring; t7 has 14 rings, so about 210k less, giving
  about 285k. The ring is already a module with a fixed band, a forwarded clock and a strap; it is the cheapest box.
  Third cut if still needed: `dsfd_ctrl_rg3_native32` x 2 (status "reuse" in the plan contents; the split lane measured
  bind_native at 164k).

Seams and cycles:

- Provider seams. Each provider box sits in the band of the hcores it serves (four freed `g_h[8..15]` bands, 259.2 um
  tall), so the provider-to-hcore distance is inside one band. Required before kits: both-side registers on every
  provider pin (close-by-construction). Only `idx_hslice_fp` is known to have pin registers on (2d2291f3f7). For
  sml / smd / merge_h4 / smc / smr / tr_x this is **not checked**: run PRECHECK reach on the H8 bound (core pin to first
  flop, 300 um) and add a pin register where a pin has none; +1 cycle on that seam is pre-approved and is internal to
  the type (the 11-19 re-baseline found 0 die-lane cycles for the form: AR 838.8 / MTP 2701.3 unchanged).
- Gather (score) bus. Inside the slice it is `dsdv_svc_sx`: 4 rows x 4 faces, each face lane split in two halves of
  269 bits on 276-bit relay stations; a hop is centre register, A, B, then C, leaf pin flop: 5 cycles at `NR = 1`,
  `2*NR + 3` in general. Between two svc partitions it is the `attnh` bus: out pin flop, plan stations (`ot_dp_st`
  W 2133 are already in the bound), then the receiver's 4-slot landing ring on the forwarded clock. With the superset
  pinout this path is bit-for-bit the J4f path; at H8 only bits `[1076:0]` of each lane are live and the pad flops drop
  out as declared ties.
- Broadcast (dn 805 b), up (16 b), P.V return (514 b) and scatter (1,076 b + v) do not depend on H; they cross exactly
  as in J4f. No width work there.
- Reach. The type is 1442.88 x 2980.8 (lo) and 1442.88 x 2747.52 (hi). With `NR = 1` a slice-internal leg is about a
  quarter of the centre-to-centre hop: about 360 um east-west and about 700 um north-south (lo N face to hi S face).
  The 300-um rule (R1, default on S81 from J5) therefore needs more stations on the N / S legs. Take them from the plan
  station rows (`relay_depth` / `istation_respace` under `REACH_UM_PER_HOP 300`), which price the latency in LATCHECK,
  not from a hand-set `NR`. Estimate: N / S hop 5 cycles to about 11, E / W 5 to 7; the role ROM GO delay
  (`svc_rs_tree.py`, "5 cycles a hop") must be regenerated from the plan depth in the same event. Not measured.
- H8 itself is the two-pass (reuse) engine: svc attention throughput cost was accepted with option A on 11-19.

## 3. Placement and outline (d): fits, no growth

- Outlines stay: svc_lo 1442.88 x 2980.8, svc_hi rs 1442.88 x 2747.52, pvso_entry 1442.88 x 2877.12. The die has
  103.7 um spare in X and Y and 8 svc columns abut, so nothing may grow.
- The H8 rows drop 32 hcores a type: 32 x 157.68 x 259.2 = 1.31M um2 freed, and put 58 (lo) / 26 (hi) provider boxes at
  signed sizes into those four bands; the svc_lo macro row at y >= 2415 lifts 8.64 um. Private G0 on D8h: only the two
  cut errors that D8h already had; reach_fix 0 errors.
- For comparison the H16 provider split does not fit: 62 core outlines need 1.196M um2 against 1.138M um2 free.
- Add to the rows (S81-DIE-R3): (1) fence the parent logic by instance prefix to the band it serves (`u_att.u_eng.g_t[i]`
  to band i, `u_sx` to the hrow band, `u_cland_*` to their `band_fixed_um`), so the 300k to 450k parent cells are
  seeded and not spread over 3 mm; (2) the SOFT0.. regions stay for SE / SM glue; (3) bank sites for shared stations in
  free channels, as the leaf hi-corridor tool does (`s81_hi_corridor.py sites`), so a station bank does not land inside
  a provider box.

## 4. Registered reads (c)

Measured in the RTL: all svc SRAMs sit behind three wrappers, `dsdv_svc_mem_ar`, `dsdv_svc_mem_la`, `dsdv_svc_mem_lr`
(68 macros on a hi type, 97 on lo t7). In all three the macro `rd_out` goes through the write-bypass mux straight to the
consumer (up to 512 bits), and in `mem_la` / `mem_lr` the read address is combinational from the pointer (`rp + 1`,
bank select) into the macro pin. Neither side is registered, and the macros sit in the macro row at the top of the type.

Fix: one parameter `RREG` (define `OT_SVC_MEM_RREG`) in the three wrappers: a capture register on `rd` after the bypass
mux and a register on the address / write pins, both placed at the macro (macro-side group in the plan). Read latency
+1 (pre-approved). Because `mem_la` / `mem_lr` are look-ahead stores, the cheapest correct form is to advance the
pointer one cycle earlier inside the wrapper so the consumers do not change; `mem_ar` already has a `SYNC` option for
its address. Proof: the lock-step bench with shift 1 (pattern of `tb_vp_cfr` for `OT_S81SL_VP_SRAMREG`) and LATCHECK +1
on the 16 rows. This does not depend on levers 1 to 3, but it needs the same rebind, so put the define in the J6 rows
only if the bench is green by 11-21 08:00 PST; otherwise J7. Not blocking.

## 5. Evidence per lever (e)

| Lever | Evidence | Where |
|---|---|---|
| Flat form cannot close | 4,992,695 instances (lo t7), 3,394,731 (hi t4), 3,531,946 (hi t6); yosys 3.5 h; floorplan repair 50,584 / 55,780 endpoints, all violating, 0 % gain; t7 repair 6 h 05 | FLOW-FIX-2045 02:0x; epyc2 kits t4 a14, t6 a14 `2_1_floorplan.tmp.log` |
| Flat form cannot close | lo7 11-17: 5.69M instances, core use 0.899, movable 61.4 % of free area, after timing repair target density 1.0636, GPL slack -2,572 ps; no placed DB written | S81-TYPES-R3 11-17 13:15 |
| Where the area is | hi t4 synth: 2.109M um2 = hcores 1.41M + SRAM 0.137M + hrow 0.062M + cells about 0.50M (4.17M flat cells) | epyc2 t4 a14 `synth_stat.txt` |
| Providers close | 10 cores signed 11-19, DRC 0, TT +80.6..+151, FF hold +7.8..+28 | S81-SVC-SPLIT-1119 08:28 |
| Parent size | 381,961 / 228,760 measured 11-09; H16 shell 597,137 and 699k, 476,923 with 8 rings boxed | split lane 04:37, 05:44, 09:03 |
| H16 split does not fit | 1.196M um2 needed, 1.138M um2 free, die spare 103.7 um | split lane 04:25 |
| Width class | stale overlay `wire [8527:0]`; plan_j3b buses 2133 and `"H": "16"`; lint `-Wno-WIDTH` | origin/main 150d614de88; plan_j3b |
| Live ties | 83,926 dead, 26,540 live at H8; 202 bind errors | S81-DIE-R3 02:11 |
| Registered reads | unregistered bypass-mux read in mem_ar / la / lr | origin/main rtl `svc_rs/dsdv_svc_mem_*.sv` |
| Core-to-core links | hi t2 flat: 72 cores, 0 core-to-core links, every core input ends at logic | FABLE-FIX-S81-LEAF 11-19 13:59 (blind on t4/t5/t6) |

No svc type kit has been placed or routed in the H8 form on the current RTL. Levers 2 and 3 rest on core sign-offs, the
11-09 census and the G0 of the rows, not on a type kit.

## 6. Order of work to the J6 cut

1. S81-SVC-SPLIT-1119, now: regenerate the two portfix178 overlays with H from the defines; parameterise `_f`,
   `_entry_f`, lp and group72 emitters; lint with WIDTH as error at H8 and H16 on all fv variants; add the FRESH check.
2. S81-DIE-R3: `svc_form.H`, `used_width`, dead-input rows at H 8, the declared ties, the pvso hcore path; WIDTH-FORM
   and LIVE-TIE in the bind. Private bind of the 16 svc types on plan_j4f + `rows_h8_svc16_1119.json`. Pass = 0 errors,
   0 live ties.
3. Same bind: parent census of 16 types. Any type over 450k gets the landing-ring boxes in the same event.
4. Two proof kits to GRT TT, in parallel with the event (r712): svc_hi rs t4 and svc_lo rs t7, private, H8 rows.
5. J6 carries the svc H8 rows if steps 1 to 3 are green by 11-21 10:00 PST. The proof kits will most likely not have a
   routed TT number by the cut; say so in the event note. If step 2 is not green, J6 keeps the C6 form and svc goes
   to J7; do not put svc H8 rows into J6 unproven a second time.

## 7. Stop list

- Do not put svc H8 rows into any event until WIDTH, FRESH and LIVE-TIE are all 0.
- Do not hand-edit the `portfix178` copies, and do not "fix" the truncation by widening the H8 core ports to 8528 with
  ties.
- Do not narrow the die-level `attnh` buses, ft slots or `busland_2133` in J6.
- Do not pursue the H16 provider split, rows v2 (+155.52 um X a type) or any die or outline growth.
- Do not spend lane time on the flat C6 / H16 svc kits (floorplan skip, longer runs, more retries): they are count
  sources at best. Whether the live rows are stopped is COORD's call under the unsignable rule; I stopped nothing.
- Do not launch H8 type kits before the parent census; do not launch a parent over 450k.
- Do not set `NR` or the role-ROM hop delay by hand; do not accept a lint that runs with `-Wno-WIDTH`.
- Do not count the column frames as part of this bug until a real gather-width line is shown.

## Not checked

- Pin registers on the providers other than idx_hslice_fp; any reach number on an H8 bound.
- The H8 parent count on today's RTL (estimates only), and the ring-box saving on t7 (scaled from rs_w t1).
- Whether the plan `dead_inputs` rows with H 16 were what the r7 bind read, or only S81-DIE-R3's separate re-proof.
- The consumers of the three memory wrappers (which ones tolerate the look-ahead form of the +1), and the read timing of
  the SRAM views.
- The N / S and E / W cycle estimates in section 2 (geometry arithmetic, no PRECHECK run).
- GRT or CTS results of hi3 flat (11-17); I found no post with its numbers.
- `tools/landed_parent/lp.py` itself (no 2132 literal in it; the literal is in its generated outputs).
