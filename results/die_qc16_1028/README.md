# DIE-QC-16 (2026-10-28 11:4x- PDT): QC die owner, successor of DIE-QC-15

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc16-1028. OWN / UNCHECKED-independent unless marked CHECKED
(CHECKED = read from a log/JSON written by this lane's run, after its start).
Tools: die_trial = git-archive 9c4415e27c (main + DIE-QC-13 region_stub, not yet on main) in tool13/; die STA =
git-archive ad1358b21c (FLOW-ONEMODEL-3, per-tap core insertion) in tool_om3/.

## Task 1: c_* with one early A0 tap per instance (nk 736/639, nl 796/694 routed insertion)

Input: ev/qc_k2b_p12_a0early.json (sha256 c2ab5c3c52564b0b..., made by mk_event.py from qc_k2b_phase12.json): the
16 cb* types get clock.core_taps="early", and their 64 existing A0 core taps (one per instance at the native ck pin)
get insertion 736/639 (nk) or 796/694 (nl). That makes 768 instances on the die. Before this, the c_* types had no
early core taps: the A0 ck pins hung on the nearest grid tap, and the 390/312 PLACEHOLDER was never used. trial11
therefore timed A0 at 250 while the real routed A0 is 736.

### ESTIMATE (est_early.py, trial11 routed GRT arrivals)
- Earliness needed (insertion - common): nk 486 TT / 436.5 FF, nl 546 / 491.5.
- Calibrated on the trial11 chains, the die tree delivers 0.274 ps/um TT and 0.239 ps/um FF.
- Inside the region it does not fit. The c_* region root -> glue taps is 553 TT (median; range 495-647, measured on
  trial12). The root -> A0 ck pin leg is 657-806 um (A0 2x2, centre-entry pins about 560 um above or below the region
  centre), which costs 209-312 ps. So the earliest A0 delivery inside the region is about 553 - 256 = 297 ps.
  Need: 486.
- Above the region root, 703/768 instances have an ancestor that fits. It sits median 1495 um from the pin and
  needs median 198 um of elongation. 65 instances have no ancestor that fits.

### BUILT: trial12 (same flags as trial11 + the derived event; kit 23 min; clock GRT TT/FF EXIT 0)
- tree.json sha 45b375ee0f2f79b0: 7889 taps, 768 c_* clk_c taps.
- region_dme early_taps: every A0 tap hangs at the region ROOT (node_S = root_S 407.6 model ps). miss_ps is -59..-107
  model ps, about 90-160 ps measured.
- Achieved earliness, CHECKED (early12.py on c12_TT/FF arrivals):

| | need | achieved min / med / max | shortfall (med) |
|---|---|---|---|
| nk TT | 486 | 227 / 293 / 387 | |
| nl TT | 546 | 273 / 334 / 359 | |
| all TT | | | 195 (99..273) |
| nk FF | 436.5 | 187 / 250 / 334 | |
| nl FF | 491.5 | 232 / 285 / 309 | |
| all FF | | | 188 (103..260) |

- Per-region spread of (tap arrival + DECLARED insertion), eval12 (CHECKED vs eval11):
  - c_*: TT med 258.5 / max 312.7, FF 246.9 / 295.1. trial11 was 66.2 / 106.3 and 62.6 / 98.4, but trial11 timed
    A0 at the 250 contract, so its c_* number was optimistic by about 486.
  - Other classes are unchanged (sl 64.5, su_c 94.2, coll 55.7 TT max).
- Duty TT 48.7-51.9 % / FF 49.7-54.6 %, 0 outside 45-55, MPW 0 (CHECKED, duty12.log).
- CA/STA were NOT run on trial12. A 190-ps systematic miss is a plan failure, not a timing residual.

### Finding (structural, measured)
- With a 736/796 A0 insertion, the c_* region tree cannot balance A0 against the glue. Earliness can only come from
  above the leg, and region root -> glue is 553 while root -> A0 pin is 256.
- Hanging A0 above the region root (estimate: median 1.5 mm up the feed) leaves about 790 ps FF of UNSHARED die
  clock between glue and A0 registers. At the gate's measured early/late spread on unshared die branches (0.136, from
  the seam pair below), that is about 108 ps hold damage on every A0<->glue pair (UNCHECKED). So it is not a clean
  fix.
- Clean fix: A0 insertion <= about 250 + 297 = ~547 TT (~455 FF). An in-region hang then closes: the A0 parent trunk
  is re-planned for a lower insertion, for example by the v5.0 early child taps inside A0 instead of children at the
  250 contract, with the shorter trunk balanced by wire. A faster root->A0 leg (M8/M9 express) is a second lever,
  about 0.12 ps/um, NUMBER-CHECK needed.

## Task 2: FF hold with signed core views (FLOW-ONEMODEL-3, t11i proof = DIE-QC-13 trial11 inv2-tagged)

- View dirs: none exist for prog (s8b kit has no views/) or btab. crh (qc/closed views) and crh_rp1 (autopilot views)
  have ETMs but NO provenance.json/pins_sha256, so the pin-match rule rejects them (24 instances, "view has no
  pins_sha256").
- `--core-insertion view` (gate): 96 early core taps, view 0 / missing 96 -> FAIL CLOSED. intra FF hold -281.85,
  seam -143.27 (CHECKED).
- `--core-insertion declared` (PLANNING ESTIMATE ONLY, not a gate pass):
  - intra FF hold -281.85 -> **-179.65** (CHECKED).
  - The worst intra pair moves out of su_c to c_E5_bn_10 clk_t18->clk_t3 (damage 142.2, in-region grid tree).
  - su_c early-tap damage no longer leads.
  - seam is unchanged at -143.27; kit-contract hold intra -142.18 / seam -70.61.
- Seam -143 breakdown (worst pair sl_W0_hc2 clk_t2 -> sl_W0_hc1 clk_t5; the same in W5/E4; FF, spice x1.0552):
  - LCA h1000000000 is at 1073.5 late; CPPR 147.1 -> 155.2 after scaling.
  - Unshared branches below it: launch 374, capture 428 ps.
  - Damage 110.6 = **56.9 systematic** + **53.7 OCV**. Systematic: the hc1 taps arrive 27-54 ps after the hc2 taps
    (hc2 1447-1474, hc1 1475-1501). OCV: the launch early derate on 374 ps unshared, 0.136.
  - Structural fix: (i) region balance hc1 vs hc2 in the plan (-57); (ii) a shared feed node for the seam-paired
    hc1/hc2 neighbours, so the unshared part is <= ~200 ps (OCV ~27). Estimated seam damage is then ~27, inside the
    40-ps kit window (UNCHECKED). HB4 stays a ledgered residual only.
- su_c c- vs t-tap DME balance is not done. In declared mode su_c is no longer the worst; c_* is. The c_* fix is task 1.

## Task 3: FLOW-GEN-2 canary (node a0k3, post_place_rebind=exact_count): IN FLIGHT
- Kit ot_qwen_tile_node_a0k3 kit_hash 9ab290801d71a0d5, from claude/die-qc16-fg2-1028@6356112ec8. That is
  321117422e + one json line: core_tree.post_place_rebind="exact_count" in
  physical/die_plan/qwen_compute/cores/a0/slices/ot_qwen_tile_node.json.
- The autopilot accepted it with no hold: AP 3597c704ea32, SUBMIT 12:03:20, routing on intel2.
- Pre-route CHECKED: RTL_LINT, SDC_LINT, SELRANGE, FACE_GUARD 2565/2565, LEC EQUIVALENT 14420/14420.
- Baseline 10:12 (AP 0a4950716786, CHECKED signoff.json): TT WNS -221.66 (59 ep, TNS -4406), FF hold -37.89, pair
  skew TT 131.1/152.5, FF 127.6/151.2, DRC 0.
- The FG2 hand-run trial already showed skew 53/54 but TNS -9039 (119 ep). Watch the TNS.
- Collect after ~13:25: `python3 -I .../fg2canary/tools/cmp.py <baseline signoff.json> <kit>/signoff/signoff.json`.

## Task 4: ICG enable at the A0 tile root
Sub-lane result on claude/die-qc16-icg-1028@9ce9c463a5 (results/die_qc16_icg_1028/README.md). Changed:
rtl/physical/a0_core/qfd_tile_n{k,l}_a0c.sv and tools/qwen_romleaf/a0core/icg/*. Opt-in parameter ICG (default 0);
the pinned body files are byte-identical.

- Enable: en = act | (dr != 0), with act = !rst_n | go_f | |go_h | !me_idle | nv_act (NK only).
  - go_f is a copy of the go face bit tap_q[0]; it gives the 1-cycle lead.
  - me_idle is the existing ot_qwen_w12_matvec_part.idle register.
  - dr is a 64-cycle drain counter.
  - The input faces and the enable logic stay ungated.
- Bench (CHECKED): Verilator, 12,000 cycles, 11 go commands, idle->busy, back-to-back gos, reset while idle and while
  busy. PASS on NK and NL, 0 mismatches on valid/fault bits and on valid-qualified data.
  - The gate is closed on 50 % (NK) / 55 % (NL) of cycles.
  - The en=1 control gives a strict compare with 0 mismatches.
  - A strict all-bit compare of the closing gate fails only on invalid data words.
  - 5 mutants CAUGHT on NK and NL: no lead, !me_idle dropped, drain dropped, nv term dropped (NK), reset term dropped.
    Dropping the go hold passes, which is expected: the drain covers it.
- LEC (CHECKED, yosys, pinned body as a black box):
  - ICG=0 vs main: EQUIVALENT (NK 1030, NL 516).
  - ICG=1 synthesized vs main: EQUIVALENT, because the gate is OPEN under SYNTHESIS.
  - tile_id mutant: NOT EQUIVALENT.
- NOT ADOPTABLE YET:
  - me_idle reaches the tile only through a hierarchical reference. A real gate needs an idle output threaded
    through 4 pinned modules (logic_w12, rom_tile_w12, rom_tile_nk, rp2_45), and that is a COORD re-pin.
  - The equivalence of a closing gate is valid-qualified, not strict, and needs a COORD/owner ruling.
  - The drain bound of 64 is not proven minimal.
  - The face -> ICG enable timing is unchecked.
  - The ICG is not yet in the kit or the trunk.

## Task 5: BLOCKED (main 9644a2fed lacks the RM165 CLK-INV-CAL-1 rework and region_stub).

## Added task (COORD 12:2x): nl trunk elongation (3431 um / 39 legs, 2.2x nk) + OCV-inclusive spread
Scripts are in nlent/: nl_why.py, nl_ocv.py, and the entry sweep. The shared parent_trunk_dme.py at abb5f93ce7
reproduces nl q0 byte-identically (cmp, CHECKED).

- **Why nl needs it.** It is not the entry position and not the spread of child pins.
  - nl and nk have the same distances from the entry. Children: nl 76/389/642 um (min/med/max), nk 76/423/642.
    Clusters: nl 25/291/664, nk 34/270/660.
  - Entry sweep: 21 entries, x 200/229/260 by y 400-760. The plan elongation is 2041.9 um at EVERY entry (CHECKED).
    The entry only shifts the root leg.
  - The cause is the MERGE ORDER. The greedy DME leaves one far singleton sink to the end, a0cl1: a 1-register
    cluster (t_out[504]) at the N edge (153,1138). It is then merged at the ROOT against the whole tree.
    - In the q0 plan its root leg carries 1051 um of the 2043-um excess (51 %).
    - After the routed corr iterations it is a 1700-um, 14-stage snake (d_tt 731), the long leg in the render.
    - The nk root merge also has a 722-um leg, but it pairs two subtrees.
- **Tried, plan level:**
  - Better entry: no effect (above).
  - Absorbing the two 1-register clusters (a0cl1 -> a0cl41, a0cl0 -> a0cl7): elongation 2042 -> 1847 only. The next
    outlier (a0cl4) takes the root, with a 1043-um excess and the root imbalance growing 11 -> 73 ps. So clustering
    does not fix it.
  - Fix: top-down balanced bipartition (geometric halves merged at the root) in place of greedy bottom-up pairing,
    as an opt-in mode of the shared parent_trunk_dme.py. A shared tool change -> READY ROOT-MERGE. Estimated saving:
    about the root-leg excess, ~1050 um (UNCHECKED). NOT BUILT this slice.
- **OCV-inclusive spread** (nl_ocv.py, ESTIMATE, UNCHECKED-independent):
  - Method: routed q3/q6 arrivals per sink (cluster regs min..max; child = pin + 250/202.5). For every ordered pair
    (capture late, launch early), add the approved AOCV table pessimism (g 0.21 %/mm, class A cell share, flat
    +-3 % nets, same region so no droop) on the planned branches below the pair's LCA. The children's own
    insertion is not charged.
  - The nominal spreads reproduce evr: nl 35.9/36.3, nk 39.1/40.0.

| trunk | nominal TT / FF | OCV-inclusive TT / FF | worst pair (nominal + OCV) |
|---|---|---|---|
| nl q3 | 35.9 / 36.3 | **73.6 / 75.4** | a0cl27-a0cl48 33.8 + 39.8 (TT); a0cl43-a0cl1 35.5 + 39.9 (FF) |
| nk q6 | 39.1 / 40.0 | **74.2 / 68.5** | a0cl42-a0cl47 37.1 + 37.2 |

  - Both trunks FAIL the <= 60 acceptance once OCV is included. The worst pairs split at the root or a top merge,
    with ~500-700 ps of unshared trunk, so they carry ~35-40 ps of OCV.
  - To close, the nominal must fall to <= ~20 on root-split pairs, or the split must move deeper.
  - So the nl (and nk) trunk is NOT accepted yet. It also feeds task 1: a shorter, balanced A0 trunk lowers both the
    elongation OCV and the A0 insertion (target <= ~547 TT).
