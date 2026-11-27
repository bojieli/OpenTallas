#!/usr/bin/env python3
"""plan_gate_pre: pre-bind closure check for a die plan event (PLAN-GATE-PRE-1115, ruling r196, FABLE-FLOW-1800 class 1).

A plan gate (G0 / elab / bind) is run on a hand-assembled tree: compose tree + bind overlay + rows of other lanes + staged
tools.  Nothing compared the parts before the 1-2 h bind started.  This check takes seconds, reads only, and fails fast with
one named reason per defect.  It is a precondition check, not a limit on the design run.

    python3 -I tools/die_plan/plan_gate_pre.py check --tree BINDTREE --plan PLAN.json [--sidecar SC.json]
        [--asbuilt AB.json] [--compose-tree T] [--baseline-plan BASE.json] [--rows-proof P.json ...]
        [--rows FILE ...] [--skip CLASS ...] [--json OUT] [--quiet]
    python3 -I tools/die_plan/plan_gate_pre.py mkproof --plan PLAN.json --baseline-plan BASE.json --lane LANE
        --evidence PATH --out P.json [--result pass]

BINDTREE is the directory the bind runs in (cwd of `python3 tools/die_plan/bind.py`): it holds tools/die_plan/*.py and the
overlay.  Five classes, each finding line starts `FAIL <CLASS> ...`:

  SCHEMA   every key of the composed plan is known to BINDTREE/tools/die_plan/schema.py (the G1d miss: overlay ovl_b6E carried
           the B6gE schema, the compose tree the BANDTAP one: 17 "unknown key band_fixed_um"); die_plan.schema.json of the
           tree equals the dump of its schema.py; with --compose-tree every schema property of the compose tree exists in
           the bind tree (SCHEMA-TREE-SKEW names the overlay).
  INPUT    every path the elab/bind reads exists: the as-built lists files / prefer / netlist / rtl_roots / hard_params
           (resolved against base as bind.py does), map_file, clock_landing_table, dead-input proofs, the plan and sidecar.
           The G1d miss: hard_params.json removed by a cleanup, found after the elab.  Its manifest is also the keep set for
           cleanup (--list prints the resolved paths).
  TOOLS    the tool modules of BINDTREE/tools/die_plan come from one consistent source: every `import X; X.attr`, `from X
           import a` and call `X.f(...)` between sibling modules resolves to a name that exists with a matching arity.
           Catches the KV 7u tree (core_tap_early_ps called with another arity than schema.py defines, reset_tree
           without pin_root_copies, a gen_phys.py older than the schema.py next to it).
  GEOM     no station, relay or reset-relay site (ft_slots / internal_stations regs_um, reset.local_taps_um, reset.tap_um) lies
           inside a landing ring core (cl_*) of its own type, every overlap listed (G0 has no such check: 2 KV krsp stations in
           ring cores passed it, r235).  With --baseline-plan every overlap the baseline lacks is refused, with --strict-cores
           every overlap; the overlaps over other cores of adopted plans are only counted (WARN).
  ROWS     rows of another lane in the plan (reset.consumer_localization, the rows a lane merges into an event) carry a
           passing ROWS-PROOF: a dry-run of the consumer check on the EMITTED bind RTL, keyed by the rows' sha.  Rows equal to
           the --baseline-plan (the adopted plan) need none.  QC-SC-ROWS' reset rows had never been dry-run: 9/9 types
           rejected at bind, after 1-2 h.

INOUTLINE (FP-CONVERGE-S81 11-25, COORD): WARN INOUTLINE by default, FAIL INOUTLINE when $OT_PRE_INOUTLINE_BLOCK=1 (set for the c11 cut only; a live cut's PRE
  never blocks on it) <type> when a planned coordinate (station regs / bit-site footprints, ft slots, relay sites,
  reach/sink sites, added taps, landing bands, landing-contract collector root / outs / relays / local sources / pins) lies > 1 um outside outline_um.
  With --base only NEW or CHANGED lines block (PRE-DIFF).  Replaces the WARN ADV-IN-OUTLINE / ADV-FT-OUTSIDE lines in this gate.

SITE-OFF-OUTLINE (COORD K10 11-25): FAIL ADV-SITE-OFF-OUTLINE <type>, always blocking: a station site / bit site, relay site, CLAND seat
  (collector local source, reset tap), port pin or clock tap outside outline_um (adv_site_in_macro.off_outline_findings).  The
  ADV-SITE-IN-MACRO advisory no longer WARNs off-outline sites.  KV A5t8: 10 hg o_ectl station regs + kv3_pv_v1e port (GRT-0209 in D29).

PRE-DIFF (COMPOSE-FAST 11-25): `check ... --base BASE [--base-tree T]` fails only on FAIL lines that are NEW (or CHANGED) against the
  same check on BASE; base lines the row repeats are LIST PRE-INHERITED.  The base check runs beside the row check, cached by
  base/as-built/tools sha (pre_diff.py has the rules).  The canonical row gate (row_gate.py) always passes --base.

BIND-SPEED-1118 adds four classes (bind_rowcheck.py; run inside `bind` after the elab, and by `bind_fast.py precheck`):
  FIXEDCYC lane fixed_cycles vs its latency row (double-counted / stale table); ROWSINK R8 table rows whose sink / port is no leaf of
  the elaborated die (names compared in u_r0_u_x instance form too; --elab-dir OUT); MODULES modules named by asbuilt.substitute_inst /
  substitute / sub_core_leaf that exist nowhere; TOOLSTALE tools/die_plan files older than the live tree (--ref-tools, $OT_RT_CURRENT).

TOOLROOT-1123 (COORD 16:1x, FABLE flow review): when an rt sha is declared ($OT_TOOLS_SHA, else the rt/<sha> $OT_RT_CURRENT
  names after rt_pin.py --export), the repo root this PRE runs from must BE that sha (rt/<sha> dir or git HEAD) and hash equal to
  its rt manifest on tools/die_plan + physical/common_flow; else FAIL TOOLROOT (fail closed).  Nothing declared: not checked.
  Gate scripts run the same check standalone: python3 -I <tools>/die_plan/tool_root.py --expect <sha>.

LANDREMAP-1122 (FLOW-OPS-R2, COORD): with --baseline-plan, every type whose hard core (landing cl_*, ectl, any) or clock tap
  table moved against BASE re-solves its reset tree and renumbers rst_rl_<k>.  A landing reset reference (landing_reader_start /
  landing_writer_start / landing_local_resets / landing_raw_branches; collector_tree excluded) that still names, at the same
  plan path, the same relay as BASE while that name is now a DIFFERENT relay (depth, site, kind) of the new tree was not
  remapped: FAIL LANDREMAP with the landing_remap.py command.  KV R6d (ae4b6866747e vs plan_r6c): 7 EMIT errors after a 1-2 h
  bind, refused here in ~3 s.  bind.py runs this class against $OT_PLAN_GATE_BASELINE, else the plan recorded in
  OUT/provenance_bind.json, else in <plan dir>/bind_of_record/provenance_bind.json (the tree's previous bind of record).

ABSPATH-1122 (FLOW-OPS-R2, COORD): an absolute path in the plan json (or its --sidecar, or <plan dir>/wave_prepare.json) that
  lies outside the plan's own tree (--tree, else the nearest parent holding tools/die_plan or physical+rtl; realpath counted)
  is an input that dies with its snapshot (HEAD r16/r17: sink censuses into the deleted s81_head_r4_s0 -> kit_rtl /
  abs_inputs).  ABSPATH-MISSING (target gone) and ABSPATH-OUTSIDE (target present): WARN before ABSPATH_STRICT_FROM (live
  plans keep cutting), FAIL from it; $OT_PLAN_ABSPATH=fail (composers / new plans) or =warn overrides; a bind always warns.
  Keys provenance / source* / note* / comment* / receipt* / evidence* / proof* / report* / history / *_log are records.  Fix: `plan_gate_pre.py localize --plan P --out P2` copies each present outside
  file into <plan dir>/inputs/ and rewrites the reference tree-relative (composers run it before G0).

PIN-REACH-1124 (S81-RSTSOLVE, FABLE-RC-ALL): WARN RSTPIN (report only) per reset.parent_pins entry whose pinned parent is farther than the
  hop (275 um) from the part's reset input.  wf_solve leaves such a part unreachable and attaches it (now nearest-first) to the
  nearest reached part, so one widened box can move a whole chain (c8 step 03: s_2S_x00, 11 parts, fW0_p1_b0 at 7.7 mm).  --skip RSTPIN.

DERIVED-DROP-1123 (PRECHECK-DERIVED-DROP, COORD 21:36 / FABLE-RC-KV): a re-floor, grow or tap rewrite that leaves a DERIVED section
  pointing at the old tree.  RSTREACH: START / local reset raw hops over the edge reach (S81 c7a svc_tap_inv: 2233 um), FSTART
  face flops beyond 405 um of their raw reset (stripped landing_raw_branches, KV pv_v3 -721 ps; branch base relays moved by the KV
  +112 um grow).  DERIVEDNAME: relay / tap names not emitted, landing_raw_branches no longer a D-chain of the re-solved tree (KV
  A3g io_ft_v1 EMIT), dangling consumers / START keys, station ends on removed hard cores.  derived_drop.py (doc there);
  --elab-dir or <plan dir>/bind_of_record decides FSTART face flops; OT_DERIVED_BUDGET_S bounds the tree solves.
  ENTRYFOOT (PRE-QC-GENCHECK 11-23, QC C1-noSU cbn_q00__cl622f65d2: cores + clock_entry_access footprints moved, early taps
  not; strict bind + LATCHECK passed, kit GEN died): each early core tap on a clock_entry_access pin emits exactly the access
  footprint; with a baseline every early core tap follows its moved hard core; every forwarded-clock
  output's source_clock_port tap lies within 300 um of its pin (STALE-EXPORT-TAP, KV A5).  Seconds (S81: 9 min of tap grids).

ISTCYC-1122 (FLOW-OPS-R2, COORD): with --baseline-plan, every lane whose end-bus internal_stations depth (source OUT bus +
  destination IN bus, the deepest bus:<name> row as the kit merges them) changed against BASE, and whose BASE fixed_cycles
  followed the rule fixed_cycles = source + destination, must carry the new source + destination; else FAIL ISTCYC with the
  lane, the depths and the required cycles (the bind refuses it later: native_istations "fixed_cycles must equal source +
  destination").  Only lanes on types whose stations changed are read.  Fix: `plan_gate_pre.py reprice --plan P
  --baseline-plan B --out P2` sets exactly those lanes (fixed_cycles and latency fixed / cycles / natural by the same delta).

DEADIN-1122 (FLOW-OPS-R2, COORD): with an as-built that names dead_input_proofs, the bind's own dead_inputs.ProvenDead
  validation (repository-relative paths, PASS verdict, defines / re-proofs, dependency module hashes, selected source) runs here,
  before the elab: OPUS-FIX-S81-COLROM-R6 kit G lost 28 min of elab to "dead-input proof must be repository-relative".

STNXREF (STATION-MOVE-HELPER 11-24, report-only WARN per r703, no date switch): every station / relay the plan references
  must match across the records derived from it: reset.bank_taps sinks (BANKSINK: removed / renumbered station; BANKFOLLOW: moved
  station on its BASE tap), ft bit_sites_um (BITCOUNT / BITFOLLOW), clock.landing_network edges (LANDPIN; LANDHOP: endpoint moved,
  relays not re-derived; LANDFOLLOW: station 0 vs landing in-pin), latency stage counts (STAGECNT) and name-keyed tap records
  (TAPKEY).  KV C2T io_cor_v1 bank_taps (bind EMIT), S81 D2 60 landing edges (G0).  station_xref.py (doc there); the repair for
  every form is station_move.py move / remove / reseat.  BASE = the remap base.  --skip STNXREF.
LATPKG (STATION-MOVE-HELPER 11-24, COORD / FABLE-RC-ALL 46fa8c69, report-only WARN): every latency package next to the plan
  (<die>_latency.json / <pkg>_lat_pkg.sv in the plan dir, its lat/ r8/ subdirs and the die's lat/ r8/) carries the plan digest it
  was generated from; a digest != gen.plan_digest(bound plan) is WARN LATPKG with the stale value count and the types / tools that
  read it (HEAD w3 prep_r18w3c/lat: a74be4f5, 85 values behind).  The bind runs it through this PRE.  latpkg_check.py; --skip LATPKG.
STNPRICE (STN-REPRICE 11-24, report-only): one LIST line counting lanes whose source OUT + destination IN station depth != fixed_cycles.  Rows that add
  stations are re-priced in the same op set by `stn_reprice.py wrap -- ROW.py PLAN_IN PLAN_OUT` (law-table guard: WARN, --strict refuses unless a regenerated
  table is supplied).
REMAP-BASE-1122 (FLOW-OPS-R2, COORD): LANDREMAP and ISTCYC compare against the remap base, resolved without the lane naming
  it: --remap-base, else --baseline-plan, else $OT_PLAN_REMAP_BASE, else the plan recorded in <plan dir>/bind_of_record/
  provenance_bind.json (the tree's last bind).  publish_gate passes the die's live plan (kit_wave.json), ot_build passes its
  --remap-base / the same fallback, private-spec the wave plan it forks from.  The base used is printed as a WARN-free LIST line.

R8STALE-1122 (FLOW-OPS-R2, COORD; FAM-KV-IOPC-R4 pc_v3: +5 stations on 32 pi bundles, reprice ran, 3 strict binds then died at
  R8_FAIL_FAST with 30 R8_STALE): with a remap base, every lane whose end-bus station depth changed against the base is looked up
  in the as-built's R8 tables (land_r8 + land_r8_extra, member "lane").  A table that is byte-identical to the base tree's copy
  (same tree-relative path) was not re-derived after the change: FAIL R8STALE with the members and the regeneration recipe (one
  strict bind stops at R8_FAIL_FAST and writes OUT/r8_derived.json; install it, or r8_refresh.py, then bind).  Base copy not found:
  WARN with the same recipe.

R8BOUND-1124 (COORD flow review #2, report-only WARN per r703): every DIRECT R8 table member (its lane runs from its src_part to its
  sink_part) must carry bound == the plan's latency.lanes[<lane>].cycles (the bind's bound depth); a mismatch is a strict-bind
  R8_STALE found in seconds instead of after a 1-3 h bind (C1m: 6 dvs_E*.so_w flt members, table 2, plan 4).  check_r8bound.

ABSTRACT-BLANKET-OBS (ABSTRACT-EXACT 11-25, COORD; report-only WARN per r703): every bound hard-core view (partition_types.*.hard_cores
[].lef, generated memory macros skipped) whose M4/M5/M6 OBS is one blanket rect over >= 80 % of the macro (write_abstract_lef
-bloat_occupied_layers) gets a WARN line naming the layers; LIST line with the count.  Fix: tools/die_plan/abstract_exact.py form.
TAPREACH (C-TAP-REACH, QC-INT-R2-TOOLS 11-26; report-only WARN, FAIL with $OT_PRE_TAPREACH_BLOCK=1): every FIRM relay / station / landing / clock-sink
  seat of a type lies within clock.tap_radius_um (Manhattan, as taps.assign) of some tap of its type.  QC cA4 coll_ft east relay column
  x=655.  tap_reach.py (doc there; `tap_reach.py census PLAN`).  --skip TAPREACH.
STALETABLE (P-STALE-TABLE, QC-INT-R2-TOOLS 11-26; ADVISORY WARN, FAIL with $OT_PRE_STALETABLE_BLOCK=1): tables derived from a row are re-derived
  and compared: tap_window / tap_offset per_port_ps keys vs the type's tap ports, or_groups[0].regs_um vs the row's regs_um, explicit /
  added taps legal against macros, relay_sites vs station bit_sites_um.  stale_tables.py (fix-orgroups re-derives the or_groups form).  --skip STALETABLE.
HALOCORNER-1125 (COORD, QC-ALLFIX; FLOW-OPS-R3 DIEPLAN-GREEN 11-24 23:33; report-only WARN per r703): reset_tree._free bounds its
  row-high / cell-wide free runs only by halos the point is strictly inside in x or y, so a point on a SHARED corner of 2+ grown
  halos (reset_tree.blockages) has unbounded runs and is called a legal relay site (q_su31: four halos meet at (825.12, 816.48)).
  Every planned relay site (type relay_sites), published reset-tree node (collector_tree root / start_in / relays / outs) and
  reset.in_sites entry that touches 2+ halos at a corner of one of them, in no halo interior, with no run under inclusive face
  contact, is listed per type.  _free is unchanged (bound trees keep their sites); the sites move in plan rows.  --skip HALOCORNER.

CABIND-1125 (QC-CA-PRECHK, COORD; C1n-r2 plan a372ae84fa2a vs sidecar 0391a5add8e7: 36 of 60 relay parts mismatch): FAIL when --sidecar is
  given and its count_aligned disagrees with the plan where the bind does.  Per relay part: stages == count_align_bind.RELAY_STAGES + tx
  stages of the origin's type + rx stages of its own type (count_align_bind.relay_extra_from_plan; the clock_landings relay-role check),
  EVERY mismatch listed with a part table (the bind stops at the first).  Also: plan count_aligned_cycles == sidecar sched_lat per port,
  plan count_aligned_bind == sidecar schema/root/pad/root_settle_cycles, landing_output_qreg == port output_qreg, FREG declaration
  (clock_landings.check_ca_freg_declared), one origin per region == regions.origin_part.  Not covered (needs a bind): K / n_nominal
  frames (count_align_bind.bind_parts), ring depths, port endpoints vs regions.  --skip CABIND.

TAPOFF-1123 (TAP-GRID-R5, COORD class ruling; KV x10): a type with a plan clock.tap_offset.per_port_ps row (R-CLOCK-7)
  times every tap port at its row; a port with no row silently takes the window [-W, 0].  Every tap of such a type
  (schema.tap_grid, core clk_c* ports aside) must have a row: FAIL TAPOFF-MISSING per type with the missing ports and the fix
  (tools/die_plan/tap_offset_fill.py fill: the nearest listed tap's row; tap_split writes it in the same step as an append).
  TAPOFF-ALL (TAP-GRID-R6 11-23): the check is tap_offset_cover.census, so it reads every tap mode (density, grid,
  grid+explicit, explicit) and the window form (clock.tap_window.per_port_ps rows); a type whose tap grid does not solve
  still FAILs on its added taps named without a row (else WARN TAPOFF-UNCHECKED).  Fix: tap_offset_cover.py fill.

TAPNAME-1122 (FLOW-OPS-R2, COORD): for every clock.tap_mode "density" type with clock.added_taps, the density base is solved
  exactly as the bind does (taps._density_base) and the added names must be clk_t<base>, clk_t<base+1>, ... in order (cbf_q00
  clk_t101 for t114, coll_core clk_t130 for t126: EMIT "density added tap names/order must be ..." after 30+ min of bind).
  FAIL TAPNAME names each wrong name and its expected one.  A clock-section reference to a clk_t<k> that is no tap of the
  type (k >= base + added), or to a misnamed added tap, is FAIL TAPNAME-RETAP: the reset tree / consumer sites still carry
  old tap indices; re-run the tap package (retap.py) on the solved base.

ANCHORDRY-1123 (RESET-ANCHOR-TAPGUARD-1123, COORD; S81 J9 slice C c1x_C t1/t10/t7, iq_C t1, lepe_nh_mus_C t1): a type's
  clock.reset_tree_anchor names relays at the depth the bind will keep (resolve() re-picks only at the anchored depth).  For every
  START / local-reset reference path the anchored depth is compared with the depth the remap base (REMAP-BASE-1122) anchors at
  the same path (its anchor, else its published collector_tree): a different depth is FAIL ANCHORDRY (`reset_anchor record
  --source tree` after a tap row re-anchored renumbered names: EMIT 'release edge would move').  Without a base depth the plan's
  own collector_tree is compared, WARN ANCHORDRY-ADVISORY only.  $OT_ANCHORDRY_SOLVE=1 also dry-runs the bind's resolve() on the
  solved reset trees (anchor_dry.py; slow on wavefront dies): refusals / re-picks are WARN ANCHORDRY-ADVISORY.  Seconds by default.

GENDRY-1123 (COORD 17:25, FABLE flow review; HEAD E pin-move row cab67: every gate green, then kit GEN crashed at
  clock_landings.py:1808 "writer START raw reset rst_rl_334 has no registered wavefront driver"): every partition type whose
  plan entry differs from the --baseline-plan runs the kit generator dry (gen.py phys --types T --trial, tools of this PRE,
  --rtl-root TREE, --clock-landing SIDECAR or <plan dir>/source_sidecar.json) into a temp dir; rc != 0 is FAIL GENDRY with the
  generator's error line.  $OT_PRE_GENDRY_TYPES=T1,T2 names the types (also without a baseline); at most $OT_PRE_GENDRY_MAX
  (24) types, $OT_PRE_GENDRY_J (8) in parallel, $OT_PRE_GENDRY_TIMEOUT_S (1800) each; the rest are WARN GENDRY-UNCHECKED.
  No baseline and no list: not run.  The plan_gate_pre CLI runs it by default ($OT_PRE_GENDRY=0 or --skip GENDRY: off);
  library callers pass gendry=True.  Minutes.
  GENDRY-KITRTL-1123 (KV-ALLFIX A3e/A3d: 24/24 kv3_hg*/hgi*/hroot FAIL GENDRY "bus o_ectl_Q_N_eN is not bound to any leaf
  port"): a KIT-RTL type = a type with buses none of which carries a bus.leaf and no contents[].bind (a bind-mode plan, all
  KV types).  The generated plan wrapper can never build it; the real kit builds it from the bound RTL (kit_wave: bind.py
  kit-rtl -> gen.py phys --kit-rtl T=kit_rtl.f).  PRE does the same when --elab-dir names a finished bind OUT (bind_report.json, no errors):
  bind.py kit-rtl (this PRE's tools, --src-tree TREE, --asbuilt) into the temp dir, then the dry gen with --kit-rtl; a
  failure of either step is FAIL GENDRY.  Without a bind OUT (PRE runs before / beside the bind) such a type is not generated
  and is WARN GENDRY-KITRTL (classified, never FAIL); every type with any leaf binding is checked exactly as before.
  GENDRY-PADBIND-1124 (QC C1g GENDRY: glue FAIL "pad bump_bump_fwd_epoch_pad_i must bind a leaf port: None"): a type with a
  pad that no contents[].bind names is also KIT-RTL.  Such a pad is bound only in the bound RTL (QC glue: contents[].bump_ports
  of u_bump_fwd_epoch / u_bump_fwd_lrst, bound by bind.py); the plan wrapper can never bind it, the wave kit (kit_rtl mode bind)
  never builds it that way.
  GENDRY-STOPITER-1124 (KV-OWN-HUB-R2): the dry gen takes --clock-landing like the wave: --sidecar, else the as-built's
  clock_landing_table, else <plan dir>/source_sidecar.json.  A generator stop LANDING-SOURCE-UNMODELED (landing_place: a local
  source with no relay in the collector tree the run holds) is WARN GENDRY-UNMODELED, never FAIL.

SITEGRID-1123 (ADV-SITEGRID-1123, FLOW-OPS-R3, COORD 16:1x; KV D29 HGFORM: 70,200 kv3_hg* o_ectl_Q_N_tN exact bank seats off
  the native lattice, found only at global_place): every exact bank site the kit places verbatim (internal_stations
  bit_sites_um / face_bit_sites_um, clock.soft_reg_banks bit_sites_um) must satisfy the kit's own predicate in integer DBU
  (site_grid.py: round(x * dbu) - core_x0 a multiple of the 0.054 site, round(y * dbu) - core_y0 a row origin, CORE_AREA =
  kit_fit.kit_core_area): else FAIL SITEGRID per type with the count, bank rows, examples and the nearest legal origin.  Macro
  origins (origin + track_offset) off the manufacturing grid are WARN SITEGRID-MACRO; off the site column / row and plan cell
  hints the kit legalises are counted in WARN SITEGRID-SUMMARY only (adopted kits place with them).  Seconds.

SEATMATCH-1124 (SEAT-MATCH-AUDIT): with a finished bind OUT of this plan (--elab-dir), every relay_sites key is judged against the bound
  RTL text (seat_match.py: instance present, stage / bit inside the primitive's W, D / DMAX, no '/' vs '.' twin at another site).  A key that
  seats nothing leaves its live register in free placement (QC sle_ctl 16,442 of 70,623 keys).  WARN only (REPORT-ONLY until the re-keys
  land, COORD / FABLE-RC-QC 11-24): group counts, the strap bank the rows moved to, and how many are NEW against the baseline.  Seconds.

ISTPRICE (FABLE FLOW REVIEW 11-23 22:50, PRECHECK-LEDGER-R3): FAIL for every lane whose stored latency row is short of the live counts
  (PRICE-SHORT: cycles < 2 + ft stations + landing + source stations; STALE-TABLE: stored ft stations / landing != live) and, with an
  as-built, every native-source lane whose fixed_cycles != source + destination stations + the receiver's declared soft_latency.in
  cycles, counted once (FIXED-SPLIT; PRE-PRICE-ONCE-1125) or whose native source bus has
  != 1 outgoing lane (OUT-LANES): the strict bind dies on these in build_buses / native_istations 35-60 min later (S81 c8 dn_s_3N_L3
  fixed_cycles 10 != 8 + 1; KV A3c / A2f).  Passes only at 0 flagged lanes.  NOT skippable (--skip ISTPRICE is ignored and said so).
  As-built: --asbuilt, else the plan's own `asbuilt` section, else <plan dir>/{plan_of_record/native_bind,plan_inputs/run}/asbuilt_run*.json, else the same under <tree>/physical/die_plan/*/
  (the newest); none found = FAIL ISTPRICE (the native rules cannot be judged), never a silent pass.  tools/die_plan/adv_ist_price.py.
TREEPRE (PRE-SCHEMA-KEYS 11-24, S81-ALLFIX-INT / COORD): tree_precheck.py runs first: SCHEMA-KEYS (plan keys vs the bind tree AND the
  launch rt schema.py), TREE-SOURCES (as-built / bind.f paths and *_sources/ folders in the tree), TREE-FRESH (.fork.json vs the source's
  current seal).  WARN / LIST lines only (r703); bind.py runs it before its elab and sets OT_TREE_PRECHECK_RAN=1, which skips it here.
PRE-INPUT-STOP-1124 (COORD; FAM-S81-COL-H9R0 3.5 h PRE then INPUT-MISSING): TREEPRE, SCHEMA and INPUT run first, in seconds; a missing
  input (FAIL INPUT-MISSING / SCHEMA-UNKNOWN-KEY / SCHEMA-LOAD, a TREE-SOURCES path line) ends the check there with LIST PRE-INPUT-STOP
  (FAIL PRE-INPUT-STOP when only a TREE-SOURCES line triggered it), before the slow classes ($OT_PRE_INPUT_STOP=0: run them anyway).  PRE-TIME-1124: LIST PRE-TIME names the seconds per class; a class
  over $OT_PRE_TIME_TRACE_S (30) prints PRE-TIME to stderr when it ends.
RESET-TREE-CACHE-1124 (COORD; S81 c8 PRE profile: LANDREMAP 960 s): after the input stop, reset_solve_types() takes the union of the
  reset trees LANDREMAP (+ its re-pick), RESETPUB / ANCHORDRY (solve modes), RSTREACH / DERIVEDNAME would solve, from each class's own
  selection, and reset_prewarm() solves them once in a fork pool (reset_tree.prewarm: cores / $OT_RUN_THREADS / free memory) into
  reset_tree's process-wide cache, which every class reads.  LIST RESET-PREWARM / RESET-TREE-CACHE name the work and any read the
  prewarm missed or solve no class read.  OT_PRE_RESET_PREWARM=0 skips the prewarm; OT_RESET_TREE_CACHE=0 turns the cache off.
ADVISORY (PRECHECK-R2, COORD 11-22; owner 11-19: an estimator, never a gate): plan_advisory.py's static checks (CORE-PARAM,
  GHOST-MACRO, SITE-COLLIDE, PORT-WINDOW-PAIR, DEPTH-VS-RTL, DENSITY, TAP-BUDGET, TAP-LOAD, ... BANK-OFFAREA) run on every check and add WARN ADV-<CHECK>
  lines only: they never change the verdict or the exit code.  They print with --quiet too and go to --json "advisories".
  --skip ADVISORY or OT_PLAN_ADVISORY=off leaves them out.

COMPOSEDROP (COMPOSE-GUARD-1124, QC-COMPOSE-GUARD / COORD 11-24; QC C1k lost the QC-OPEN-STA r10 st_a row): with --baseline-plan
  (the previous event's plan), every plan path the baseline carries and this plan lacks or holds null (dict keys; list elements with a
  unique name / conn / inst / id) is listed by group: compose_drop_guard.py.  WARN only (r703 report-only); OT_COMPOSE_DROP=fail makes
  it a FAIL; $OT_COMPOSE_DROP_LIST names the intended drops (fnmatch patterns over the dotted path).  Reverts to an older plan and lost
  private rows need the full tool: compose_drop_guard.py PREV NEW --history OLDER... --row NAME=BASE:ROW --drop-list FILE (rc 1).
Exit 0 = clean, 1 = at least one FAIL, 2 = usage / unreadable input.  Library: check(...) returns (findings, info).
"""
import argparse
import ast
import hashlib
import json
import math
import time
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

PROOF_SCHEMA = "opentallas.rows_proof.v1"
ROWS_KEY = "consumer_localization"
LIST_KEYS = ("files", "prefer", "netlist", "rtl_roots", "hard_params")
CLASSES = ("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM", "KITFIT", "FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "LANDREMAP", "ABSPATH", "ISTCYC", "DEADIN", "TAPNAME", "R8STALE", "RELAYSINK", "EMITNAME", "RESETPUB", "MACROGHOST", "SEATMATCH", "ANCHORDRY", "TOOLROOT", "SITEGRID", "GENDRY", "DEPTH", "RSTREACH", "DERIVEDNAME", "ENTRYFOOT", "ISTPRICE", "RSTPIN", "RSTNAMES", "STNXREF", "LATPKG", "TREEPRE", "ADVISORY", "COMPOSEDROP", "FTSITE", "R8BOUND", "HALOCORNER", "MONLEG", "STRAPREACH", "CABIND", "INOUTLINE", "SITE-OFF-OUTLINE", "TAPREACH", "STALETABLE", "VIEWOBS")
# GEOM scope.  Stations of the adopted plans already lie over planned cores (KV 7u: 335 sites over head/pvg cores; S81 B6gE 51,
# QC S4q7e 24: through-stations over native / lane cores), and G0 accepts them, so a plain "no site inside any core" would refuse
# every adopted plan.  Default: refuse the overlaps with the landing ring cores the ring split adds (instance name cl_*), the
# class G0 missed on 7w+v21.  --baseline-plan BASE: refuse every overlap that BASE does not already have (new = refused, same
# type + site + core = inherited).  --strict-cores: refuse every overlap.  The rest is counted in one WARN line.
REFUSE_CORES = r"^cl_"


def _load(p):
    return json.loads(Path(p).read_text())


# RESETPUB-SOLVE-DEFAULT-1125 (COORD / FABLE-RC-QC 19:45): the QC C1p R6 gate passed only because the caller exported OT_RESETPUB_SOLVE=1,
# so a rebind or a re-run without it was not reproducible.  The solve is now the default for the dies listed here (PRE, the bind's PRE and
# the publish gate all decide through this rule); OT_RESETPUB_SOLVE=1 / =0 still forces it on / off for any die.
RESETPUB_SOLVE_DIES = ("qwen_compute",)


def plan_die(plan):
    """-> the die a plan belongs to: <...>/die_plan/<die>/... in its path, else its top-level "die" key, else ''"""
    parts = Path(str(plan)).parts
    for i, x in enumerate(parts[:-1]):
        if x == "die_plan" and i + 2 < len(parts):
            return parts[i + 1]
    try:
        return str(_load(plan).get("die") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def resetpub_solve(plan, env=None):
    """True when RESETPUB solves every localized type: OT_RESETPUB_SOLVE=1 / =0 decides; unset = on for RESETPUB_SOLVE_DIES"""
    env = os.environ if env is None else env
    v = str(env.get("OT_RESETPUB_SOLVE", "")).strip()
    if v in ("0", "1"):
        return v == "1"
    return plan_die(plan) in RESETPUB_SOLVE_DIES


def _canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- SCHEMA
_SCHEMA_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import schema
mode = sys.argv[2]
if mode == "validate":
    obj = json.load(open(sys.argv[3]))
    print(json.dumps({"errors": schema.validate_structure(obj)}))
elif mode == "keys":
    out = set()
    def walk(s, path):
        if not isinstance(s, dict):
            return
        for k, v in (s.get("properties") or {}).items():
            out.add(path + "." + k)
            walk(v, path + "." + k)
        if isinstance(s.get("additionalProperties"), dict):
            walk(s["additionalProperties"], path + ".*")
        if isinstance(s.get("items"), dict):
            walk(s["items"], path + "[]")
    walk(schema.SCHEMA, "$")
    dump = json.dumps(schema.SCHEMA, indent=1) + "\n"
    print(json.dumps({"keys": sorted(out), "dump": dump if len(sys.argv) > 3 else None}))
"""


PROBE_BASE_S = 180          # one schema import + validate of a small plan on an idle host
PROBE_S_PER_MB = 20         # validate time grows with the plan file (S81 plan ~100+ MB)


def probe_timeout(plan=None, env=None, load=None, ncpu=None):
    """S81-DIE-R3 11-19 (COORD): the schema probe timeout, never a fixed 180 s.  OT_PLAN_GATE_PRE_PROBE_S (> 0) wins;
    otherwise (180 s + 20 s per MB of the plan) x max(1, 1-min load / cpus), so a big plan on a host at load 290/96
    (epyc8, D8i C6 r10 'schema probe timed out') gets the time the work needs instead of a false SCHEMA-LOAD FAIL."""
    env = os.environ if env is None else env
    try:
        v = float(env.get("OT_PLAN_GATE_PRE_PROBE_S") or 0)
    except ValueError:
        v = 0
    if v > 0:
        return v
    mb = 0.0
    if plan:
        try:
            mb = os.path.getsize(plan) / 1e6
        except OSError:
            mb = 0.0
    if load is None:
        try:
            load = os.getloadavg()[0]
        except OSError:
            load = 0.0
    ncpu = ncpu or os.cpu_count() or 1
    return (PROBE_BASE_S + PROBE_S_PER_MB * mb) * max(1.0, load / ncpu)


def _probe(tree, *args, timeout=None):
    if timeout is None:
        plan = next((a for a in args if isinstance(a, (str, Path)) and str(a).endswith(".json") and os.path.isfile(a)), None)
        timeout = probe_timeout(plan)
    sd = Path(tree) / "tools" / "die_plan"
    if not (sd / "schema.py").is_file():
        return None, f"{sd}/schema.py does not exist"
    try:
        r = subprocess.run([sys.executable, "-I", "-B", "-c", _SCHEMA_PROBE, str(sd), *map(str, args)],
                           capture_output=True, text=True, timeout=timeout, cwd=str(tree))
    except subprocess.TimeoutExpired:
        return None, f"schema probe timed out ({timeout:.0f} s; OT_PLAN_GATE_PRE_PROBE_S overrides)"
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["?"])[-1]
        return None, f"schema.py of the bind tree does not import: {tail}"
    return json.loads(r.stdout), None


def check_schema(tree, plan, compose_tree=None):
    out = []
    res, err = _probe(tree, "validate", plan)
    if err:
        return [f"FAIL SCHEMA-LOAD {err}"]
    errs = res["errors"]
    unk = {}
    other = []
    for e in errs:
        m = re.search(r"unknown key '([^']+)'", e)
        if m:
            unk.setdefault(m.group(1), []).append(e)
        else:
            other.append(e)
    for k, es in sorted(unk.items()):
        out.append(f"FAIL SCHEMA-UNKNOWN-KEY '{k}' x{len(es)} not in {tree}/tools/die_plan/schema.py (first: {es[0]}); "
                   f"the plan comes from a newer schema than this bind tree (overlay/tool mismatch)")
    for e in other[:5]:
        out.append(f"FAIL SCHEMA-INVALID {e}")
    if len(other) > 5:
        out.append(f"FAIL SCHEMA-INVALID ... and {len(other) - 5} more")
    kres, kerr = _probe(tree, "keys", "dump")
    if not kerr:
        jf = Path(tree) / "tools" / "die_plan" / "die_plan.schema.json"
        if jf.is_file() and jf.read_text() != kres["dump"]:
            out.append(f"WARN SCHEMA-JSON-STALE {jf} differs from the dump of {tree}/tools/die_plan/schema.py "
                       f"(re-dump: python3 -I tools/die_plan/schema.py dump-schema)")
        if compose_tree:
            cres, cerr = _probe(compose_tree, "keys")
            if cerr:
                out.append(f"FAIL SCHEMA-LOAD compose tree: {cerr}")
            else:
                miss = sorted(set(cres["keys"]) - set(kres["keys"]))
                if miss:
                    out.append(f"FAIL SCHEMA-TREE-SKEW {len(miss)} schema properties of the compose tree {compose_tree} "
                               f"are missing in the bind tree {tree}: {', '.join(miss[:8])}"
                               f"{' ...' if len(miss) > 8 else ''}")
    return out


# ---------------------------------------------------------------- INPUT
def manifest_paths(ab, manifest_dir, tree):
    """[(key, resolved Path, kind)] for one as-built section, resolved as tools/die_plan/bind.py does."""
    tree, manifest_dir = Path(tree), Path(manifest_dir)
    b = ab.get("base")
    if b is None:
        base = tree
    elif Path(b).is_absolute():
        base = Path(b)
    else:
        base = manifest_dir / b
    res = []

    def add(key, p, rel_to, kind="file"):
        if not isinstance(p, str) or not p:
            return
        q = Path(p) if Path(p).is_absolute() else Path(rel_to) / p
        res.append((key, q, kind))

    for k in LIST_KEYS:
        v = ab.get(k) or []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            continue
        for p in v:
            add(k, p, base, "dir" if k == "rtl_roots" else "file")
    add("map_file", ab.get("map_file"), manifest_dir)
    add("clock_landing_table", ab.get("clock_landing_table"), base)
    for k in ("dead_input_reproofs", "dead_input_proofs"):
        v = ab.get(k)
        if isinstance(v, str):
            v = [v]
        if isinstance(v, list):
            for p in v:
                add(k, p, tree)
    pr = ab.get("param_regen")
    if isinstance(pr, dict):
        add("param_regen", pr.get("file"), tree)
    return base, res


def check_bind_assets(raw, tree, plan, types=None):
    """Bind reads clock inventory. Physical kit generation checks guides separately."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import plan_file_inputs
    return [f"FAIL INPUT-MISSING plan asset {issue}"
            for issue in plan_file_inputs.missing(raw, plan, Path(tree), guide_types=set(), bin_types=types)]


def check_inputs(tree, plan, sidecar=None, asbuilt=None, want_list=False, require_asbuilt=False):
    out = []
    listing = []
    for what, p in (("plan", plan), ("sidecar", sidecar)):
        if p and not Path(p).is_file():
            out.append(f"FAIL INPUT-MISSING {what} {p}")
    raw = _load(plan)
    out += check_bind_assets(raw, tree, plan, _SCOPE)
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).resolve().parent
    else:
        ab, mdir = raw.get("asbuilt"), Path(plan).resolve().parent
    if not isinstance(ab, dict):
        lvl = "FAIL" if require_asbuilt else "WARN"
        return out + [f"{lvl} INPUT-NO-ASBUILT {plan} has no `asbuilt` section and no --asbuilt manifest: no bind inputs to check"]
    base, paths = manifest_paths(ab, mdir, tree)
    if not base.is_dir():
        out.append(f"FAIL INPUT-MISSING base {base}")
    miss = {}
    for key, p, kind in paths:
        listing.append(str(p))
        ok = p.is_dir() if kind == "dir" else p.exists()
        if ok and p.is_symlink() and not p.exists():
            ok = False
        if not ok:
            miss.setdefault(key, []).append(str(p))
    for key, ps in sorted(miss.items()):
        out.append(f"FAIL INPUT-MISSING {key} x{len(ps)} (base {base}): " + "; ".join(ps[:4])
                   + (f"; ... +{len(ps) - 4}" if len(ps) > 4 else ""))
    if want_list:
        out.append("LIST " + json.dumps(sorted(set(listing))))
    return out


# ---------------------------------------------------------------- TOOLS
class _Mod:
    def __init__(self, name, path):
        self.name, self.path = name, path
        self.any = False          # exports unknowable (star import / __getattr__)
        self.names = {}           # name -> FunctionDef | None
        self.dups = set()
        self.tree = None
        self.error = None
        try:
            warnings.simplefilter("ignore")
            self.tree = ast.parse(Path(path).read_text(errors="replace"), filename=str(path))
        except SyntaxError as e:
            self.error = f"{path}:{e.lineno}: {e.msg}"
            return
        self._scan(self.tree.body)

    def _define(self, n, fn=None):
        if n in self.names:
            self.dups.add(n)
        self.names[n] = fn

    def _scan(self, body):
        for s in body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if s.name == "__getattr__":
                    self.any = True
                self._define(s.name, s if not s.decorator_list else None)
            elif isinstance(s, ast.ClassDef):
                self._define(s.name)
            elif isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                tg = s.targets if isinstance(s, ast.Assign) else [s.target]
                for t in tg:
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            self._define(x.id)
            elif isinstance(s, (ast.Import, ast.ImportFrom)):
                for a in s.names:
                    if a.name == "*":
                        self.any = True
                    else:
                        self._define((a.asname or a.name).split(".")[0])
            elif isinstance(s, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
                for f in ("body", "orelse", "finalbody", "handlers"):
                    for sub in getattr(s, f, []) or []:
                        self._scan(sub.body if isinstance(sub, ast.ExceptHandler) else [sub])
            if isinstance(s, (ast.Global,)):
                pass

    def has(self, n):
        return self.any or n in self.names


def _arity_error(fn, call):
    """None, or why `call` cannot bind to FunctionDef `fn` (only when every argument is plain)."""
    if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
        return None
    a = fn.args
    pos = [x.arg for x in a.posonlyargs + a.args]
    kwonly = [x.arg for x in a.kwonlyargs]
    ndef = len(a.defaults)
    required = pos[:len(pos) - ndef] if ndef else list(pos)
    kwreq = [x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    npos = len(call.args)
    if npos > len(pos) and not a.vararg:
        return f"{npos} positional arguments, def takes {len(pos)}"
    names = {k.arg for k in call.keywords}
    for k in names:
        if k not in pos and k not in kwonly and not a.kwarg:
            return f"unexpected keyword '{k}'"
        if k in pos[:npos]:
            return f"'{k}' given twice"
    miss = [r for r in required[npos:] if r not in names] + [r for r in kwreq if r not in names]
    if miss:
        return f"missing {', '.join(miss)} (def takes {len(pos)} positional)"
    return None


def check_tools(tree, max_findings=12):
    d = Path(tree) / "tools" / "die_plan"
    if not d.is_dir():
        return [f"FAIL TOOLS-LOAD {d} does not exist"]
    mods = {}
    for p in sorted(d.glob("*.py")):
        if p.is_file() and not p.stem.startswith("test_") and p.stem != "conftest":
            mods[p.stem] = _Mod(p.stem, p)
    out = []
    for m in mods.values():
        if m.error:
            out.append(f"FAIL TOOLS-SYNTAX {m.error}")
    found = []
    all_mods = mods
    extra_cache = {}
    for m in all_mods.values():
        if m.tree is None or m.name.startswith("test_") or m.name == "conftest":
            continue
        # a module that does sys.path.insert(0, <here>/"X") imports X's modules first (ca_region_table -> tools/s81_head/fallback_land.py):
        # resolve those names in tools/X, not in the same-named sibling of tools/die_plan (a checker false positive on KV 7u/7uh)
        mods = dict(all_mods)
        try:
            src = m.path.read_text()
        except (OSError, AttributeError, UnicodeDecodeError):
            src = ""
        for xd in re.findall(r"sys\.path\.insert\(\s*\d+\s*,[^\n]*?[\"']([A-Za-z0-9_]+)[\"']\s*\)", src):
            xdir = Path(tree) / "tools" / xd
            if xdir.is_dir() and xd != "die_plan":
                for xp in xdir.glob("*.py"):
                    if xp.stem in mods and not xp.stem.startswith("test_"):
                        key = str(xp)
                        extra_cache.setdefault(key, _Mod(xp.stem, xp))
                        mods[xp.stem] = extra_cache[key]
        alias = {}                  # local name -> sibling module name
        multi = set()               # local names bound to more than one module (function-local imports)
        frm = {}                    # local name -> (module, name)
        for n in ast.walk(m.tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    parts = a.name.split(".")
                    tgt = parts[-1] if (len(parts) == 1 or parts[-2] == "die_plan") else None
                    if tgt in mods and tgt != m.name and (a.asname or len(parts) == 1):
                        if alias.get(a.asname or a.name, tgt) != tgt:
                            multi.add(a.asname or a.name)
                        alias[a.asname or a.name] = tgt
            elif isinstance(n, ast.ImportFrom):
                mod = (n.module or "")
                last = mod.split(".")[-1] if mod else ""
                pkg = (n.level > 0 and not mod) or mod.endswith("die_plan")
                if pkg:
                    for a in n.names:
                        if a.name in mods and a.name != m.name:
                            if alias.get(a.asname or a.name, a.name) != a.name:
                                multi.add(a.asname or a.name)
                            alias[a.asname or a.name] = a.name
                elif (n.level > 0 or mod == last) and last in mods and last != m.name:
                    for a in n.names:
                        if a.name == "*" or (a.name.startswith("__") and a.name.endswith("__")):
                            continue
                        tm = mods[last]
                        if tm.tree is not None and not tm.has(a.name) and not (d / f"{a.name}.py").is_file():
                            found.append(f"{m.name}.py:{n.lineno} `from {mod} import {a.name}`: {last}.py has no {a.name}")
                        frm[a.asname or a.name] = (last, a.name)
        # a local name that is also assigned / a parameter / a loop target anywhere is not (only) the module
        rebound = {x.id for x in ast.walk(m.tree) if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del))}
        rebound |= {x.arg for x in ast.walk(m.tree) if isinstance(x, ast.arg)}
        guarded = set()            # hasattr(X, "name") / getattr(X, "name", d): the module may legitimately lack it
        for x in ast.walk(m.tree):
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in ("hasattr", "getattr") \
                    and len(x.args) >= 2 and isinstance(x.args[0], ast.Name) and isinstance(x.args[1], ast.Constant):
                guarded.add((x.args[0].id, x.args[1].value))
        for r in rebound | multi:
            alias.pop(r, None)
            frm.pop(r, None)
        for n in ast.walk(m.tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias \
                    and not (n.attr.startswith("__") and n.attr.endswith("__")) and (n.value.id, n.attr) not in guarded:
                tm = mods[alias[n.value.id]]
                if tm.tree is not None and not tm.has(n.attr):
                    found.append(f"{m.name}.py:{n.lineno} {tm.name}.{n.attr}: {tm.name}.py has no {n.attr}")
            if isinstance(n, ast.Call):
                tgt = None
                f = n.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in alias:
                    tgt = (alias[f.value.id], f.attr)
                elif isinstance(f, ast.Name) and f.id in frm:
                    tgt = frm[f.id]
                if tgt:
                    tm = mods[tgt[0]]
                    fn = tm.names.get(tgt[1]) if tm.tree is not None and tgt[1] not in tm.dups else None
                    if fn is not None:
                        why = _arity_error(fn, n)
                        if why:
                            found.append(f"{m.name}.py:{n.lineno} {tm.name}.{tgt[1]}(...): {why} "
                                         f"(def {tm.name}.py:{fn.lineno})")
    for f in found[:max_findings]:
        out.append(f"FAIL TOOLS-SKEW {f}")
    if len(found) > max_findings:
        out.append(f"FAIL TOOLS-SKEW ... and {len(found) - max_findings} more")
    return out


# ---------------------------------------------------------------- ROWS
def _find_rows(node, path=""):
    """{path: rows} for every non-empty ROWS_KEY below node."""
    got = {}
    if isinstance(node, dict):
        for k, v in node.items():
            if k == ROWS_KEY and v:
                got[f"{path}.{k}"] = v
            else:
                got.update(_find_rows(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            got.update(_find_rows(v, f"{path}[{i}]"))
    return got


def plan_rows(plan_raw):
    """{partition type: sha of its rows} for rows carried in partition_types."""
    out = {}
    for t, v in (plan_raw.get("partition_types") or {}).items():
        rows = _find_rows(v)
        if rows:
            out[t] = _canon_sha(rows)
    return out


def delta_rows(plan_raw, base_raw=None):
    cur = plan_rows(plan_raw)
    base = plan_rows(base_raw) if base_raw else {}
    return {t: s for t, s in cur.items() if base.get(t) != s}


def check_rows(plan, baseline=None, proofs=(), rows_files=()):
    out = []
    raw = _load(plan)
    need = delta_rows(raw, _load(baseline) if baseline else None)
    good, bad = {}, []
    for pf in proofs:
        try:
            pr = _load(pf)
        except (OSError, ValueError) as e:
            out.append(f"FAIL ROWS-PROOF-UNREADABLE {pf}: {e}")
            continue
        if pr.get("schema") != PROOF_SCHEMA:
            out.append(f"FAIL ROWS-PROOF-SCHEMA {pf}: schema {pr.get('schema')!r}, need {PROOF_SCHEMA}")
            continue
        if pr.get("result") != "pass":
            bad.append((pf, pr.get("result"), pr.get("lane")))
            for t in (pr.get("types") or {}):
                good.pop(t, None)
                bad.append((t, "withdrawn/failed proof", pr.get("lane")))
            continue
        for t, s in (pr.get("types") or {}).items():
            good[t] = (s, pr.get("lane"), pf)
    bad_types = {b[0] for b in bad}
    for pf, res, lane in bad:
        if pf not in need:
            out.append(f"FAIL ROWS-PROOF-NOT-PASS {pf}: result {res!r} (lane {lane})")
    nop, stale = [], []
    for t, s in sorted(need.items()):
        if t in bad_types:
            nop.append(t)
        elif t not in good:
            nop.append(t)
        elif good[t][0] != s:
            stale.append(t)
    if nop:
        out.append(f"FAIL ROWS-NO-PROOF {len(nop)} partition types carry {ROWS_KEY} rows that differ from the baseline "
                   f"and have no passing ROWS-PROOF (dry-run of the consumer check on the EMITTED bind RTL): "
                   + ", ".join(nop[:6]) + (f", ... +{len(nop) - 6}" if len(nop) > 6 else ""))
    if stale:
        out.append(f"FAIL ROWS-PROOF-STALE {len(stale)} types: proof sha differs from the plan's rows (rows changed after "
                   f"the dry-run): " + ", ".join(stale[:6]))
    for rf in rows_files:
        rp = Path(rf)
        if not rp.is_file():
            out.append(f"FAIL ROWS-MISSING {rf}")
            continue
        sha = hashlib.sha256(rp.read_bytes()).hexdigest()[:16]
        ok = any(pr_ok for pr_ok in _file_proofs(rp, sha, proofs))
        if not ok:
            out.append(f"FAIL ROWS-NO-PROOF rows file {rf} (sha {sha}) has no passing ROWS-PROOF naming it")
    return out


def _file_proofs(rp, sha, proofs):
    cands = list(proofs) + [str(rp) + ".proof.json"]
    for pf in cands:
        try:
            pr = _load(pf)
        except (OSError, ValueError):
            continue
        if pr.get("schema") == PROOF_SCHEMA and pr.get("result") == "pass" and pr.get("files", {}).get(rp.name) == sha:
            yield True


def mkproof(plan, baseline, lane, evidence, result="pass"):
    raw = _load(plan)
    d = delta_rows(raw, _load(baseline) if baseline else None)
    return {"schema": PROOF_SCHEMA, "lane": lane, "result": result, "plan": str(plan),
            "plan_sha": hashlib.sha256(Path(plan).read_bytes()).hexdigest()[:16], "evidence": str(evidence),
            "check": "dry-run of the consumer check (reset_consumers.localize) on the EMITTED bind RTL of every type below",
            "types": d}


# ---------------------------------------------------------------- GEOM
def type_sites(t):
    """(name, (x, y)) for every station, relay and reset-relay site of one partition type (type frame, um)."""
    for i, sl in enumerate(t.get("ft_slots") or []):
        for j, p in enumerate(sl.get("regs_um") or []):
            yield f"ft_slots[{i}:{sl.get('name')}].regs_um[{j}]", p
    for i, st in enumerate(t.get("internal_stations") or []):
        for j, p in enumerate(st.get("regs_um") or []):
            yield f"internal_stations[{i}:{st.get('conn')}].regs_um[{j}]", p
    rs = t.get("reset") or {}
    for j, p in enumerate(rs.get("local_taps_um") or []):
        yield f"reset.local_taps_um[{j}]", p
    if rs.get("tap_um"):
        yield "reset.tap_um", rs["tap_um"]


def core_boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        try:
            ox, oy = c["origin_um"]
            w, h = c["outline_um"]
        except (KeyError, TypeError, ValueError):
            continue
        out.append((c.get("inst", "?"), float(ox), float(oy), float(ox) + float(w), float(oy) + float(h)))
    return out


def geom_overlaps(raw, halo=0.0):
    """[(type, site name, (x, y), core inst, box)] for every site strictly inside (halo-grown) a hard-core box of ITS OWN type."""
    out = []
    for tn, t in (raw.get("partition_types") or {}).items():
        if t.get("hard"):
            continue
        boxes = core_boxes(t)
        if not boxes:
            continue
        for name, p in type_sites(t):
            try:
                x, y = float(p[0]), float(p[1])
            except (TypeError, ValueError, IndexError):
                continue
            for inst, x0, y0, x1, y1 in boxes:
                if x0 - halo < x < x1 + halo and y0 - halo < y < y1 + halo:
                    out.append((tn, name, (x, y), inst, (x0, y0, x1, y1)))
    return out


def check_geom(plan, halo=0.0, strict_cores=False, baseline=None, refuse=REFUSE_CORES):
    """FAIL STATION-IN-CORE per refused overlapping site (all listed); one WARN line counts the tolerated overlaps."""
    out = []
    ref = re.compile(refuse)
    known = None
    if baseline:
        known = {(tn, name, xy, inst) for tn, name, xy, inst, _ in geom_overlaps(_load(baseline), halo)}
    n_inh = 0
    for tn, name, (x, y), inst, b in geom_overlaps(_load(plan), halo):
        if known is not None:
            refused = (tn, name, (x, y), inst) not in known
        else:
            refused = strict_cores or bool(ref.match(inst))
        if strict_cores:
            refused = True
        if not refused:
            n_inh += 1
            continue
        out.append(f"FAIL GEOM-STATION-IN-CORE type {tn}: {name} at ({x:g}, {y:g}) lies inside hard core {inst} "
                   f"[{b[0]:g}, {b[1]:g}, {b[2]:g}, {b[3]:g}]")
    if n_inh:
        out.append(f"WARN GEOM-INHERITED {n_inh} station/relay sites lie over other hard cores (tolerated: adopted plans carry "
                   f"them; --baseline-plan refuses new ones, --strict-cores all)")
    return out


# ---------------------------------------------------------------- driver
LR_NAME = re.compile(r"^rst_rl_\d+$")
LR_SKIP = ("collector_tree",)        # a self-contained tree with its own relay names


def landing_reset_refs(t):
    """{plan path: rst_rl_<k>} of every generated reset relay name the type's clock section references (collector_tree excluded)"""
    out = {}

    def walk(o, path):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if k in LR_SKIP:
                continue
            if isinstance(v, str) and LR_NAME.match(v):
                out[f"{path}/{k}"] = v
            else:
                walk(v, f"{path}/{k}")
    walk(t.get("clock") or {}, "clock")
    return out


def moved_types(raw, base_raw):
    """{type: [what moved]}: hard-core boxes (origin / outline) or the clock tap tables differ from the baseline"""
    out = {}
    bt = base_raw.get("partition_types") or {}
    for tn, t in (raw.get("partition_types") or {}).items():
        b = bt.get(tn)
        if not isinstance(b, dict) or not isinstance(t, dict) or t.get("hard"):
            continue
        cb, cn = {c[0]: c[1:] for c in core_boxes(b)}, {c[0]: c[1:] for c in core_boxes(t)}
        why = [k for k in cn if k in cb and cn[k] != cb[k]]
        ck, bk = t.get("clock") or {}, b.get("clock") or {}
        why += [k for k in ("taps", "added_taps") if ck.get(k) != bk.get(k)]
        if why:
            out[tn] = why
    return out


SHIFT_TOL_UM = 0.011


def planned_shifts(t, b):
    """LANDREMAP-SHIFT-1123 (COORD, HEAD-R18 s2 nst4 rst_rl_17 -34.56 / wch4b hd_lep0N_w rst_rl_35 +69.12): the non-zero
    translations (dx, dy) the row applied to this type, read from the row itself: hard-core origin deltas (same inst, same outline)
    and clock tap xy deltas (same tap name) vs the baseline type"""
    out = set()
    cb = {c[0]: c[1:] for c in core_boxes(b)}
    for c in core_boxes(t):
        o = cb.get(c[0])
        if o and abs((c[3] - c[1]) - (o[2] - o[0])) < SHIFT_TOL_UM and abs((c[4] - c[2]) - (o[3] - o[1])) < SHIFT_TOL_UM:
            out.add((round(c[1] - o[0], 2), round(c[2] - o[1], 2)))
    def taps(x):
        r = {}
        for k in ("taps", "added_taps"):
            for a in (x.get("clock") or {}).get(k) or []:
                try:
                    r[a["name"]] = (float(a["xy"][0]), float(a["xy"][1]))
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
        return r
    bt = taps(b)
    for n_, xy in taps(t).items():
        if n_ in bt:
            out.add((round(xy[0] - bt[n_][0], 2), round(xy[1] - bt[n_][1], 2)))
    out.discard((0.0, 0.0))
    out.discard((-0.0, 0.0)); out.discard((0.0, -0.0)); out.discard((-0.0, -0.0))
    return out


def _shifted(old, new, shifts):
    """the planned shift (dx, dy) that carries relay identity old (depth, xy, kind) onto new, else None"""
    if not old or not new or not shifts or old[0] != new[0] or old[2] != new[2] or len(old[1]) != 2 or len(new[1]) != 2:
        return None
    for dx, dy in sorted(shifts):
        if abs(new[1][0] - old[1][0] - dx) < SHIFT_TOL_UM and abs(new[1][1] - old[1][1] - dy) < SHIFT_TOL_UM:
            return (dx, dy)
    return None


def landremap_same(raw, braw, tn):
    """{plan path: relay} of the type's landing reset references unchanged vs the base: LANDREMAP solves both trees when non-empty"""
    rn = landing_reset_refs(raw["partition_types"][tn])
    rb = landing_reset_refs(braw["partition_types"][tn])
    return {p: v for p, v in rn.items() if rb.get(p) == v}


def landremap_types(raw, braw):
    """the moved types check_landremap solves (plan and base tree; the bind re-pick reads the same plan tree)"""
    return sorted(tn for tn in moved_types(raw, braw) if landremap_same(raw, braw, tn))

def check_landremap(plan, baseline, tree_fn=None, max_list=4, repick_fn=None, tree=None):
    """FAIL LANDREMAP per moved type whose landing reset references were not remapped (see LANDREMAP-1122 in the doc).
    tree_fn(raw, plan_path, type) -> {relay name: identity}; injectable for tests.
    GATE-AGREE-R1: a stale reference the bind re-picks itself (reset_anchor.repicked_paths, the bind's own predicate) is only
    WARN LANDREMAP-ADVISORY; one the bind would not repair stays FAIL, and an anchor the bind would refuse is named (FAIL LANDREMAP-BIND).
    A reset tree that cannot be built is FAIL LANDREMAP-UNCHECKED (LANDREMAP-TREE-FAIL-1123); a reference whose relay moved by a planned
    shift of the row (planned_shifts) is the same relay: WARN LANDREMAP-SHIFT, not stale (LANDREMAP-SHIFT-1123).
    repick_fn(raw, plan_path, type) -> (paths, error); injectable (default none when tree_fn is injected)."""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    mv = {tn: v for tn, v in moved_types(raw, braw).items() if _in_scope(tn)}     # PRE-SPEED-1125: a scoped PRE judges its scope
    if not mv:
        return []
    if tree_fn is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import schema
        import reset_tree as RT
        import reset_anchor as RA
        plans = {}

        def _tree(r, pp, tn):
            if id(r) not in plans:
                plans[id(r)] = schema.Plan(r, Path(pp).parent / "die_plan.json")
            return RT.for_type(plans[id(r)], tn)

        def tree_fn(r, pp, tn):                         # plan inputs (sink_bins_file ...) read from --tree (LANDREMAP-TREE-FAIL-1123)
            return _in_tree(tree, lambda: {x["q"]: (x.get("depth"), tuple(round(float(c), 2) for c in x.get("xy") or ()), x.get("kind"))
                                           for x in _tree(r, pp, tn)["relays"]})

        if repick_fn is None:
            def repick_fn(r, pp, tn):
                root = Path(tree).resolve() if tree and Path(tree).is_dir() else Path(__file__).resolve().parents[2]
                return _in_tree(tree, lambda: RA.repicked_paths(tn, r["partition_types"][tn], _tree(r, pp, tn), root))
    out, bad = [], []
    for tn in sorted(mv):
        same = landremap_same(raw, braw, tn)
        if not same:
            continue
        try:
            tb, tw = tree_fn(braw, baseline, tn), tree_fn(raw, plan, tn)
        except Exception as e:  # noqa: BLE001 - LANDREMAP-TREE-FAIL-1123: an unbuilt tree is a FAIL, never a skip
            out.append(f"FAIL LANDREMAP-UNCHECKED {tn}: reset tree not built ({type(e).__name__}: {str(e)[:160]}); landing reset "
                       f"references NOT checked -- the bind / kit gen builds the same tree and stops there; re-run with --tree "
                       f"<tree holding the plan inputs> or fix the tree inputs")
            continue
        stale = sorted((p, v) for p, v in same.items() if tb.get(v) != tw.get(v))
        shifts = planned_shifts(raw["partition_types"][tn], braw["partition_types"][tn])
        moved = [x for x in stale if _shifted(tb.get(x[1]), tw.get(x[1]), shifts)]
        if moved:                                        # LANDREMAP-SHIFT-1123: the same relay, carried by the row's planned shift
            ds = sorted({_shifted(tb.get(v), tw.get(v), shifts) for _, v in moved})
            out.append(f"WARN LANDREMAP-SHIFT {tn}: {len(moved)} landing reset reference(s) name the same relay translated by the "
                       f"planned shift {', '.join(f'({dx:+g}, {dy:+g})' for dx, dy in ds)} um of the type's moved cores / taps "
                       f"({', '.join(f'{v} {tb.get(v)[1]}->{tw.get(v)[1]}' for _, v in moved[:max_list])}): not stale")
            stale = [x for x in stale if x not in moved]
        if not stale:
            continue
        rp, rerr = set(), None
        if repick_fn is not None:
            try:
                rp, rerr = repick_fn(raw, plan, tn)
            except Exception as e:  # noqa: BLE001 - unknown = the old, blocking reading
                out.append(f"WARN LANDREMAP {tn}: bind re-pick not evaluated ({type(e).__name__}: {str(e)[:160]}); all findings blocking")
        auto = [x for x in stale if x[0] in rp]
        stale = [x for x in stale if x[0] not in rp]
        if auto:
            out.append(f"WARN LANDREMAP-ADVISORY {tn}: {len(auto)} stale landing reset reference(s) are re-picked by the bind itself "
                       f"(reset_tree_anchor / LOCAL-RESET-RAW-1; GATE-AGREE-R1), no landing_remap needed")
        if rerr:
            out.append(f"FAIL LANDREMAP-BIND {tn}: the bind would refuse this type: {rerr[:300]}")
        if not stale:
            continue
        inv = {}
        for n_, idt in tw.items():
            inv.setdefault(idt, []).append(n_)
        nofix = [(p, v) for p, v in stale if len(inv.get(tb.get(v), [])) != 1]
        if nofix:                                        # PORTPAD-1122: landing_remap's identity pass cannot place these; never suggest it
            ex = "; ".join(f"{p} = {v} {tb.get(v)}: {len(inv.get(tb.get(v), []))} new relay(s) of that identity" for p, v in nofix[:max_list])
            out.append(f"FAIL LANDREMAP-NOREMAP {tn}: {len(nofix)} landing reset reference(s) name a relay with no unique successor "
                       f"in the new reset tree ({ex}); landing_remap cannot fix this: re-site the landing branch with a plan row")
            if len(nofix) == len(stale):
                continue
        bad.append(tn)
        ex = "; ".join(f"{p} = {v} was {tb.get(v)} now {tw.get(v)}" for p, v in stale[:max_list])
        out.append(f"FAIL LANDREMAP {tn}: {','.join(mv[tn][:3])} moved vs baseline but {len(stale)} landing reset "
                   f"reference(s) still name the old relays ({ex})")
    if bad:
        out.append(f"FAIL LANDREMAP RUN landing_remap: python3 -I tools/die_plan/landing_remap.py {baseline} {plan} OUT.json "
                   f"--types {','.join(bad)} --root . --receipt RECEIPT.json   (then bind OUT.json)")
    return out


ABSPATH_STRICT_FROM = "2026-11-29"           # present-but-outside absolute inputs: WARN before this day, FAIL from it
ABS_RE = re.compile(r"^/(?:srv|home|mnt|data|scratch|tmp|opt|archive|nvme)[^\s\"';|&<>]*$")
ABS_SKIP = re.compile(r"^(?:provenance|source.*|note.*|comment.*|receipt.*|evidence.*|proof.*|.*_proof|report.*|.*_report|history|why|.*_log)$", re.I)


def plan_tree_root(plan, tree=None):
    """the plan's own tree: --tree, else the nearest parent of the plan holding tools/die_plan or physical + rtl"""
    if tree:
        return Path(tree)
    d = Path(plan).resolve().parent if not Path(plan).is_dir() else Path(plan)
    for q in [Path(plan).absolute().parent, *Path(plan).absolute().parents, d, *d.parents]:
        if (q / "tools" / "die_plan").is_dir() or ((q / "physical").is_dir() and (q / "rtl").is_dir()):
            return q
    return Path(plan).absolute().parent


def abs_refs(obj, path=""):
    """[(json path, absolute path string)] of every absolute path value outside record keys (ABS_SKIP)"""
    out = []
    items = obj.items() if isinstance(obj, dict) else enumerate(obj) if isinstance(obj, list) else ()
    for k, v in items:
        if isinstance(k, str) and ABS_SKIP.match(k):
            continue
        if isinstance(v, str):
            if ABS_RE.match(v):
                out.append((f"{path}/{k}", v))
        elif isinstance(v, (dict, list)):
            out += abs_refs(v, f"{path}/{k}")
    return out


def _inside(p, roots):
    cands = {Path(p).absolute()}
    try:
        cands.add(Path(p).resolve())
    except (OSError, RuntimeError):
        pass
    for r in roots:
        for c in cands:
            try:
                c.relative_to(r)
                return True
            except ValueError:
                pass
    return False


def abspath_findings(plan, tree=None, sidecar=None, level=None, today=None, max_list=6, already=""):
    """FAIL/WARN ABSPATH lines (see ABSPATH-1122 in the doc); a path named in `already` (earlier findings, e.g. INPUT-MISSING) is not repeated."""
    import time as _t
    root = plan_tree_root(plan, tree)
    roots = {root.absolute()}
    try:
        roots.add(root.resolve())
    except OSError:
        pass
    lv = (level or os.environ.get("OT_PLAN_ABSPATH") or "").lower()
    strict = (today or _t.strftime("%Y-%m-%d")) >= ABSPATH_STRICT_FROM
    files = [Path(plan)] + ([Path(sidecar)] if sidecar else []) + [Path(plan).parent / "wave_prepare.json"]
    miss, outside = [], []
    for f in dict.fromkeys(files):
        if not f.is_file():
            continue
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for jp, v in abs_refs(doc):
            if _inside(v, roots) or v in already:
                continue
            (outside if Path(v).exists() else miss).append(f"{f.name}:{jp} = {v}")
    out = []
    if miss:
        tag = "FAIL" if lv == "fail" or (strict and lv != "warn") else "WARN"
        out.append(f"{tag} ABSPATH-MISSING {len(miss)} absolute input(s) outside tree {root} do not exist (kit gen dies at "
                   f"abs_inputs; FAIL from {ABSPATH_STRICT_FROM}): " + "; ".join(miss[:max_list]))
    if outside:
        tag = "FAIL" if lv == "fail" or (strict and lv != "warn") else "WARN"
        out.append(f"{tag} ABSPATH-OUTSIDE {len(outside)} absolute input(s) outside tree {root} (die with their snapshot; "
                   f"FAIL from {ABSPATH_STRICT_FROM}): " + "; ".join(outside[:max_list]))
    if out:
        out.append(f"{out[0].split()[0]} ABSPATH fix: python3 -I tools/die_plan/plan_gate_pre.py localize --plan {plan} --out PLAN2.json"
                   + (f" --tree {tree}" if tree else ""))
    return out


def localize(plan, out, tree=None, sidecar=None):
    """copy every present outside absolute input file of the plan into <plan dir>/inputs/<sha12>_<name> and rewrite the
    reference tree-relative; -> (n copied, [unresolved]).  Directories and missing targets are reported, not changed."""
    import shutil
    root = plan_tree_root(plan, tree).absolute()
    pdir = Path(plan).absolute().parent
    raw = json.loads(Path(plan).read_text())
    done, left = {}, []

    def fix(o):
        items = list(o.items()) if isinstance(o, dict) else list(enumerate(o)) if isinstance(o, list) else []
        for k, v in items:
            if isinstance(k, str) and ABS_SKIP.match(k):
                continue
            if isinstance(v, str) and ABS_RE.match(v) and not _inside(v, {root, root.resolve()}):
                src = Path(v)
                if not src.is_file():
                    left.append(v)
                    continue
                if v not in done:
                    h = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
                    dst = pdir / "inputs" / f"{h}_{src.name}"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        tmp = dst.with_name(dst.name + ".part")
                        shutil.copyfile(src, tmp)
                        os.replace(tmp, dst)
                    try:
                        done[v] = str(dst.relative_to(root))
                    except ValueError:
                        done[v] = str(dst)
                o[k] = done[v]
            elif isinstance(v, (dict, list)):
                fix(v)
    fix(raw)
    Path(out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    return len(done), left


def _bus_depth(raw, tn, bus):
    rows = [e for e in ((raw.get("partition_types") or {}).get(tn) or {}).get("internal_stations") or []
            if e.get("conn") == "bus:" + str(bus)]
    return max((len(e.get("regs_um") or []) for e in rows), default=0)


def istcyc_lanes(raw, braw):
    """[(lane id, src (type, bus), dst (type, bus), base depth, new depth, base fixed, new fixed)] for the lanes whose end-bus
    station depth changed vs the baseline and whose baseline fixed_cycles == baseline source + destination; touched types only"""
    bt, nt = braw.get("partition_types") or {}, raw.get("partition_types") or {}
    changed = {tn for tn, t in nt.items() if isinstance(t, dict) and tn in bt
               and (t.get("internal_stations") or []) != ((bt.get(tn) or {}).get("internal_stations") or [])}
    if not changed:
        return []
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    blanes = {L.get("id"): L for L in braw.get("lanes") or []}
    out = []
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if not ps or not ps[0] or not ps[-1]:
            continue
        try:
            src = (parts[ps[0]["src"]["part"]]["type"], ps[0]["src"]["bus"])
            dst = (parts[ps[-1]["dst"]["part"]]["type"], ps[-1]["dst"]["bus"])
        except (KeyError, TypeError):
            continue
        if src[0] not in changed and dst[0] not in changed:
            continue
        b = blanes.get(L.get("id"))
        if b is None:
            continue
        db = _bus_depth(braw, *src) + _bus_depth(braw, *dst)
        dn = _bus_depth(raw, *src) + _bus_depth(raw, *dst)
        bfx, nfx = int(b.get("fixed_cycles", 0) or 0), int(L.get("fixed_cycles", 0) or 0)
        if dn == db or bfx != db:
            continue
        out.append((L.get("id"), src, dst, db, dn, bfx, nfx))
    return out


def depth_changed_lanes(raw, braw):
    """{lane id: (base depth, new depth)} for lanes on types whose internal_stations changed, whose source OUT + destination IN
    station depth differs from the base (no fixed_cycles rule: every bound depth that moves)"""
    bt, nt = braw.get("partition_types") or {}, raw.get("partition_types") or {}
    changed = {tn for tn, t in nt.items() if isinstance(t, dict) and tn in bt
               and (t.get("internal_stations") or []) != ((bt.get(tn) or {}).get("internal_stations") or [])}
    if not changed:
        return {}
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    out = {}
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if not ps or not ps[0] or not ps[-1]:
            continue
        try:
            src = (parts[ps[0]["src"]["part"]]["type"], ps[0]["src"]["bus"])
            dst = (parts[ps[-1]["dst"]["part"]]["type"], ps[-1]["dst"]["bus"])
        except (KeyError, TypeError):
            continue
        if src[0] not in changed and dst[0] not in changed:
            continue
        db = _bus_depth(braw, *src) + _bus_depth(braw, *dst)
        dn = _bus_depth(raw, *src) + _bus_depth(raw, *dst)
        if db != dn:
            out[L.get("id")] = (db, dn)
    return out


def check_r8stale(tree, plan, baseline, asbuilt=None, max_list=6):
    """FAIL / WARN R8STALE (see R8STALE-1122)"""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    lanes = depth_changed_lanes(raw, braw)
    if not lanes:
        return []
    ab, mdir = None, Path(plan).parent
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).parent
    if not isinstance(ab, dict):
        ab = raw.get("asbuilt") if isinstance(raw.get("asbuilt"), dict) else None
    if not ab:
        return []
    base, _ = manifest_paths(ab, mdir, tree)
    tabs = []
    if ab.get("land_r8"):
        tabs.append(ab["land_r8"])
    tabs += list(ab.get("land_r8_extra") or [])
    root, broot = plan_tree_root(plan, tree).absolute(), plan_tree_root(baseline).absolute()
    out = []
    recipe = (f"regenerate: one strict bind of this plan stops at R8_FAIL_FAST and writes OUT/r8_derived.json (OUT/bus_groups.json); "
              f"install it as the table (or python3 -I tools/die_plan/r8_refresh.py {plan} OUT/bus_groups.json TABLE --asbuilt AB), then bind")
    for rel in tabs:
        tp = Path(os.path.normpath(Path(rel) if Path(rel).is_absolute() else Path(base) / rel))
        try:
            members = (json.loads(tp.read_text()) or {}).get("members") or []
        except (OSError, ValueError):
            continue
        hit = sorted({str(m.get("lane")) for m in members if m.get("lane") in lanes})
        if not hit:
            continue
        try:
            bcopy = broot / tp.absolute().relative_to(root)
        except ValueError:
            bcopy = None
        ex = ", ".join(f"{x} {lanes[x][0]}->{lanes[x][1]}" for x in hit[:max_list])
        nm = sum(1 for m in members if m.get("lane") in lanes)
        if bcopy is not None and bcopy.is_file() and bcopy.read_bytes() == tp.read_bytes():
            out.append(f"FAIL R8STALE {tp}: {nm} member(s) on {len(hit)} lane(s) whose station depth changed vs the base ({ex}), "
                       f"but the table is byte-identical to the base copy {bcopy} (not re-derived); {recipe}")
        else:
            out.append(f"WARN R8STALE {tp}: {nm} member(s) on {len(hit)} lane(s) whose station depth changed vs the base ({ex}); "
                       f"base copy {'not found' if bcopy is None or not bcopy.is_file() else 'differs (re-derived?)'}; if not re-derived: {recipe}")
    return out


def r8_tables(tree, plan, asbuilt=None):
    """[resolved Path] of the as-built's R8 tables (land_r8 first, then land_r8_extra), resolved as bind.py does"""
    ab, mdir = None, Path(plan).parent
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).parent
    if not isinstance(ab, dict):
        raw = _load(plan)
        ab = raw.get("asbuilt") if isinstance(raw, dict) and isinstance(raw.get("asbuilt"), dict) else None
    if not ab:
        return []
    base, _ = manifest_paths(ab, mdir, tree)
    rels = ([ab["land_r8"]] if ab.get("land_r8") else []) + list(ab.get("land_r8_extra") or [])
    return [Path(os.path.normpath(Path(r) if Path(r).is_absolute() else Path(base) / r)) for r in rels]


R8BOUND_LEVEL = "WARN"     # R8BOUND-1124 (COORD flow review #2, r703 new-check rule): report-only until COORD rules otherwise


def check_r8bound(tree, plan, asbuilt=None, max_list=8, raw=None):
    """R8BOUND-1124 (COORD flow review #2; QC C1m scoped bind died after 7,185 s on R8_STALE x6 dvs_E*.so_w, flt lane 2 -> 4):
    the bind's bound depth of a DIRECT lane bit is the plan's latency.lanes[<lane>].cycles (bind.py plan_lanes / recv), so every
    R8 table member whose lane runs straight from its src_part to its sink_part must carry bound == that cycles, else the strict
    bind fails R8_STALE at its head.  Tables merge as the bind merges them (land_r8_extra authoritative per id; INNER:* skipped).
    Forwarded members (lane ends != the member's partitions: bound = a sum over lanes) and lanes without a latency cycles row are
    not judged (counted).  One R8BOUND_LEVEL line per table with stale members, with the refresh recipe."""
    raw = raw if raw is not None else _load(plan)
    if not isinstance(raw, dict):
        return []
    tabs = r8_tables(tree, plan, asbuilt)
    if not tabs:
        return []
    lat = (raw.get("latency") or {}).get("lanes") or {}
    ports = {x.get("id"): x for x in raw.get("ports", []) or []}
    ends = {}
    for ln in raw.get("lanes", []) or []:
        try:
            hp = [ports[q] for q in ln["ports"]]
            ends[ln["id"]] = (hp[0]["src"]["part"], hp[-1]["dst"]["part"])
        except (KeyError, IndexError, TypeError):
            continue
    merged, origin, out = {}, {}, []
    for tp in tabs:
        try:
            members = (json.loads(tp.read_text()) or {}).get("members") or []
        except (OSError, ValueError) as e:
            out.append(f"{R8BOUND_LEVEL} R8BOUND {tp}: table not readable ({type(e).__name__}); not checked")
            continue
        for m in members:
            if isinstance(m, dict) and m.get("id") and not str(m["id"]).startswith("INNER:"):
                merged[m["id"]], origin[m["id"]] = m, tp
    bad, skipped = {}, 0
    for i, m in merged.items():
        ln = m.get("lane")
        L = lat.get(ln) if ln is not None else None
        if ln not in ends or not isinstance(L, dict) or "cycles" not in L or ends[ln] != (m.get("src_part"), m.get("sink_part")):
            skipped += 1
            continue
        try:
            want = int(L["cycles"])
        except (TypeError, ValueError):
            skipped += 1
            continue
        if m.get("bound") != want:
            bad.setdefault(origin[i], []).append((i, ln, m.get("bound"), want))
    recipe = (f"refresh before the bind: python3 -I tools/die_plan/r8_refresh.py {plan} OUT/bus_groups.json TABLE --asbuilt AB "
              f"(OUT/bus_groups.json from `bind.py r8-prepass` or a strict bind that stopped at R8_FAIL_FAST)")
    for tp, rows in bad.items():
        ex = "; ".join(f"{i} lane {ln} table {b} plan {w}" for i, ln, b, w in sorted(rows)[:max_list])
        out.append(f"{R8BOUND_LEVEL} R8BOUND {tp}: {len(rows)} direct member(s) whose bound != the plan lane cycles (strict bind "
                   f"will fail R8_STALE; report-only): {ex}{' ...' if len(rows) > max_list else ''}; {recipe}")
    if bad or skipped:
        out.append(f"LIST R8BOUND members {len(merged)} judged {len(merged) - skipped} stale {sum(map(len, bad.values()))} "
                   f"not judged (forwarded / no cycles row) {skipped}")
    return out


HALOCORNER_LEVEL = "WARN"  # HALOCORNER-1125 (COORD, QC-ALLFIX): report-only; the sites move in plan rows (C1o / A5t8 / c10), never in bound trees
HALOCORNER_EPS = 1e-6      # um; far below one DBU (0.001), above the decimal roundoff of abutting faces (816.48 vs 816.4799999999999)


def halo_corner_hit(p, boxes, eps=HALOCORNER_EPS, row_um=None, cell_w_um=None):
    """HALOCORNER-1125: number of grown halos the point p sits on at a SHARED CORNER, else 0.
    p is a hit when it touches (closed box) 2 or more halos of `boxes`, is a corner of at least one of them, lies in no halo's
    interior (that is a different class), and has no free row-high (ROW_UM, y) or cell-wide (CELL_W_UM, x) run under INCLUSIVE
    face contact (the intended reset_tree._free rule, FLOW-OPS-R3 11-24 23:33).  reset_tree._free bounds its runs only by boxes
    the point is strictly inside in x or y, so at such a corner the runs are unbounded and the point is called a legal site.
    Two halos on one straight seam (p mid-seam, no corner) are not a hit: _free already rejects them (zero-width run)."""
    if row_um is None or cell_w_um is None:
        import reset_tree as RT
        row_um, cell_w_um = RT.ROW_UM, RT.CELL_W_UM
    x, y = p
    touch, corner = 0, False
    ylo, yhi, xlo, xhi = -math.inf, math.inf, -math.inf, math.inf
    for a, b, c, d in boxes:
        ix, iy = a - eps <= x <= c + eps, b - eps <= y <= d + eps
        if not (ix and iy):
            if ix:
                if b >= y - eps:
                    yhi = min(yhi, b)
                elif d <= y + eps:
                    ylo = max(ylo, d)
            if iy:
                if a >= x - eps:
                    xhi = min(xhi, a)
                elif c <= x + eps:
                    xlo = max(xlo, c)
            continue
        if a + eps < x < c - eps and b + eps < y < d - eps:
            return 0
        touch += 1
        corner = corner or ((abs(x - a) <= eps or abs(x - c) <= eps) and (abs(y - b) <= eps or abs(y - d) <= eps))
        if b >= y - eps:
            yhi = min(yhi, b)
        elif d <= y + eps:
            ylo = max(ylo, d)
        if a >= x - eps:
            xhi = min(xhi, a)
        elif c <= x + eps:
            xlo = max(xlo, c)
    if touch < 2 or not corner:
        return 0
    if yhi - ylo >= row_um - eps and xhi - xlo >= cell_w_um - eps:
        return 0
    return touch


def _xy(v):
    if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(q, (int, float)) and not isinstance(q, bool) for q in v[:2]):
        return (float(v[0]), float(v[1]))
    return None


def halocorner_points(raw, tn, t):
    """[(source, name, (x, y))]: every planned relay site and published reset-tree node of type tn (type frame).
    relay_sites{name: xy}; clock.landing_contract.collector_tree root / start_in / relays[].xy / outs[]; reset.in_sites[tn]."""
    pts = []
    for nm, v in sorted(((t.get("relay_sites") or {}) if isinstance(t.get("relay_sites"), dict) else {}).items()):
        q = _xy(v)
        if q:
            pts.append(("relay_sites", nm, q))
    ct = ((t.get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
    if isinstance(ct, dict):
        for k in ("root", "start_in"):
            q = _xy(ct.get(k))
            if q:
                pts.append(("reset_tree", k, q))
        for r in ct.get("relays") or []:
            q = _xy(r.get("xy")) if isinstance(r, dict) else None
            if q:
                pts.append(("reset_tree", str(r.get("name")), q))
        for i, o in enumerate(ct.get("outs") or []):
            q = _xy(o)
            if q:
                pts.append(("reset_tree", f"out[{i}]", q))
    q = _xy(((raw.get("reset") or {}).get("in_sites") or {}).get(tn))
    if q:
        pts.append(("reset_in_site", "in_site", q))
    return pts


def halocorner_rows(raw, eps=HALOCORNER_EPS):
    """(rows, stats): rows = [(die, type, source, name, x, y, halos)] of every planned relay site / reset-tree node on a shared
    halo corner (halo_corner_hit), halos from reset_tree.blockages (the geometry reset_tree._free judges); stats = counts."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import reset_tree as RT
    die = str((raw.get("die") or {}).get("name") or "?") if isinstance(raw.get("die"), dict) else "?"
    rows, n_types, n_pts, errs = [], 0, 0, []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        pts = halocorner_points(raw, tn, t)
        if not pts:
            continue
        try:
            boxes = [tuple(map(float, b)) for b in RT.blockages(t)]
        except Exception as e:  # noqa: BLE001 - a type whose halos cannot be built is named, never silently passed
            errs.append(f"{tn} ({type(e).__name__}: {str(e)[:80]})")
            continue
        n_types += 1
        n_pts += len(pts)
        if len(boxes) < 2:
            continue
        g = 1e-4                                         # corner index: only points within eps of some halo corner are judged
        keys = set()
        for a, b, c, d in boxes:
            for cx in (a, c):
                for cy in (b, d):
                    keys.add((round(cx / g), round(cy / g)))
        memo = {}
        for src, nm, (x, y) in pts:
            kx, ky = round(x / g), round(y / g)
            if not any((kx + i, ky + j) in keys for i in (-1, 0, 1) for j in (-1, 0, 1)):
                continue
            if (x, y) not in memo:
                memo[(x, y)] = halo_corner_hit((x, y), boxes, eps, RT.ROW_UM, RT.CELL_W_UM)
            if memo[(x, y)]:
                rows.append((die, tn, src, nm, x, y, memo[(x, y)]))
    return rows, {"die": die, "types": n_types, "points": n_pts, "errors": errs}


_TAPSITES_CACHE = {}


def tap_sites_cached(plan, raw, tns):
    """{type: (sites, core, why)} for TAPREACH / STALETABLE (tap_offset_cover.type_ports in the fork pool), solved once per plan path"""
    key = (str(plan), tuple(sorted(tns)))
    if key not in _TAPSITES_CACHE:
        import tap_reach as TR
        _TAPSITES_CACHE.clear()
        _TAPSITES_CACHE[key] = TR.solve_tap_sites(raw, plan, tns, mapper=fork_map)
    return _TAPSITES_CACHE[key]


def check_tapreach(plan, raw=None):
    """TAPREACH-1126: tap_reach.census findings (WARN; FAIL with $OT_PRE_TAPREACH_BLOCK=1)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import tap_reach as TR
    raw = raw or _load(plan)
    tns = [tn for tn in (raw.get("partition_types") or {}) if _in_scope(tn)]
    return TR.findings(raw, TR.census(raw, tap_sites_cached(plan, raw, tns), set(tns)))


def check_staletable(plan, raw=None):
    """STALETABLE-1126: stale_tables.findings (ADVISORY WARN; FAIL with $OT_PRE_STALETABLE_BLOCK=1)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import stale_tables as ST
    raw = raw or _load(plan)
    tns = [tn for tn in (raw.get("partition_types") or {}) if _in_scope(tn)]
    if _SCOPE is not None:
        raw = scope_view(raw, set(tns))
    return ST.findings(raw, tap_sites_cached(plan, raw, tns), ST.make_legal(raw, plan))


def check_halocorner(plan, max_list=6, raw=None):
    """HALOCORNER-1125 (COORD; FLOW-OPS-R3 DIEPLAN-GREEN 11-24 23:33, reset_tree._free corner escape since 42eeacf87f7): one
    HALOCORNER_LEVEL line per type with planned relay sites / reset-tree nodes on a shared corner of 2+ grown halos (not a legal
    site: no row-high / cell-wide run), plus one LIST line.  Report-only: never a FAIL; the fix is a plan row that moves them."""
    raw = raw if raw is not None else _load(plan)
    if not isinstance(raw, dict):
        return []
    rows, st = halocorner_rows(raw)
    by = {}
    for r in rows:
        by.setdefault(r[1], []).append(r)
    out = []
    for tn, rs in sorted(by.items()):
        nxy = len({(r[4], r[5]) for r in rs})
        ex = "; ".join(f"{r[2]}:{r[3]} ({r[4]:g}, {r[5]:g}) x{r[6]}" for r in rs[:max_list])
        out.append(f"{HALOCORNER_LEVEL} HALOCORNER {st['die']}/{tn}: {len(rs)} relay site(s) / reset-tree node(s) at {nxy} shared halo "
                   f"corner(s) (reset_tree._free accepts them; no row-high / cell-wide run; report-only, move in the next plan row): "
                   f"{ex}{' ...' if len(rs) > max_list else ''}")
    for e in st["errors"]:
        out.append(f"{HALOCORNER_LEVEL} HALOCORNER {st['die']}/{e}: halos not built; not checked")
    out.append(f"LIST HALOCORNER die {st['die']} types {st['types']} points {st['points']} flagged {len(rows)} at "
               f"{len({(r[1], r[4], r[5]) for r in rows})} corner(s) in {len(by)} type(s)")
    return out


CABIND_LEVEL = "FAIL"


def cabind_rows(plan_raw, sidecar_raw):
    """CABIND-1125 (QC-CA-PRECHK): the bind's count-aligned sidecar-vs-plan equalities, computed by the bind's own functions.
    Returns (parts, other): parts = [(part, region, role, src, have, expect, why, tail)] for every sidecar count_aligned.parts row
    (expect = RELAY_STAGES + tx(origin type) + rx(own type) from count_align_bind.relay_extra_from_plan, the rule bind_parts and
    the clock_landings relay-role check apply; n_nominal(relay) = n_nominal(origin) + expect) and other = [msg] for the remaining
    equalities clock_landings.Landings checks at bind time (see check_cabind)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import count_align_bind as CAB
    ca = (sidecar_raw or {}).get("count_aligned") or {}
    net = ((plan_raw.get("clock") or {}).get("landing_network") or {})
    plist = plan_raw.get("partitions") or []
    plist = list(plist.values()) if isinstance(plist, dict) else plist
    ptype = {p["name"]: p.get("type") for p in plist}
    parts, other = [], []
    cp = ca.get("parts")
    if cp:
        try:
            extra = CAB.relay_extra_from_plan(plan_raw)
        except CAB.BindError as e:
            extra = {}
            other.append(f"relay stage key invalid: {e}")
        regs = ca.get("regions") or {}
        origins = {}
        for q, v in cp.items():
            if v.get("role") == "origin":
                origins.setdefault(v.get("region"), []).append(q)
        for q, v in sorted(cp.items()):
            role, src, have = v.get("role"), v.get("src"), int(v.get("stages", -1))
            why = []
            if role == "relay":
                if q not in ptype:
                    why.append("relay partition not in the plan")
                tx, rx = int(extra.get(src, 0)), int(extra.get("rx:" + q, 0))
                expect = CAB.RELAY_STAGES + tx + rx
                if (cp.get(src) or {}).get("role") != "origin":
                    why.append(f"src {src} is not an origin part")
                elif cp[src].get("region") != v.get("region"):
                    why.append(f"src {src} is in region {cp[src].get('region')}")
                tail = f"2 + tx[{ptype.get(src)}]={tx} + rx[{ptype.get(q)}]={rx}"
            elif role == "origin":
                expect, tail = 0, "origin"
            else:
                expect, tail = have, f"role {role!r}"
                why.append(f"role {role!r} is neither origin nor relay")
            if have != expect:
                why.insert(0, f"stages {have} != {tail} = {expect}")
            parts.append((q, v.get("region"), role, src, have, expect, "; ".join(why), tail))
        for r, qs in sorted(origins.items()):
            org = (regs.get(r) or {}).get("origin_part")
            if len(qs) != 1 or (org is not None and org not in qs):
                other.append(f"region {r}: sidecar origin parts {qs} vs regions.origin_part {org}")
    cyc = net.get("count_aligned_cycles")
    cports = ca.get("ports") or {}
    if ca and net.get("data_cycles_per_crossing") == "count_aligned":
        if not isinstance(cyc, dict):
            other.append("plan landing_network has no count_aligned_cycles dict")
        else:
            bad = sorted(p for p, c in cports.items() if p in cyc and int(cyc[p]) != int(c["sched_lat"]))
            if bad:
                other.append(f"{len(bad)} port(s) plan count_aligned_cycles != sidecar sched_lat: "
                             + ", ".join(f"{p} {cyc[p]}!={cports[p]['sched_lat']}" for p in bad[:6]))
            if not ca.get("mixed"):
                miss = sorted(set(cports) - set(cyc))
                stale = sorted(set(cyc) - set(cports))
                if miss:
                    other.append(f"{len(miss)} sidecar port(s) without a plan count_aligned_cycles entry: {miss[:4]}")
                if stale:
                    other.append(f"{len(stale)} plan count_aligned_cycles entr(ies) without a sidecar port: {stale[:4]}")
        bb = net.get("count_aligned_bind")
        if isinstance(bb, dict):
            d = [f"{k} plan {bb[k]!r} != sidecar {ca.get(k)!r}" for k in sorted(bb) if bb[k] != ca.get(k)]
            if d:
                other.append("count_aligned_bind " + "; ".join(d))
        try:
            import clock_landings as CL
            pports = {p["id"]: p for p in plan_raw.get("ports") or []}
            bad = []
            for pid, c in sorted(cports.items()):
                p = pports.get(pid)
                if p is None:
                    continue
                tn = ptype.get(p["dst"]["part"])
                bus = p["dst"]["bus"]
                q = bool(CL.output_qreg(plan_raw, tn, bus))
                if q != bool(c.get("output_qreg")):
                    bad.append(f"{pid} ({tn}.{bus}) output_qreg plan {q} sidecar {bool(c.get('output_qreg'))}")
                try:
                    CL.check_ca_freg_declared(plan_raw, tn, bus, c, pid)
                except CL.LandingError as e:
                    bad.append(str(e)[:160])
            if bad:
                other.append(f"{len(bad)} port(s) QREG/FREG declaration vs plan: " + " | ".join(bad[:4]))
        except ImportError as e:
            other.append(f"QREG/FREG declaration not checked: {e}")
    return parts, other


def check_cabind(plan, sidecar, raw=None):
    """CABIND-1125 (QC-CA-PRECHK; C1n-r2: 36 of 60 relay parts stale after the RTX-ALL / st_a landing_relay_tx_stages rows, the bind
    raised only on the first): FAIL per sidecar count_aligned.parts row whose stages differ from the bind's rule (every one, no cap),
    a per-part LIST table, and FAIL per other sidecar-vs-plan equality the bind enforces.  No sidecar count_aligned: no line."""
    raw = raw if raw is not None else _load(plan)
    sc = _load(sidecar) if sidecar else None
    if not isinstance(raw, dict) or not isinstance(sc, dict) or not sc.get("count_aligned"):
        return []
    parts, other = cabind_rows(raw, sc)
    out = []
    rel = [r for r in parts if r[2] == "relay"]
    bad = [r for r in parts if r[6]]
    for q, reg, role, src, have, exp, why, tail in bad:
        out.append(f"{CABIND_LEVEL} CABIND {q}: {why} (sidecar role {role} src {src}; the bind refuses relay role != relay(origin, N))")
    for m in other:
        out.append(f"{CABIND_LEVEL} CABIND {m}")
    if rel:
        out.append("LIST CABIND part table: part, region, src, sidecar stages, expected stages, expected dN vs origin, status")
        for q, reg, role, src, have, exp, why, tail in rel:
            out.append(f"LIST CABIND   {q}\t{reg}\t{src}\t{have}\t{exp}\t+{exp}\t{'MISMATCH' if why else 'ok'}")
    out.append(f"LIST CABIND parts {len(parts)} relay {len(rel)} mismatching {len(bad)} other {len(other)}")
    return out


def check_istcyc(plan, baseline, max_list=8):
    """FAIL ISTCYC per touched lane whose fixed_cycles was not re-priced (see ISTCYC-1122 in the doc)"""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    bad = [x for x in istcyc_lanes(raw, braw) if x[6] != x[4]]
    if not bad:
        return []
    out = [f"FAIL ISTCYC lane {lid}: stations {s[0]}.{s[1]} -> {d[0]}.{d[1]} source+destination {db} -> {dn}, fixed_cycles "
           f"{nfx} (base {bfx}), required {dn}" for lid, s, d, db, dn, bfx, nfx in bad[:max_list]]
    if len(bad) > max_list:
        out.append(f"FAIL ISTCYC ... {len(bad) - max_list} more lane(s)")
    out.append(f"FAIL ISTCYC fix: python3 -I tools/die_plan/plan_gate_pre.py reprice --plan {plan} --baseline-plan {baseline} "
               f"--out PLAN2.json   ({len(bad)} lane(s): " + ",".join(str(x[0]) for x in bad[:20]) + ")")
    return out


def reprice(plan, baseline, out):
    """set fixed_cycles = new source + destination on exactly the ISTCYC lanes; the latency row (fixed / cycles / natural)
    moves by the same delta.  -> {lane: (old, new)}"""
    raw, braw = json.loads(Path(plan).read_text()), json.loads(Path(baseline).read_text())
    lat = (raw.get("latency") or {}).get("lanes") or {}
    byid = {L.get("id"): L for L in raw.get("lanes") or []}
    done = {}
    for lid, _s, _d, _db, dn, _bfx, nfx in istcyc_lanes(raw, braw):
        if nfx == dn:
            continue
        byid[lid]["fixed_cycles"] = dn
        r = lat.get(lid)
        if r is not None:
            for f in ("fixed", "cycles", "natural"):
                if f in r:
                    r[f] = int(r[f]) + (dn - nfx)
        done[lid] = (nfx, dn)
    Path(out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    return done


def check_istprice(tree, plan, asbuilt=None, max_list=10):
    """FAIL ISTPRICE per over-cycle lane (see ISTPRICE in the module doc); the as-built is resolved here when none is given"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import adv_ist_price as IP
    except ImportError as e:
        return [f"FAIL ISTPRICE cannot run: {e}"]
    raw = _load(plan) or {}
    ab, how = None, ""
    if asbuilt:
        ab, how = _load(asbuilt), f"--asbuilt {asbuilt}"
    elif isinstance(raw.get("asbuilt"), dict):
        ab, how = raw["asbuilt"], "the plan's own asbuilt section"
    else:
        pd = Path(plan).resolve().parent
        cands = []
        for rel in ("plan_of_record/native_bind", "plan_inputs/run", "native_bind", "."):
            cands += sorted((pd / rel).glob("asbuilt_run*.json"), key=lambda q: q.stat().st_mtime, reverse=True)
        if not cands and tree:      # a composed plan outside the tree (c8/..json): the tree's own plan_of_record asbuilt_run
            for g in ("physical/die_plan/*/plan_of_record/native_bind/asbuilt_run*.json", "physical/die_plan/*/plan_inputs/run/asbuilt_run*.json"):
                cands += sorted(Path(tree).glob(g), key=lambda q: q.stat().st_mtime, reverse=True)
        if cands:
            ab, how = _load(cands[0]), str(cands[0])
    if not raw.get("lanes") or not raw.get("partition_types"):
        return []                                         # nothing to price (fixtures, type-only plans)
    types = raw.get("partition_types") or {}
    native_possible = any(isinstance(t, dict) and any(str(e.get("conn", "")).startswith("bus:") for e in t.get("internal_stations") or [] if isinstance(e, dict))
                          for t in types.values()) and bool(raw.get("lanes"))
    IP.MAX_LINES = 10 ** 6
    lines = IP.findings(raw, str(plan), tree, asbuilt=ab if isinstance(ab, dict) else None)
    out, warn = [], []
    for ln in lines:
        if ln.startswith("WARN ADV-IST-PRICE not checked"):
            # ISTPRICE-REPORT-1124 (COORD, r703: new checks stay report-only): a rule that could not run is a WARN, never a FAIL
            warn.append("WARN ISTPRICE " + ln.split("ADV-IST-PRICE ", 1)[1])
        elif ("summary" not in ln) and (" lane " in ln or "OUT-LANES" in ln):
            out.append("FAIL ISTPRICE " + ln.split("ADV-IST-PRICE ", 1)[1])
    n = len(out)
    if n > max_list:
        out = out[:max_list] + [f"FAIL ISTPRICE ... {n - max_list} more lane(s)"]
    if not isinstance(ab, dict) and native_possible:
        # ISTPRICE-REPORT-1124: no as-built only means FIXED-SPLIT / OUT-LANES were not judged (HEAD W3/W6/r7, QC C1g PRE "fail only on
        # ISTPRICE, no as-built" since 11d45bef39d): report-only WARN, said every run; flagged lanes stay FAIL
        warn.append("WARN ISTPRICE no as-built found (--asbuilt, plan asbuilt section, plan_of_record/native_bind/asbuilt_run*.json): "
                    "FIXED-SPLIT / OUT-LANES (native station rules) not judged (report-only); pass the integrator's as-built")
    out += warn
    if n:
        out.append(f"FAIL ISTPRICE {n} lane(s) over-cycle; fix: refresh the latency table / fixed_cycles = source + destination + declared receiver soft (ADV-IST-PRICE has the per-lane fix)")
    elif ab is not None:
        out.append(f"LIST ISTPRICE 0 lanes flagged (as-built: {how})")
    return out


BOUND_CHECKS = ("MACROGHOST", "SEATMATCH", "GENDRY-KITRTL", "RSTREACH")


def pre_mode(elab_dir, skip=()):
    """PRE-MODE-1124 (FABLE-RC-KV): one line saying whether the checks that need the BOUND RTL (--elab-dir with an error-free bind_report.json)
    ran on it ('PRE-MODE bound') or quietly fell back / were skipped ('PRE-MODE plan-only: N bound checks downgraded (names)'), so row lanes
    can label their PRE result (edge-strip lane read 23 vs 27 findings for exactly this reason)."""
    ok = bool(elab_dir) and gendry_bind_out(elab_dir) is not None
    if ok:
        return "LIST PRE-MODE bound"
    names = [n for n in BOUND_CHECKS if n.split("-")[0] not in {x.upper() for x in skip}]
    return f"LIST PRE-MODE plan-only: {len(names)} bound checks downgraded ({', '.join(names)})"


START_SETTLE_LEVEL = "WARN"   # START-SETTLE-1124 (COORD r703): report-only; COORD promotes it to FAIL by an explicit ruling (edit this constant), never by date


def start_settle_bound(sidecar_doc, max_release):
    """collector boot model of reach_relay_plan.reprice_monitor_budget.ready_bound for a given raw release: cycles after
    the raw reset release until the observer's registered ready (raw release + ring training + chain depths)."""
    col = (sidecar_doc or {}).get("collector") or {}
    bud = col.get("boot_budget") or {}
    depths = bud.get("local_registered_depths")
    if not depths or not col.get("root"):
        return None
    train = int(bud.get("ring_train_max_cycles", 21))
    ch = {}
    for e in col.get("edges", []):
        ch.setdefault(e["dst"], []).append(e)
    memo = {}

    def deadline(part):
        if part not in memo:
            arr = [max_release + train]
            for e in ch.get(part, ()):
                t = e["boot_transport_extra_cycles"]
                if e.get("seam"):
                    t = train + e.get("monitor_relay_cycles", 0)
                arr.append(deadline(e["src"]) + t)
            memo[part] = max(arr) + depths[part]
        return memo[part]
    return deadline(col["root"])


def startsettle_sidecar(tree, sidecar=None, asbuilt=None):
    """the landing sidecar START-SETTLE reads (--sidecar, else the as-built clock_landing_table), None when there is none"""
    sc = sidecar
    if not sc and asbuilt:
        ab = _load(asbuilt) or {}
        t = ab.get("clock_landing_table")
        if t:
            sc = str(t if os.path.isabs(t) else Path(tree) / t)
    return sc if sc and Path(sc).is_file() else None


def startsettle_types(raw):
    """the types reset_tree.wf_plan solves for START-SETTLE (wavefront plans): the type of every partition of a non-hard type"""
    if ((raw or {}).get("reset") or {}).get("release") != "wavefront":
        return []
    pt = raw.get("partition_types") or {}
    parts = raw.get("partitions") or []
    return sorted({p.get("type") for p in parts if isinstance(p, dict) and p.get("type") in pt
                   and not (pt[p["type"]] or {}).get("hard")})

def check_startsettle(tree, plan, sidecar=None, asbuilt=None, today=None, max_release=None):
    """START-SETTLE-1124: the die START is ot_dp_landing_root #(SETTLE = count_aligned.root_settle_cycles) and every child
    origin leaves reset at its wavefront release, so SETTLE must be >= the collector ready bound at the plan's actual max
    release (raw release + 21 ring training + chain depths), and the sidecar boot_budget must carry that release.
    Always START_SETTLE_LEVEL (WARN: report-only until COORD rules otherwise).  No sidecar / no collector: WARN, not run."""
    lvl = START_SETTLE_LEVEL
    sc = startsettle_sidecar(tree, sidecar, asbuilt)
    if not sc:
        return ["WARN START-SETTLE check not run: no landing sidecar (--sidecar or as-built clock_landing_table)"]
    try:
        doc = json.loads(Path(sc).read_text())
        if max_release is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import schema as _S
            import reset_tree as _RT
            # RESET-TREE-CACHE-1124 (profile: 1929 s on its own Plan): the shared Plan the prewarm solved the die wavefront on, inputs read
            # from --tree like the other reset classes; wf_plan's per-type trees come from the reset-tree cache
            P = _shared_plan(plan, _load(plan))
            if not _RT.wavefront(P):
                return []
            max_release = int(_in_tree(tree, lambda: _RT.wf_plan(P))["max_release"])
        need = start_settle_bound(doc, max_release)
        have = int(((doc.get("count_aligned") or {}).get("root_settle_cycles")) or 64)
        bud = ((doc.get("collector") or {}).get("boot_budget") or {})
    except Exception as e:  # noqa: BLE001
        return [f"WARN START-SETTLE check not run: {type(e).__name__}: {str(e)[:200]}"]
    if need is None:
        return [f"WARN START-SETTLE check not run: sidecar {sc} has no collector boot_budget local_registered_depths"]
    out = []
    if have < need:
        out.append(f"{lvl} START-SETTLE root_settle_cycles {have} < ready bound {need} (max release {max_release} + ring train + chain "
                   f"depths): START (ot_dp_landing_root SETTLE) can fire before the last partition leaves reset; set "
                   f"count_aligned.root_settle_cycles >= {need} in {sc} (report-only: {lvl})")
    if int(bud.get("raw_reset_release_max_cycles", -1)) != max_release:
        out.append(f"{lvl} START-SETTLE boot_budget raw_reset_release_max_cycles {bud.get('raw_reset_release_max_cycles')} != plan max "
                   f"release {max_release} in {sc}")
    return out


def check_deadin(tree, plan, asbuilt):
    """FAIL DEADIN <bind error> when dead_inputs.ProvenDead refuses the as-built's dead-input proofs (see DEADIN-1122)"""
    ab = _load(asbuilt) if asbuilt else None
    if not isinstance(ab, dict) or not ab.get("dead_input_proofs"):
        return []
    raw = _load(plan) or {}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import dead_inputs
        dead_inputs.ProvenDead(ab, tree, {k: dict(v) for k, v in (raw.get("partition_types") or {}).items()})
    except ValueError as e:
        return [f"FAIL DEADIN {e} (bind.py would refuse this after the elab; as-built {asbuilt})"]
    except Exception as e:  # noqa: BLE001 - the bind reports anything else itself
        return [f"WARN DEADIN check not run: {type(e).__name__}: {str(e)[:200]}"]
    return []


# clock keys the density tap solve never reads: kit-side exports only (gen_phys.tap_balance_to_exports -> tap_balance.tcl, TAP-GRID-R5)
TAPNAME_KIT_ONLY_KEYS = ("tap_balance_to", "tap_slowest_max_ps")


def _tap_clock(ck):
    return json.dumps({k: v for k, v in (ck or {}).items() if k not in TAPNAME_KIT_ONLY_KEYS}, sort_keys=True)


_FORK_FN = []


def _fork_one(x):
    return x, _FORK_FN[0](x)


def fork_map(fn, items, jobs=None):
    """{item: fn(item)} computed in a fork pool (reset_tree.pool_size: cores / $OT_RUN_THREADS / free memory; $OT_RESET_POOL_J), serially
    when one worker or one item; fn must not raise and must return a picklable value"""
    items = list(items)
    try:
        import reset_tree as RT
        n = jobs or RT.pool_size(len(items))
    except Exception:  # noqa: BLE001
        n = 1
    if n <= 1 or len(items) < 2:
        return {x: fn(x) for x in items}
    import multiprocessing as _mp
    _FORK_FN[:] = [fn]
    try:
        with _mp.get_context("fork").Pool(n) as pool:
            return dict(pool.imap_unordered(_fork_one, items))
    finally:
        _FORK_FN[:] = []

def check_tapoff(plan, max_list=6):
    """FAIL TAPOFF-MISSING per type whose per-port clock row (clock.tap_offset.per_port_ps, or clock.tap_window.per_port_ps
    for a type without an offsets row) misses a tap port, in EVERY tap mode (tap_offset_cover census; see TAPOFF-1123)."""
    raw = json.loads(Path(plan).read_text())
    ck = raw.get("clock") or {}
    if not ((ck.get("tap_offset") or {}).get("per_port_ps") or (ck.get("tap_window") or {}).get("per_port_ps")):
        return []
    try:
        import tap_offset_cover as TC
        # TAPOFF-POOL-1124 (S81 c8 PRE profile: TAPOFF 1973 s, one serial tap_grid solve per listed type): the per-type port solve
        # (tap_offset_cover.type_ports, the census's own) runs in a fork pool; census() reads the results unchanged
        P = TC.S.Plan(raw, Path(plan))
        tns = sorted({tn for _f, tn, _t in TC.tables(raw) if _in_scope(tn)})
        rows = TC.census(raw, plan, types=None if _SCOPE is None else "^(" + "|".join(re.escape(t) for t in tns) + ")$",
                         port_results=fork_map(lambda tn: TC.type_ports(P, raw, tn), tns))
    except Exception as e:                                  # an unloadable plan is SCHEMA-LOAD's finding, not this one
        return [f"WARN TAPOFF-UNCHECKED {type(e).__name__}: {str(e)[:200]}"]
    out, warn = [], []
    for r in rows:
        if r["status"] == "OK":
            continue
        if r["status"] == "UNEVALUATED" and not r["missing"]:
            warn.append(f"WARN TAPOFF-UNCHECKED {r['type']}: tap grid not solvable ({r['why']}); its added taps all have a row")
            continue
        tbl = "clock.tap_offset.per_port_ps" if r["form"] == "offset" else "clock.tap_window.per_port_ps"
        low = " (tap grid unsolvable: added taps by name, a lower bound)" if r["status"] == "UNEVALUATED" else ""
        out.append(f"FAIL TAPOFF-MISSING {r['type']}: {r['missing']} {r['tap_mode']}-mode tap port(s) without a {tbl} row{low} "
                   f"({r['sample']}{' ...' if r['missing'] > 4 else ''}): they time at the type's full window; fix: python3 -I "
                   f"tools/die_plan/tap_offset_cover.py fill {plan} OUT.json --types '^{r['type']}$'")
    return out + warn


def _monleg_src(raw, max_list, ML):
    """MONLEG-REACH-SRC (S81-MONLEG 11-25, COORD ruling 4, report-only WARN): collector_local_sources whose status points
    (status_pins_xy_um / xy_um, plus the ring-flop band centre) are over 405 um from the relay of their node.  KV A5t7: 79
    sources on 22 types, QC C1n: 4 on 3.  Fix: rows_s81_monleg.py --src (same-depth re-pick), then rows_s81_monleg_src.py
    (relay insertion, status-path latency same or longer) for the rest."""
    s = ML.src_census(raw)
    by = {}
    for tn, i, node, um in s["over"]:
        by.setdefault(tn, []).append((um, i, node))
    out = []
    for tn in sorted(by)[:max_list]:
        w = max(by[tn])
        out.append(f"WARN MONLEG-REACH-SRC {tn}: {len(by[tn])} source(s) over {ML.REACH_UM:.0f} um from their node, worst source #{w[1]} -> "
                   f"{w[2]} {w[0]:.0f} um (report only)")
    if by:
        out.append(f"WARN MONLEG-REACH-SRC-SUMMARY {s['over_reach']} sources on {s['over_reach_types']} types over {ML.REACH_UM:.0f} um "
                   f"({s['over_fail']} over {ML.FAIL_UM:.0f}, max {s['max_um']:.0f}); fix: rows_s81_monleg.py PLAN_IN PLAN_OUT --src, then "
                   f"rows_s81_monleg_src.py for the rest" + (f"; listed {max_list} types" if len(by) > max_list else ""))
    return out


def check_monleg(plan, max_list=8):
    """MONLEG-REACH (S81-MONLEG 11-25, FABLE-RC-S81 af8bee1e, report-only WARN, never a FAIL): the monitor band centre
    (landing_contract.bands.monitor_i) of every collector child is farther than 405 um (METHODOLOGY 12.1e) from the relay of
    collector_children[i].node, the leg that carries the monitor's ready/fault and its reset copy.  c9s: 118 of 259 pairs on
    83 types, 85 pairs on 71 types over 900 um (c8s col_h9_r0_p1-p3 -1009 .. -1073 ps).  Row: rows_s81_monleg.py (0 added
    cycles).  One WARN line per type (worst pair), plus WARN MONLEG-REACH-SUMMARY.  Seconds, reads only."""
    try:
        import rows_s81_monleg as ML
        raw = json.loads(Path(plan).read_text())
        c = ML.census(raw)
    except Exception as e:
        return [f"WARN MONLEG-REACH-UNCHECKED {type(e).__name__}: {str(e)[:200]}"]
    by = {}
    for tn, i, node, um in c["over"]:
        by.setdefault(tn, []).append((um, i, node))
    out = _monleg_src(raw, max_list, ML)
    for tn in sorted(by)[:max_list]:
        w = max(by[tn])
        out.append(f"WARN MONLEG-REACH {tn}: {len(by[tn])} monitor/collector pair(s) over {ML.REACH_UM:.0f} um, worst monitor_{w[1]} -> "
                   f"{w[2]} {w[0]:.0f} um (report only)")
    if by:
        out.append(f"WARN MONLEG-REACH-SUMMARY {c['over_reach']} of {c['pairs']} pairs on {c['over_reach_types']} types over "
                   f"{ML.REACH_UM:.0f} um ({c['over_fail']} pairs on {c['over_fail_types']} types over {ML.FAIL_UM:.0f} um, max "
                   f"{c['max_um']:.0f}); fix: python3 -I tools/die_plan/rows_s81_monleg.py PLAN_IN PLAN_OUT (0 added cycles)"
                   + (f"; listed {max_list} types" if len(by) > max_list else ""))
    return out


def check_ftsite(plan, max_list=8):
    """FTSITE-1124 (S81-OWN-LEAF, report-only, never a FAIL): explicit FT bit sites (ft_slots[*].bit_sites_um) whose cell lies
    outside the kit CORE_AREA (kit_fit.kit_core_area: the no-row core margin, place refuses 'explicit FT site is not on a
    row/site', c8s leaf t24/t28/t40/t74/t75 2784 sites) or that snap onto one grid point (gen refused 'snap to one site',
    c8s leaf t8/t39/t41/t46).  gen's ft_bit_sites.snap_slots(core_box=...) clamps and de-collides them (positions only), so
    this is an early count per type: WARN FTSITE, plus one WARN FTSITE-SUMMARY.  Seconds."""
    try:
        import ft_bit_sites as FB
        from kit_fit import kit_core_area
        raw = json.loads(Path(plan).read_text())
    except Exception as e:
        return [f"WARN FTSITE-UNCHECKED {type(e).__name__}: {str(e)[:200]}"]
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        slots = [x for x in (t.get("ft_slots") or []) if x.get("bit_sites_um")]
        if not slots:
            continue
        try:
            r = FB.site_findings(slots, kit_core_area(t))
        except Exception as e:
            rows.append(f"WARN FTSITE-UNCHECKED {tn}: {type(e).__name__}: {str(e)[:120]}")
            continue
        if r["offcore"] or r["collide"]:
            rows.append((tn, r))
    out = [x for x in rows if isinstance(x, str)]
    hits = [x for x in rows if not isinstance(x, str)]
    for tn, r in hits[:max_list]:
        out.append(f"WARN FTSITE {tn}: {r['offcore']} explicit FT bit site(s) off CORE_AREA, {r['collide']} on an already "
                   f"used grid point ({'; '.join(r['sample'])}); gen clamps / de-collides them (ft_bit_sites.snap_slots "
                   f"core_box), report only")
    if hits:
        out.append(f"WARN FTSITE-SUMMARY {len(hits)} type(s), {sum(r['offcore'] for _, r in hits)} off-core and "
                   f"{sum(r['collide'] for _, r in hits)} colliding explicit FT bit sites"
                   + (f" (listed {max_list})" if len(hits) > max_list else ""))
    return out


def check_tapname(plan, base_fn=None, max_list=6, tree=None, base=None, solve_all=False):
    """FAIL TAPNAME / TAPNAME-RETAP lines (see TAPNAME-1122).  base_fn(P, raw, type) -> density base tap count; injectable.
    TAPNAME-UNCHECKED-1122 (COORD, QC-PLAN-R13 / QC-SLE-R5: run from a bare rt dir the density base inputs were not found, a WARN was
    printed and the broken v3p7d plan reported PASS): the base is solved with the plan's repo-relative inputs read from --tree; a base
    that still cannot be solved is FAIL TAPNAME-UNCHECKED (non-zero, verdict UNCHECKED), never a silent PASS.
    TAPNAME-DELTA-1122 (COORD: on a full QC plan the density solve of every type ran ~1 h CPU per check, a serial hour on every QC bind
    chain): with a base plan (--remap-base / --baseline-plan / bind_of_record) only the density types whose clock section differs from the
    base's (kit-only keys TAPNAME_KIT_ONLY_KEYS aside) are solved; a type whose clock section is identical to the bound base keeps the base's tap names (one WARN line counts them).
    solve_all ($OT_TAPNAME_ALL=1) or no base: every density type is solved."""
    raw = _load(plan)
    if not raw:
        return []
    bty = {}
    if base and not solve_all:
        try:
            bty = _load(base).get("partition_types") or {}
        except (OSError, ValueError):
            bty = {}
    same = 0
    todo = []
    for tn, ty in (raw.get("partition_types") or {}).items():
        ck = (ty or {}).get("clock") or {} if isinstance(ty, dict) else {}
        if ck.get("tap_mode") != "density":
            continue
        refs = [v for v in _tap_ref_names(ck)]
        if ck.get("added_taps") or refs:
            bck = ((bty.get(tn) or {}).get("clock") if isinstance(bty.get(tn), dict) else None)
            if bck is not None and _tap_clock(bck) == _tap_clock(ck):
                same += 1                                # clock section as bound in the base: names already proven there
                continue
            todo.append((tn, ck, refs))
    note = ([f"WARN TAPNAME {same} density type(s) with a clock section identical to base {base} not re-solved "
             f"(OT_TAPNAME_ALL=1 solves all)"] if same else [])
    if not todo:
        return note
    if base_fn is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import schema
        import taps as TP
        _pc = {}

        def base_fn(_P, _raw, tn):
            here, root0 = os.getcwd(), TP._root
            try:
                if tree and Path(tree).is_dir():
                    # plan inputs (sink_bins_file ...) are repo-relative: read them from --tree, not from the tool tree this
                    # checker runs from (a bare rt/<sha> dir holds tools only)
                    os.chdir(tree)
                    TP._root = lambda: Path(tree).resolve()
                if "P" not in _pc:               # a plan the schema cannot load is UNCHECKED too (inside the per-type try)
                    _pc["P"] = _shared_plan(Path(here, plan) if not Path(plan).is_absolute() else Path(plan), raw)
                return len(TP._density_base(_pc["P"], tn))
            finally:
                os.chdir(here)
                TP._root = root0
    out = []
    for tn, ck, refs in todo:
        added = [str((a or {}).get("name")) for a in ck.get("added_taps") or []]
        if not added and not refs:
            continue
        try:
            nb = base_fn(None, raw, tn)
        except Exception as e:  # noqa: BLE001 - the bind reports a density solve error itself
            out.append(f"FAIL TAPNAME-UNCHECKED {tn}: density base not solved ({type(e).__name__}: {str(e)[:160]}); added tap names NOT checked "
                       f"-- re-run with --tree <tree holding the plan inputs> (tree {tree or '-'})")
            continue
        exp = [f"clk_t{nb + i}" for i in range(len(added))]
        wrong = [(a, e) for a, e in zip(added, exp) if a != e]
        if wrong:
            out.append(f"FAIL TAPNAME {tn}: density base gives {nb} taps, so added_taps must be {exp[0]}..{exp[-1]}; "
                       + "; ".join(f"{a} should be {e}" for a, e in wrong[:max_list]))
        names = {"clk"} | {f"clk_t{i}" for i in range(1, nb)} | set(exp)
        bad = sorted({r for r in refs if r not in names or r in {a for a, _ in wrong}}, key=lambda s: int(s[5:]) if s[5:].isdigit() else -1)
        if bad:
            out.append(f"FAIL TAPNAME-RETAP {tn}: clock references name {len(bad)} tap(s) that are not taps of the solved base "
                       f"({nb} density + {len(added)} added): {', '.join(bad[:max_list])}; re-run the tap package (retap) on this base")
    return out + note


_PLAN_OBJ = {}


def _shared_plan(plan, raw):
    """one schema.Plan per (plan file, mtime) in this process: TAPNAME and RESETPUB share its solved taps (the die wavefront reset
    solve taps every type; solving them twice doubled a QC check)"""
    import schema
    pa = Path(plan).absolute()
    try:
        key = (str(pa), pa.stat().st_mtime_ns)
    except OSError:
        key = (str(pa), None)
    if key not in _PLAN_OBJ:
        _PLAN_OBJ.clear()
        _PLAN_OBJ[key] = schema.Plan(json.loads(json.dumps(raw)), pa)
    return _PLAN_OBJ[key]


def _in_tree(tree, fn):
    """run fn() with the plan's repo-relative inputs read from --tree (taps._root + cwd), not from this checker's tool tree"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import taps as TP
    here, root0, env0 = os.getcwd(), TP._root, os.environ.get("OT_REPO_ROOT")
    try:
        if tree and Path(tree).is_dir():
            os.chdir(tree)
            TP._root = lambda: Path(tree).resolve()
            os.environ["OT_REPO_ROOT"] = str(Path(tree).resolve())     # REPO-ROOT-1123 readers (reset_tree pin tables, bind_elab)
        return fn()
    finally:
        os.chdir(here)
        TP._root = root0
        if env0 is None:
            os.environ.pop("OT_REPO_ROOT", None)
        else:
            os.environ["OT_REPO_ROOT"] = env0


def _reset_lineage(tree, net):
    """[(q, d, depth)] from net up to rst_root_n in a published collector_tree (stops at an unknown / cyclic net)"""
    by_q = {r.get("q"): r for r in (tree or {}).get("relays") or [] if isinstance(r, dict)}
    out, seen = [], set()
    while net in by_q and net not in seen and net != "rst_root_n":
        seen.add(net)
        r = by_q[net]
        out.append((net, r.get("d"), r.get("depth")))
        net = r.get("d")
    return out


def _reset_inputs(t):
    """what a type's reset tree is solved from, minus the published tree itself (clock without landing_contract.collector_tree, reset)"""
    ck = json.loads(json.dumps((t or {}).get("clock") or {}))
    (ck.get("landing_contract") or {}).pop("collector_tree", None)
    return json.dumps({"clock": ck, "reset": (t or {}).get("reset")}, sort_keys=True)


def _diff_keys(a, b, pre=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += _diff_keys(a.get(k), b.get(k), f"{pre}.{k}" if pre else str(k))
        return out
    return [] if a == b else [pre or "."]


def check_resetpub(tree, plan, tree_fn=None, max_list=4, base=None, solve=False):
    """RESETPUB-1122 (COORD; QC V3 n3 / cr / b2r binds died at EMIT 'control reset localization sle_sc_v1__cl7479a5ec: rst_n_t0:
    emitted/published reset edge mismatch' after TAP-GRID-R5 clock keys changed and retap.py, seeing no tap-set change, left the
    published tree as it was): for every soft type with reset.consumer_localization and a published clock.landing_contract.
    collector_tree, the reset tree the tools solve now (reset_tree.for_type, the tree the bind emits) is compared with the published
    one along each localized reset's lineage -- the edges reset_consumers.localize checks.  A differing edge or depth is
    FAIL RESETPUB (republish: retap.py OLD NEW OUT --types T --republish-reset).  A tree that cannot be solved is FAIL
    RESETPUB-UNCHECKED.  tree_fn(tn) -> solved tree; injectable.
    Cost: the reset solve of a wavefront plan solves the whole die (QC v3p6n3: not done after 3400 s, 1 GB), longer than the check may
    take before a bind.  So by default nothing is solved: a SUSPECT type -- its clock / reset inputs differ from the base plan (base =
    --remap-base / --baseline-plan / bind_of_record) while its published collector_tree is byte-identical to the base's (inputs moved,
    tree not republished: the V3 case, tap_balance_to + tap_slowest_max_ps) -- is FAIL RESETPUB in seconds, naming the moved keys.
    Clear it by republishing (retap.py BASE PLAN OUT --types T --republish-reset), or prove the tree unchanged with solve=True
    ($OT_RESETPUB_SOLVE=1: every localized type is solved and compared edge by edge), or --skip RESETPUB when the moved keys provably do
    not reach the reset tree.  No base and no solve: nothing is checked."""
    raw = _load(plan)
    braw = None
    if base and not solve:
        try:
            braw = _load(base).get("partition_types") or {}
        except (OSError, ValueError):
            braw = None
    todo = resetpub_todo(raw, braw, solve, max_list)
    if not todo:
        return []
    return _resetpub_solve(tree, plan, raw, todo, tree_fn, max_list, solve)


def resetpub_todo(raw, braw, solve, max_list=4):
    """[(type, published tree, nets)] check_resetpub judges; with solve every one is solved (reset_tree.for_type)"""
    todo = []
    for tn, ty in (raw.get("partition_types") or {}).items():
        if not isinstance(ty, dict) or ty.get("hard"):
            continue
        loc = (ty.get("reset") or {}).get("consumer_localization") or []
        pub = ((ty.get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
        if not loc or not isinstance(pub, dict) or pub.get("hard") or not pub.get("relays"):
            continue
        nets = sorted({str(c.get("new_reset")) for c in loc if isinstance(c, dict) and c.get("new_reset")})
        if not nets:
            continue
        if not solve:
            bt = (braw or {}).get(tn)
            if not isinstance(bt, dict):
                continue
            bpub = ((bt.get("clock") or {}).get("landing_contract") or {}).get("collector_tree")
            if _reset_inputs(ty) == _reset_inputs(bt) or json.dumps(bpub, sort_keys=True) != json.dumps(pub, sort_keys=True):
                continue                                 # inputs unchanged, or the tree was republished with them
            nets = nets + ["@" + ",".join(_diff_keys(json.loads(_reset_inputs(bt)), json.loads(_reset_inputs(ty)))[:max_list])]
        todo.append((tn, pub, nets))
    return todo


def _resetpub_solve(tree, plan, raw, todo, tree_fn, max_list, solve):
    if tree_fn is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import schema
        import reset_tree as RT
        _pc = {}

        def tree_fn(tn):
            def solve():
                if "P" not in _pc:
                    _pc["P"] = _shared_plan(plan, raw)
                return RT.for_type(_pc["P"], tn)
            return _in_tree(tree, solve)
    out = []
    for tn, pub, nets in todo:
        why = next((n[1:] for n in nets if n.startswith("@")), "")
        nets = [n for n in nets if not n.startswith("@")]
        if not solve:
            out.append(f"FAIL RESETPUB {tn}: clock / reset inputs changed vs base ({why}) but the published collector_tree is byte-identical "
                       f"to the base's (localized resets {', '.join(nets[:max_list])}): the bind emits the tree solved on the new inputs and dies at "
                       f"EMIT 'emitted/published reset edge mismatch' when it differs -- republish: retap.py BASE PLAN OUT --types {tn} "
                       f"--republish-reset (or prove it unchanged: OT_RESETPUB_SOLVE=1, die-wide solve, slow; or --skip RESETPUB)")
            continue
        try:
            new = tree_fn(tn)
        except Exception as e:  # noqa: BLE001 - the bind reports a reset solve error itself; the published tree is unchecked
            out.append(f"FAIL RESETPUB-UNCHECKED {tn}: reset tree not solved ({type(e).__name__}: {str(e)[:160]}); published collector_tree "
                       f"NOT checked -- re-run with --tree <tree holding the plan inputs>")
            continue
        sol = {r.get("q"): r for r in (new or {}).get("relays") or [] if isinstance(r, dict)}
        bad = []
        for net in nets:
            for q, d, dp in _reset_lineage(pub, net):
                s = sol.get(q)
                if s is None:
                    bad.append(f"{q} published d={d}, solved tree has no relay {q}")
                elif s.get("d") != d or (dp is not None and s.get("depth") is not None and s.get("depth") != dp):
                    bad.append(f"{q} published d={d} depth={dp}, solved d={s.get('d')} depth={s.get('depth')}")
        bad = list(dict.fromkeys(bad))
        if bad:
            out.append(f"FAIL RESETPUB {tn}: published collector_tree is stale against the reset tree the bind emits ({len(bad)} edge(s) on the "
                       f"localized resets {', '.join(nets[:max_list])}" + (f"; inputs changed vs base: {why}, tree not republished" if why else "")
                       + "): " + "; ".join(bad[:max_list])
                       + " -- the bind dies at EMIT 'emitted/published reset edge mismatch'; republish: retap.py OLD NEW OUT --types "
                       f"{tn} --republish-reset")
    return out


def _tap_ref_names(ck):
    """clk_t<k> names the clock section references outside the tap tables (landing_remap.tap_refs rule)"""
    out = []

    def walk(o):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if isinstance(k, str) and k in ("taps", "added_taps"):
                continue
            if isinstance(v, str) and re.match(r"^clk_t\d+$", v):
                out.append(v)
            else:
                walk(v)
    walk(ck)
    return out


def remap_base(plan, explicit=None, baseline=None):
    """(path, how) of the LANDREMAP / ISTCYC base (REMAP-BASE-1122); (None, why) when none resolves or it is the plan itself"""
    cands = [(explicit, "--remap-base"), (baseline, "--baseline-plan"), (os.environ.get("OT_PLAN_REMAP_BASE"), "$OT_PLAN_REMAP_BASE")]
    try:
        prov = json.loads((Path(plan).parent / "bind_of_record" / "provenance_bind.json").read_text())["provenance"]["plan"]
        cands.append((prov, "bind_of_record/provenance_bind.json"))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for c, how in cands:
        if not c:
            continue
        try:
            if not Path(c).is_file():
                continue
            if Path(c).resolve() == Path(plan).resolve() or Path(c).read_bytes() == Path(plan).read_bytes():
                return None, f"{how} {c} is the plan itself"
        except OSError:
            continue
        return str(c), how
    return None, "no base (pass --remap-base, set $OT_PLAN_REMAP_BASE, or keep the tree bind_of_record)"


def _src_def(text, name):
    """the source of top-level `def NAME` in TEXT, or ''"""
    m = re.search(r"(?ms)^def " + re.escape(name) + r"\(.*?(?=^\S)", text + "\nEND\n")
    return m.group(0) if m else ""


def emit_name_fns(tree):
    """(landing_name(pn), bind_name(pn)) of the TREE's tools, without importing them: bind.emit_top writes partition instance
    sv_id(pn); the clock-landing pass looks for the expression it re-escapes right before 'expected exactly one bound instance'.
    None when the tree's tools do not have that form."""
    d = Path(tree) / "tools" / "die_plan"
    try:
        bt, ct = (d / "bind.py").read_text(), (d / "clock_landings.py").read_text()
    except OSError:
        return None
    i = ct.find("expected exactly one bound instance")
    if i < 0:
        return None
    m = list(re.finditer(r"re\.escape\(((?:[^()]|\([^()]*\))*)\) \+ r\" \\\(", ct[max(0, i - 1500):i]))
    if not m:
        return None
    expr = m[-1].group(1)
    ns = {"re": re}
    try:
        for fn in ("ident", "bind_inst_id"):
            src = _src_def(ct, fn)
            if src:
                exec(src, ns)                            # noqa: S102 - the tree's own helper definitions (pure string functions)
        exec(_src_def(bt, "sv_id"), ns)                  # noqa: S102
        land = eval("lambda pn: " + expr, ns)            # noqa: S307
        return land, ns["sv_id"]
    except Exception:  # noqa: BLE001
        return None


def _bind_type_rtl(rtl, tn):
    """the bind's per-type RTL file for type tn (<die>p_<tn>.sv, or <tn>_part.sv for a type_split piece)"""
    hits = [p for p in (rtl / f"{tn}_part.sv",) if p.is_file()] or sorted(rtl.glob(f"*p_{tn}.sv"))
    return hits[0] if len(hits) == 1 else None


def seat_bind_is_of_plan(plan, bind_dir):
    """True when the finished bind in bind_dir was made from this plan file (sha256 in bind_report / provenance, else the same path)"""
    sha = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    for n in ("provenance_bind.json", "plan_gate_pre.json", "bind_report.json"):
        d = _load(Path(bind_dir) / n)
        if not isinstance(d, dict):
            continue
        txt = json.dumps({k: v for k, v in d.items() if k in ("provenance", "plan", "plan_sha256", "sha256", "plan_sha")})
        if sha in txt:
            return True
        pp = (d.get("provenance") or {}).get("plan") if isinstance(d.get("provenance"), dict) else None
        if pp and Path(pp).is_file() and hashlib.sha256(Path(pp).read_bytes()).hexdigest() == sha:
            return True
    return False


def check_seatmatch(plan, bind_dir, baseline=None):
    """SEATMATCH-1124 lines (see the doc); no finished bind RTL = not run"""
    out = gendry_bind_out(bind_dir)
    if not out or not (Path(out) / "rtl").is_dir():
        return []
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import seat_match as SM
    try:
        base = json.loads(Path(baseline).read_text()) if baseline else None
        return SM.findings(_load(plan) or {}, Path(out) / "rtl", base, seat_bind_is_of_plan(plan, out))
    except Exception as e:  # noqa: BLE001 - a checker crash names itself, it never passes silently
        return [f"WARN SEATMATCH not checked: {type(e).__name__}: {str(e)[:200]}"]


def check_macroghost(plan, bind_dir, max_list=4):
    """MACROGHOST-1122 (OPUS-FIX-S81-SVC-R9, COORD 18:0x): placed macro rows (contents with a lef, path u_bound.<inst>...)
    with no instance in the bound the kit will build.  Checked against the per-type RTL of the bind in BIND_DIR/rtl
    (the --elab-dir bind), so the PLAN-SRC-MACRO class (a certain place_macro failure at kit place, kit_contract
    macro_instances) is found before any kit.  The svc memory closure creates capture / staging-fit instances
    after bind: those rows count as bound when the closure step of their group applies to that bound
    (s81_svc_mem_cones.predict_steps: all four T7 helpers = class port, else the structural per-helper steps), else
    FAIL (ghost: e.g. pvq_capture rows on a narrow-pvq bound).  Any other row whose first component is no instance of
    the bound is a WARN (another kit-RTL step may create it).  No BIND_DIR/rtl = not run."""
    if not bind_dir or not (Path(bind_dir) / "rtl").is_dir():
        return []
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import s81_svc_mem_cones as CONES
    rtl = Path(bind_dir) / "rtl"
    raw = _load(plan) or {}
    fails, warns = [], []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        rows = [r for r in t.get("contents") or [] if r.get("lef") is not None and str(r.get("inst", "")).startswith("u_bound.")]
        if not rows:
            continue
        f = _bind_type_rtl(rtl, tn)
        if f is None:
            continue
        text = f.read_text(errors="replace")
        insts = set(re.findall(r"(\w+)\s+\(", text))
        steps = CONES.predict_steps(text)
        ghost, other = [], []
        for r in rows:
            g = CONES.plan_row_group(r["inst"])
            first = re.sub(r"(\[[^\]]*\])+$", "", r["inst"].split(".")[1])
            if g is not None:
                if g not in steps:
                    ghost.append(f"{r['inst']} ({g} not closed: bound steps {','.join(sorted(steps)) or 'none'})")
            elif first not in insts:
                other.append(r["inst"])
        if ghost:
            fails.append(f"FAIL MACROGHOST {tn}: {len(ghost)} placed macro row(s) with no bound instance after the svc "
                         f"memory closure ({f.name}); drop them or close the cone: " + "; ".join(ghost[:max_list]))
        if other:
            warns.append(f"WARN MACROGHOST {tn}: {len(other)} placed macro row(s) whose first component is no instance "
                         f"of {f.name}: " + "; ".join(other[:max_list]))
    return fails + warns


def check_emitname(tree, plan, asbuilt=None):
    """FAIL EMITNAME (FABLE-FLOW-0230 B1: FLOW-STRIPBODY-R2 1.9 h, then 'EMIT clock landing: expected exactly one bound instance'):
    with a clock landing table, the partition instance name the landing pass looks for must equal the one bind.emit_top writes,
    and no two partitions may share an instance name.  Seconds, before the elab."""
    raw = _load(plan) or {}
    ab = _load(asbuilt) if asbuilt else raw.get("asbuilt")
    if not isinstance(ab, dict) or not ab.get("clock_landing_table"):
        return []
    fns = emit_name_fns(tree)
    if fns is None:
        return ["WARN EMITNAME clock-landing / bind instance-name form not readable from the tree's tools: not checked"]
    land, bind_id = fns
    out, seen = [], {}
    for p in raw.get("partitions") or []:
        pn = p.get("name") if isinstance(p, dict) else None
        if not pn:
            continue
        try:
            a, b = land(pn), bind_id(pn)
        except Exception as e:  # noqa: BLE001
            return [f"WARN EMITNAME not checked: {type(e).__name__}: {e}"]
        if a != b:
            out.append(f"FAIL EMITNAME partition {pn}: the clock-landing pass looks for instance {a}, bind writes {b} -- the bind stops "
                       f"at EMIT ('clock landing: expected exactly one bound instance'); run the bind on tools where both agree")
        if b in seen:
            out.append(f"FAIL EMITNAME partitions {seen[b]} and {pn} share the bound instance name {b} (two matches at EMIT)")
        seen.setdefault(b, pn)
    return out[:12] + ([f"FAIL EMITNAME ... {len(out) - 12} more"] if len(out) > 12 else [])


def check_anchordry(tree, plan, base=None, solve=False, tree_fn=None, ported_fn=None):
    """ANCHORDRY-1123 lines (see the doc): anchor_dry.static_findings vs BASE; with solve, anchor_dry.dry_rows too."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import anchor_dry as AD
    raw = _load(plan) or {}
    if not any(((t or {}).get("clock") or {}).get("reset_tree_anchor") for t in (raw.get("partition_types") or {}).values()):
        return []
    try:
        braw = _load(base) if base else None
    except (OSError, ValueError) as e:
        return [f"WARN ANCHORDRY base {base} not readable ({type(e).__name__}); not checked"]
    out = AD.static_findings(raw, braw)
    if solve:
        if tree_fn is None:
            import reset_tree as RT
            P = _shared_plan(plan, raw)
            tree_fn = lambda tn: _in_tree(tree, lambda: RT.for_type(P, tn))  # noqa: E731
        root = str(Path(tree).resolve()) if tree else str(Path(__file__).resolve().parents[2])
        out += AD.dry_findings(AD.dry_rows(root, raw, plan, tree_fn=tree_fn, **({"ported_fn": ported_fn} if ported_fn else {})))
    return out


def gendry_types(plan_raw, base_raw, env=None):
    """types whose partition_types entry differs from the baseline (or $OT_PRE_GENDRY_TYPES), sorted"""
    env = os.environ if env is None else env
    named = [t for t in (env.get("OT_PRE_GENDRY_TYPES") or "").split(",") if t]
    if named:
        return sorted(t for t in named if t in plan_raw.get("partition_types", {}))
    if base_raw is None:
        return []
    pt, bt = plan_raw.get("partition_types", {}), base_raw.get("partition_types", {})
    return sorted(t for t, v in pt.items() if json.dumps(v, sort_keys=True) != json.dumps(bt.get(t), sort_keys=True))


def gendry_kitrtl_types(plan_raw, types):
    """GENDRY-KITRTL-1123: the given types that only the bound RTL can build (buses, but no bus.leaf and no contents[].bind)"""
    pt = plan_raw.get("partition_types", {})
    out = []
    for tn in types:
        t = pt.get(tn) or {}
        if (t.get("buses") and not any(b.get("leaf") for b in t["buses"])
                and not any(c.get("bind") for c in t.get("contents", []))):
            out.append(tn)
        elif gendry_plan_unbound_pads(t):                # GENDRY-PADBIND-1124: pads only the bound RTL binds
            out.append(tn)
    return out


GENDRY_WAVE_MODES = ("bind", "script", "plan")


def gendry_wave_mode(raw, env):
    """GENDRY-WAVEMODE-1124 (QC-GENDRY-TRIAGE, COORD f8832eb7): -> (kit-RTL mode of the die's wave, how known) so the dry gen takes the
    path the wave takes.  The wave (kit_wave.py) builds EVERY non-core type of a die whose kit_rtl mode is bind / script from the
    bound RTL (bind.py kit-rtl, then gen.py phys --kit-rtl), whatever its buses carry; only a die without kit_rtl uses the plan wrapper.
    $OT_PRE_KIT_RTL_MODE (bind / script / plan) wins; else kit_wave.json dies.<die>.kit_rtl.mode ($OT_KIT_WAVE_JSON or
    ~/coord/autopilot/kit_wave.json; a listed die without kit_rtl = plan); else, for a named die, bind (every live wave die runs
    kit_rtl bind or script, and kit_wave.json lives on the hub only); a plan naming no die -> (None, ...) = the per-type classifier."""
    v = (env.get("OT_PRE_KIT_RTL_MODE") or "").strip().lower()
    if v in GENDRY_WAVE_MODES:
        return v, "$OT_PRE_KIT_RTL_MODE"
    die = (raw.get("die") or {}).get("name") if isinstance(raw.get("die"), dict) else None
    if not die:
        return None, "plan names no die"
    kw = env.get("OT_KIT_WAVE_JSON") or os.path.expanduser("~/coord/autopilot/kit_wave.json")
    try:
        dies = json.loads(Path(kw).read_text()).get("dies") or {}
    except (OSError, ValueError):
        dies = None
    if isinstance(dies, dict) and isinstance(dies.get(die), dict):
        kr = dies[die].get("kit_rtl") if isinstance(dies[die].get("kit_rtl"), dict) else {}
        m = kr.get("mode") if kr.get("mode") in ("bind", "script") else "plan"
        return m, f"kit_wave.json dies.{die}.kit_rtl.mode"
    return "bind", f"default for die {die} (kit_wave.json not readable here; every live wave die runs kit_rtl bind/script)"


def gendry_plan_unbound_pads(t):
    """GENDRY-PADBIND-1124: the type's pads that no contents[].bind names (bound only in the bound RTL, e.g. bump_ports)"""
    used = {k for c in t.get("contents") or [] for k in (c.get("bind") or {}).values()}
    return [p["name"] for p in t.get("pads") or [] if isinstance(p, dict) and p.get("name") and f"pad:{p['name']}" not in used]


def gendry_native_observer(plan_raw, sidecar):
    """GENDRY-OBSERVER-1123 (PRE-QC-GENCHECK): False when the landing sidecar's observer module is not a plan contents leaf of the
    observer partition's type (QC glue: qfd_sys_face_lctx3_wrapped exists only in the bound RTL).  gen_rtl's plan-native landed
    emitter then refuses EVERY type (Landings.validate_observer_native); kit_wave builds such a die only through bind.py kit-rtl +
    gen.py --kit-rtl.  True when there is no sidecar / observer, or it cannot be read (the generator names that error)."""
    try:
        obs = ((json.loads(Path(sidecar).read_text()).get("collector") or {}).get("observer") or {}) if sidecar else {}
    except (OSError, ValueError, AttributeError):
        return True
    pn, mod = obs.get("part"), obs.get("module")
    parts = plan_raw.get("partitions") or {}
    tn = (parts.get(pn) or {}).get("type") if isinstance(parts, dict) else next(
        (p.get("type") for p in parts if isinstance(p, dict) and pn in (p.get("name"), p.get("inst"))), None)
    t = plan_raw.get("partition_types", {}).get(tn)
    if not mod or not isinstance(t, dict):
        return True
    return sum(1 for c in t.get("contents") or [] if c.get("module") == mod) == 1


def gendry_bind_out(elab_dir):
    """the finished, error-free bind OUT dir (bind_report.json with no errors) the kit-rtl step reads, else None"""
    f = Path(elab_dir) / "bind_report.json" if elab_dir else None
    if not f or not f.is_file():
        return None
    try:
        r = json.loads(f.read_text())
    except (OSError, ValueError):
        return None
    return str(Path(elab_dir).absolute()) if not r.get("errors") and not r.get("n_errors") else None


def gendry_src_tree(tree):
    """GENDRY-PADBIND-1124: the design source tree bind.py kit-rtl checks the kit filelist against.  An rt launch tree
    (rt_launch_tree.sh: L/.rt_launch_ok {"src": SRC}) symlinks rtl/ and physical/* into SRC, so the filelist resolves under SRC
    and --src-tree L refuses every file ('outside the kit source tree', QC C1g glue); the wave passes the die tree SRC too."""
    try:
        src = json.loads((Path(tree) / ".rt_launch_ok").read_text()).get("src")
    except (OSError, ValueError, AttributeError):
        src = None
    return str(Path(src).absolute()) if src and Path(src).is_dir() else str(Path(tree).absolute())


def gendry_kitrtl_cmd(tree, plan, tn, kit, bind_out, asbuilt=None):
    bind = Path(__file__).resolve().parent / "bind.py"
    cmd = [sys.executable, "-I", "-B", str(bind), "kit-rtl", str(Path(plan).absolute()), "--out", str(bind_out), "--type", tn,
           "--kit", str(kit), "--src-tree", gendry_src_tree(tree)]
    if asbuilt:
        cmd += ["--asbuilt", str(Path(asbuilt).absolute())]
    return cmd


def gendry_cmd(tree, plan, tn, out, sidecar=None, kit_rtl=None, hard=False):
    gen = Path(__file__).resolve().parent / "gen.py"
    cmd = [sys.executable, "-I", "-B", str(gen), "phys", str(Path(plan).absolute()), "--types", tn, "--out", str(out),
           "--rtl-root", str(Path(tree).absolute()), "--trial"]
    if kit_rtl:
        cmd += ["--kit-rtl", f"{tn}={kit_rtl}"]
        if hard:                                         # GENDRY-HARDWRAP-1124: gen phys builds a hard type only as a wrapper
            cmd += ["--hard-wrappers", tn]
    sc = sidecar or (Path(plan).absolute().parent / "source_sidecar.json")
    if sc and Path(sc).is_file():
        cmd += ["--clock-landing", str(Path(sc).absolute())]
    return cmd


def gendry_sidecar(tree, plan, sidecar=None, asbuilt=None, raw=None):
    """GENDRY-STOPITER-1124 (KV-OWN-HUB-R2, COORD): -> (clock-landing sidecar for the dry gen, how chosen).  The wave passes gen
    --clock-landing = the bind as-built's clock_landing_table (kit_wave.apply_bind_landing / asbuilt_clock_landing); PRE passed only
    <plan dir>/source_sidecar.json, which a KV plan dir does not hold, so the dry gen ran with no collector event and
    landing_place met the captured reset solve (kv3_hub_Eo / Wo StopIteration, A5t3 unchanged).  Order: --sidecar; the as-built
    (--asbuilt, else the plan's own section) clock_landing_table, absolute or under the source tree / TREE / the as-built base;
    <plan dir>/source_sidecar.json; else None."""
    if sidecar:
        return str(sidecar), "--sidecar"
    ab, mdir = None, Path(plan).absolute().parent
    if asbuilt:
        try:
            ab = _load(asbuilt)
        except (OSError, ValueError):
            ab = None
        mdir = Path(asbuilt).absolute().parent
    elif isinstance((raw or {}).get("asbuilt"), dict):
        ab = raw["asbuilt"]
    t = ab.get("clock_landing_table") if isinstance(ab, dict) else None
    if isinstance(t, str) and t:
        cands = [Path(t)] if os.path.isabs(t) else [Path(gendry_src_tree(tree)) / t, Path(tree).absolute() / t]
        if not os.path.isabs(t) and ab.get("base") is not None:
            b = Path(ab["base"])
            cands.append((b if b.is_absolute() else mdir / b) / t)
        for f in cands:
            if f.is_file():
                return str(f), "as-built clock_landing_table (as the wave)"
    sc = Path(plan).absolute().parent / "source_sidecar.json"
    if sc.is_file():
        return str(sc), "<plan dir>/source_sidecar.json"
    return None, "none"


def check_gendry(tree, plan, baseline=None, sidecar=None, env=None, runner=None, elab_dir=None, asbuilt=None):
    """GENDRY-1123 lines (see the doc).  runner(cmd, cwd, timeout) -> (rc, text): injectable for tests."""
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    env = os.environ if env is None else env
    try:
        raw = json.loads(Path(plan).read_text())
        base = json.loads(Path(baseline).read_text()) if baseline else None
    except (OSError, ValueError) as e:
        return [f"WARN GENDRY plan/baseline not readable ({type(e).__name__}); not checked"]
    types = gendry_types(raw, base, env)
    if not types:
        return []
    cap = int(env.get("OT_PRE_GENDRY_MAX") or 24)
    jobs = max(1, int(env.get("OT_PRE_GENDRY_J") or 8))
    tmo = int(env.get("OT_PRE_GENDRY_TIMEOUT_S") or 1800)
    run, rest = types[:cap], types[cap:]
    kitrtl = set(gendry_kitrtl_types(raw, run))      # GENDRY-KITRTL-1123
    sc, sc_how = gendry_sidecar(tree, plan, sidecar, asbuilt, raw)                 # the sidecar gendry_cmd passes (GENDRY-STOPITER-1124)
    sidecar = sc
    if sc and Path(sc).is_file() and not gendry_native_observer(raw, sc):               # GENDRY-OBSERVER-1123: kit-rtl like the wave
        kitrtl = {tn for tn in run if not (raw["partition_types"].get(tn) or {}).get("hard")}
    wmode, whow = gendry_wave_mode(raw, env)
    if wmode in ("bind", "script"):                      # GENDRY-WAVEMODE-1124: a kit_rtl die builds every non-core type from bound RTL
        # GENDRY-HARDWRAP-1124 (KV-ALLFIX, kv3_phy_v1): a hard type too.  The wave builds it as a hard wrapper (kit-rtl + gen
        # --kit-rtl --hard-wrappers; gen refuses a hard wrapper without --kit-rtl) or through core_kit, never plan-native.  The
        # native dry gen ran the whole-die landed emitter, whose observer check reads the plan `sources` of the observer type
        # (kv3_hub_C has none: "module qkd_seq_core_static_s not found in kv3_hub_C sources"), a path no kit takes.
        kitrtl = set(run)
    elif wmode == "plan":                                # a die without kit_rtl: the wave uses the plan wrapper for every type
        kitrtl = set()
    bind_out = gendry_bind_out(elab_dir) if kitrtl else None
    out = []
    if kitrtl and not bind_out:
        for tn in sorted(kitrtl):
            out.append(f"WARN GENDRY-KITRTL {tn}: kit-RTL type (no bus.leaf / contents[].bind, a pad no contents[].bind names, or the landing observer is not a "
                       f"plan leaf: the kit builds it from the bound RTL via bind.py kit-rtl); not generated dry without a finished error-free bind OUT (--elab-dir with bind_report.json)")
        run = [tn for tn in run if tn not in kitrtl]

    def _run(cmd, cwd, timeout):
        try:
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=genv)
            return r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            return None, f"timeout after {timeout} s"
    # GENDRY-REPOROOT-1123 (QC cC): these tools may run from rt/<sha> or a lane checkout; repository-relative plan inputs (sink
    # bins, view LEFs) resolve in --tree like the wave's own tree-local tools (REPO-ROOT-1123), not beside the tools
    genv = dict(os.environ, **env)
    genv["OT_REPO_ROOT"] = str(Path(tree).resolve())
    runner = runner or _run
    with tempfile.TemporaryDirectory(prefix="pre_gendry_") as td:
        def one(tn):
            o = Path(td) / tn
            o.mkdir()
            kf = None
            if tn in kitrtl:
                k = Path(td) / f"{tn}.kit_rtl"
                rc, text = runner(gendry_kitrtl_cmd(tree, plan, tn, k, bind_out, asbuilt), str(Path(tree).absolute()), tmo)
                if rc != 0:
                    ln = [x for x in (text or "").splitlines() if x.strip()]
                    e = next((x for x in reversed(ln) if "ERROR" in x or "Error" in x), ln[-1] if ln else "")
                    return tn, (rc, text if rc is None else f"bind kit-rtl ERROR: {e.strip()}")
                kf = k / "kit_rtl.f"
            return tn, runner(gendry_cmd(tree, plan, tn, o, sidecar, kf, bool((raw["partition_types"].get(tn) or {}).get("hard"))),
                              str(Path(tree).absolute()), tmo)
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            res = list(ex.map(one, run))
    for tn, (rc, text) in res:
        if rc == 0:
            continue
        lines = [x for x in (text or "").splitlines() if x.strip()]
        err = next((x for x in reversed(lines) if "ERROR" in x or "Error" in x), lines[-1] if lines else "")
        unm = next((x for x in lines if "LANDING-SOURCE-UNMODELED" in x), None)
        if rc is None:
            out.append(f"WARN GENDRY-UNCHECKED {tn}: kit generator {err}")
        elif unm:                                        # GENDRY-STOPITER-1124: a modelling gap of the dry run, report only
            out.append(f"WARN GENDRY-UNMODELED {tn}: {unm.strip()[unm.strip().find('LANDING-SOURCE-UNMODELED'):][:400]}")
        else:
            out.append(f"FAIL GENDRY {tn}: kit generator rc={rc}: {err.strip()[:400]}")
    if rest:
        out.append(f"WARN GENDRY-UNCHECKED {len(rest)} changed type(s) over the cap {cap} ($OT_PRE_GENDRY_MAX): {', '.join(rest[:12])}")
    nk = len(kitrtl) if not bind_out else 0
    out.append(f"WARN GENDRY-SUMMARY {len(run)} changed type(s) generated dry ({len(kitrtl) - nk} kit-RTL from the bound RTL), "
               f"{nk} kit-RTL classified not generated, {sum(1 for x in out if x.startswith('FAIL'))} failed; "
               f"wave kit_rtl mode {wmode or 'per-type'} ({whow}); clock-landing {sc or '-'} ({sc_how})")
    return out


INPUT_STOP = ("FAIL INPUT-MISSING", "FAIL SCHEMA-UNKNOWN-KEY", "FAIL SCHEMA-LOAD")


def input_stop(findings, env=None):
    """PRE-INPUT-STOP-1124 (COORD; FAM-S81-COL-H9R0 epyc7: 3.5 h of PRE, then FAIL INPUT-MISSING x5 svc sources the fork never got):
    -> a FAIL PRE-INPUT-STOP line when the seconds-scale presence checks (TREEPRE, SCHEMA, INPUT) found a missing input, so the slow
    classes never start; None otherwise.  Triggers: FAIL INPUT-MISSING / SCHEMA-UNKNOWN-KEY / SCHEMA-LOAD and a TREE-SOURCES path
    line (an as-built / .f / bind.f entry missing; the *_sources folder heuristic and TREE-FRESH stay WARN).  A missing input is a
    real blocker: the bind would die on it.  $OT_PRE_INPUT_STOP=0 runs every class anyway."""
    env = os.environ if env is None else env
    if env.get("OT_PRE_INPUT_STOP", "1") == "0":
        return None
    hit = [x for x in findings if x.startswith(INPUT_STOP)
           or (x.startswith("WARN TREE-SOURCES ") and " missing (base " in x)]
    if not hit:
        return None
    lvl = "LIST" if any(x.startswith("FAIL") for x in hit) else "FAIL"     # the verdict is FAIL either way; one FAIL line per cause
    return (f"{lvl} PRE-INPUT-STOP {len(hit)} missing-input finding(s) above; the slow classes were not run (fix the tree: re-fork "
            f"or copy the missing files, then re-run; OT_PRE_INPUT_STOP=0 runs them anyway)")


class PreTimer:
    """PRE-TIME-1124: seconds per class of one check(); a class over $OT_PRE_TIME_TRACE_S (30) prints to stderr as it ends"""
    def __init__(self):
        self.t0 = self.t = time.time()
        self.cur, self.T = None, {}

    def mark(self, label):
        now = time.time()
        if self.cur:
            dt = now - self.t
            self.T[self.cur] = self.T.get(self.cur, 0.0) + dt
            if dt >= float(os.environ.get("OT_PRE_TIME_TRACE_S") or 30):
                print(f"PRE-TIME {self.cur} {dt:.0f} s (PRE at {now - self.t0:.0f} s)", file=sys.stderr, flush=True)
        self.cur, self.t = label, now

    def line(self):
        self.mark(None)
        top = sorted(self.T.items(), key=lambda kv: -kv[1])[:10]
        return f"LIST PRE-TIME {time.time() - self.t0:.0f} s: " + ", ".join(f"{k} {v:.0f}s" for k, v in top)



def reset_solve_types(tree, plan, raw, skip, landremap_base=None, derived_base=None, env=None, sidecar=None, asbuilt=None):
    """RESET-TREE-CACHE-1124 (COORD ruling): {"plan": {type: [classes]}, "base": {type: [classes]}} of the reset trees this check()
    solves, from each class's own selection: LANDREMAP (landremap_types, plan + base; its bind re-pick reads the same plan tree),
    STARTSETTLE (startsettle_types: wf_plan solves every soft type of a wavefront plan; only with a landing sidecar),
    RESETPUB with OT_RESETPUB_SOLVE=1 (resetpub_todo), ANCHORDRY with OT_ANCHORDRY_SOLVE=1 (types with clock.reset_tree_anchor),
    RSTREACH / DERIVEDNAME (derived_drop.reset_tree_types), and ADV-RESET-NAME. TAPNAME only solves density tap grids.
    derived_base is not prewarmed: its trees are read only after an rstnode finding."""
    env = os.environ if env is None else env
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sel = {"plan": {}, "base": {}}

    def add(side, tns, cls):
        for tn in tns:
            sel[side].setdefault(tn, []).append(cls)
    if "LANDREMAP" not in skip and landremap_base:
        braw = _load(landremap_base)
        if raw and braw:
            lt = landremap_types(raw, braw)
            add("plan", lt, "LANDREMAP")
            add("base", lt, "LANDREMAP")
    if "STARTSETTLE" not in skip and startsettle_sidecar(tree, sidecar, asbuilt):
        add("plan", startsettle_types(raw), "STARTSETTLE")
    if "RESETPUB" not in skip and resetpub_solve(plan, env):
        add("plan", [tn for tn, _p, _n in resetpub_todo(raw, None, True)], "RESETPUB")
    if "ANCHORDRY" not in skip and env.get("OT_ANCHORDRY_SOLVE") == "1":
        import reset_anchor as RA
        add("plan", [tn for tn, t in (raw.get("partition_types") or {}).items()
                     if isinstance(t, dict) and (t.get("clock") or {}).get(RA.KEY)], "ANCHORDRY")
    if "ADVISORY" not in skip and env.get("OT_PLAN_ADVISORY", "").lower() != "off":
        import adv_reset_names as RN
        add("plan", (tn for tn, refs in RN.candidates(raw, RN.configured_types(env=env))
                     if any(RN.RELAY.fullmatch(name) for name in refs.values())), "RESET-NAME")
    dcls = [c for c in ("RSTREACH", "DERIVEDNAME") if c not in skip]
    if dcls:
        import derived_drop as DD
        bc = {}

        def broadcast():
            if "v" not in bc:
                import reset_tree as RT
                try:
                    bc["v"] = bool(_in_tree(tree, lambda: RT.start_broadcast(_shared_plan(plan, raw))))
                except Exception:  # noqa: BLE001 - raw_hops then treats rr_t as unjudged, no tree read
                    bc["v"] = False
            return bc["v"]
        add("plan", sorted(DD.reset_tree_types(raw, dcls, broadcast)), "DERIVED")
    return sel


def reset_prewarm(tree, plan, sel, landremap_base=None, *, warmed_plans=None):
    """solve the selected trees once, in a fork pool, into reset_tree's process-wide cache -> LIST line"""
    import schema
    import reset_tree as RT
    t0 = time.time()
    info = []
    for side, path in (("plan", plan), ("base", landremap_base)):
        tns = sorted(sel.get(side) or ())
        if not tns or not path:
            continue
        r = _load(path)
        try:                                             # the plan side is the shared Plan START-SETTLE / RESETPUB / TAPNAME use
            P = _shared_plan(path, r) if side == "plan" else schema.Plan(json.loads(json.dumps(r)), Path(path).parent / "die_plan.json")
            res = _in_tree(tree, lambda: RT.prewarm(P, tns))
        except Exception as e:  # noqa: BLE001 - each class then solves (and reports) on demand
            info.append(f"{side} {len(tns)} type(s) not prewarmed ({type(e).__name__}: {str(e)[:120]})")
            continue
        if warmed_plans is not None:
            warmed_plans[side] = P
        info.append(f"{side} {res['todo']}/{len(tns)} type(s) in {res['seconds']:.0f} s on {res['jobs']} worker(s)")
    return f"LIST RESET-PREWARM {'; '.join(info) or 'nothing to solve'} ({time.time() - t0:.0f} s)"


def reset_cache_line():
    import reset_tree as RT
    if not hasattr(RT, "cache_report"):
        return "LIST RESET-TREE-CACHE not available"
    reads, hits, miss, pre, unread = RT.cache_report()
    return (f"LIST RESET-TREE-CACHE {reads} tree(s) read, {hits} cache hit(s), {miss} solved on demand (not prewarmed), "
            f"{pre} prewarmed, {unread} prewarmed but never read")


def _check_unscoped(tree, plan, sidecar=None, asbuilt=None, compose_tree=None, baseline=None, proofs=(), rows_files=(),
          skip=(), want_list=False, require_asbuilt=False, strict_cores=False, halo=0.0, elab_dir=None, ref_tools=None,
          toolstale_level="FAIL", abspath_level=None, remap=None, gendry=False):
    findings = []
    _pt = PreTimer()
    _pt.mark("REMAPBASE")
    rb, rb_how = remap_base(plan, remap, baseline) if not {"LANDREMAP", "ISTCYC"} <= {s.upper() for s in skip} else (None, "")
    skip = {s.upper() for s in skip}
    _pt.mark("TREEPRE")
    if "TREEPRE" not in skip and os.environ.get("OT_TREE_PRECHECK_RAN") != "1" and (os.environ.get("OT_TREE_PRECHECK") == "on" or "PYTEST_CURRENT_TEST" not in os.environ
                                  and os.environ.get("OT_TREE_PRECHECK") != "off"):   # PRE-SCHEMA-KEYS 11-24: SCHEMA-KEYS / TREE-SOURCES / TREE-FRESH first, report only (r703)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import tree_precheck as _TP
            findings += [x if x.startswith(("WARN ", "LIST ")) else "WARN " + x
                         for x in _TP.findings(tree, plan, asbuilt=asbuilt, out=elab_dir)]
        except Exception as e:  # noqa: BLE001 - a checker crash names itself
            findings.append(f"WARN TREEPRE not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("SCHEMA")
    if "SCHEMA" not in skip:
        findings += check_schema(tree, plan, compose_tree)
    _pt.mark("INPUT")
    if "INPUT" not in skip:
        findings += check_inputs(tree, plan, sidecar, asbuilt, want_list, require_asbuilt)
    _pt.mark(None)
    _stop = input_stop(findings)                       # PRE-INPUT-STOP-1124: missing inputs stop PRE here, in seconds
    if _stop:
        return findings + [_stop, _pt.line()]
    warmed_plans = {}
    _warm = (os.environ.get("OT_RESET_TREE_CACHE", "1") != "0" and os.environ.get("OT_PRE_RESET_PREWARM", "1") != "0"
             and ("PYTEST_CURRENT_TEST" not in os.environ or os.environ.get("OT_PRE_RESET_PREWARM") == "on"))
    if _warm:                                            # RESET-TREE-CACHE-1124: every reset tree the classes below solve, once, in a pool
        _pt.mark("RESETWARM")
        try:
            _sel = reset_solve_types(tree, plan, _load(plan), skip, landremap_base=rb, derived_base=rb or baseline,
                                     sidecar=sidecar, asbuilt=asbuilt)
            _sel = scope_selection(_sel, _SCOPE)
            findings.append(reset_prewarm(tree, plan, _sel, landremap_base=rb, warmed_plans=warmed_plans))
        except Exception as e:  # noqa: BLE001 - the classes solve on demand
            findings.append(f"LIST RESET-PREWARM not run: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("TOOLS")
    if "TOOLS" not in skip:
        findings += check_tools(tree)
    _pt.mark("TOOLROOT")
    if "TOOLROOT" not in skip:                           # TOOLROOT-1123: the tools this PRE runs from = the declared rt sha
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import tool_root as _TR
        findings += _TR.check(quiet_undeclared=True)
    _pt.mark("ROWS")
    if "ROWS" not in skip:
        findings += check_rows(plan, baseline, proofs, rows_files)
    _pt.mark("GEOM")
    if "GEOM" not in skip:
        findings += check_geom(plan, halo, strict_cores, baseline)
    _pt.mark("COMPOSEDROP")
    if "COMPOSEDROP" not in skip and baseline:          # COMPOSE-GUARD-1124: baseline rows the plan silently lost (WARN, r703)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import compose_drop_guard as CDG
            findings += CDG.findings_for_pre(_load(baseline), _load(plan), os.environ.get("OT_COMPOSE_DROP_LIST") or None,
                                             "FAIL" if os.environ.get("OT_COMPOSE_DROP") == "fail" else "WARN")
        except Exception as e:  # noqa: BLE001 - a checker crash names itself
            findings.append(f"WARN COMPOSEDROP not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("LANDREMAP")
    if "LANDREMAP" not in skip:                          # LANDREMAP-1122: seconds, before any bind
        findings += check_landremap(plan, rb, tree=tree)
    _base = None
    _pt.mark("RESETBASE")
    if {"TAPNAME", "RESETPUB"} - skip:
        _base = rb if rb else remap_base(plan, remap, baseline)[0]
    _pt.mark("TAPNAME")
    if "TAPNAME" not in skip:                            # TAPNAME-1122: density added tap names, seconds before the bind
        findings += check_tapname(plan, tree=tree, base=_base, solve_all=os.environ.get("OT_TAPNAME_ALL") == "1")
    _pt.mark("TAPOFF")
    if "TAPOFF" not in skip:                             # TAPOFF-1123: appended taps with no tap_offset row, seconds
        findings += check_tapoff(plan)
    _pt.mark("FTSITE")
    if "FTSITE" not in skip:                             # FTSITE-1124: off-core / colliding explicit FT bit sites, WARN only
        findings += check_ftsite(plan)
    _pt.mark("STRAPREACH")
    if "STRAPREACH" not in skip:                         # STRAP-REACH (C-STRAP-REACH 1126): CA / count strap group seat vs its load cluster; OT_STRAP_REACH=fail blocks
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s81_head"))
            import head_count_strap_reach as _SRC
            if (Path(plan).resolve().parent / "published").is_dir():
                findings += _SRC.findings_for_pre(_load(plan) or {}, plan, level="FAIL" if os.environ.get("OT_STRAP_REACH") == "fail" else "WARN")
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, never fails PRE
            findings.append(f"WARN STRAP-REACH not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("MONLEG")
    if "MONLEG" in skip:                                 # FP-CONVERGE-S81 11-25 (FABLE-RC-S81): MONLEG-REACH runs in EVERY PRE, not skippable (WARN only)
        findings.append("WARN MONLEG --skip ignored: MONLEG-REACH is not skippable (report only, seconds)")
    findings += check_monleg(plan)
    _pt.mark("STARTSETTLE")
    if "STARTSETTLE" not in skip:                        # START-SETTLE-1124: root settle >= collector ready bound
        findings += check_startsettle(tree, plan, sidecar, asbuilt)
    _pt.mark("DEADIN")
    if "DEADIN" not in skip:                             # DEADIN-1122: bind dead-input proof checks, before the elab
        findings += check_deadin(tree, plan, asbuilt)
    _pt.mark("ISTCYC")
    if "ISTCYC" not in skip:                             # ISTCYC-1122: touched lanes only, seconds
        findings += check_istcyc(plan, rb)
    _pt.mark("ISTPRICE")
    if "ISTPRICE" in skip:
        findings.append("WARN ISTPRICE --skip ignored: ISTPRICE is not skippable (FABLE FLOW REVIEW 11-23 22:50)")
    try:                                                 # STN-REPRICE-1124: report-only count of lanes with station depth != priced fixed_cycles
        import stn_reprice as _SR
        findings += _SR.check_stnprice(plan, baseline=baseline or rb)
    except Exception as _e:  # noqa: BLE001
        findings.append(f"LIST STNPRICE not counted: {type(_e).__name__}: {str(_e)[:120]}")
    findings += check_istprice(tree, plan, asbuilt)     # ISTPRICE-1123: every lane's stations vs its priced cycles, seconds, never skipped
    _pt.mark("R8STALE")
    if "R8STALE" not in skip:                            # R8STALE-1122: R8 table not re-derived after a station change
        findings += check_r8stale(tree, plan, rb, asbuilt)
    _pt.mark("R8BOUND")
    if "R8BOUND" not in skip:                            # R8BOUND-1124: table bound vs plan lane cycles, report-only
        try:
            findings += check_r8bound(tree, plan, asbuilt)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, never fails PRE
            findings.append(f"WARN R8BOUND not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("HALOCORNER")
    if "HALOCORNER" not in skip:                         # HALOCORNER-1125: relay sites / reset nodes on shared halo corners, report-only
        try:
            findings += check_halocorner(plan)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, never fails PRE
            findings.append(f"WARN HALOCORNER not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("TAPREACH")
    if "TAPREACH" not in skip:                           # TAPREACH-1126: every FIRM seat within tap_radius of a tap, report-only
        try:
            findings += check_tapreach(plan)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, never fails PRE
            findings.append(f"WARN TAPREACH not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("STALETABLE")
    if "STALETABLE" not in skip:                         # STALETABLE-1126: derived tables == re-derived, advisory
        try:
            findings += check_staletable(plan)
        except Exception as e:  # noqa: BLE001
            findings.append(f"WARN STALETABLE not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("ABSTRACT-BLANKET-OBS")
    if "ABSTRACT-BLANKET-OBS" not in skip:               # ABSTRACT-EXACT-1125: blanket routing-layer OBS on bound hard-core views, report-only
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import abstract_exact as _AE
            findings += _AE.findings(_load(plan) or {}, tree)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, never fails PRE
            findings.append(f"WARN ABSTRACT-BLANKET-OBS not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("CABIND")
    if "CABIND" not in skip and sidecar:                 # CABIND-1125: sidecar count_aligned vs plan (relay stages ...), every mismatch, seconds
        try:
            findings += check_cabind(plan, sidecar)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself
            findings.append(f"WARN CABIND not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("EMITNAME")
    if "EMITNAME" not in skip:                           # B1 (FABLE-FLOW-0230): clock-landing EMIT instance names, seconds
        findings += check_emitname(tree, plan, asbuilt)
    _pt.mark("MACROGHOST")
    if "MACROGHOST" not in skip:                         # MACROGHOST-1122: placed macros with no bound instance (needs --elab-dir bind rtl)
        findings += check_macroghost(plan, elab_dir)
    _pt.mark("SEATMATCH")
    if "SEATMATCH" not in skip:                          # SEATMATCH-1124: relay_sites keys vs the bound RTL (needs --elab-dir bind)
        findings += check_seatmatch(plan, elab_dir, rb or baseline)
    _pt.mark("RESETPUB")
    if "RESETPUB" not in skip:                           # RESETPUB-1122: published reset tree vs the tree the bind emits
        findings += check_resetpub(tree, plan, base=_base,
                                   solve=resetpub_solve(plan))
    _pt.mark("ANCHORDRY")
    if "ANCHORDRY" not in skip:                          # ANCHORDRY-1123: anchored reset depths vs the remap base, seconds
        _abase = _base if _base else (rb if rb else remap_base(plan, remap, baseline)[0])
        findings += check_anchordry(tree, plan, base=_abase, solve=os.environ.get("OT_ANCHORDRY_SOLVE") == "1")
    _pt.mark("GENDRY")
    if gendry and "GENDRY" not in skip:                  # GENDRY-1123: changed types run the kit generator dry (CLI default)
        findings += check_gendry(tree, plan, baseline, sidecar, elab_dir=elab_dir, asbuilt=asbuilt)
    _pt.mark("SITEGRID")
    if "SITEGRID" not in skip:                           # SITEGRID-1123: exact bank sites on the kit site/row lattice, seconds
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import site_grid as SG
        findings += SG.findings(_load(plan) or {})
    _pt.mark("DEPTH")
    if "DEPTH" not in skip:                              # DEPTH-PRE-1123: generated constructor netlists within the logic-depth budget
        findings += check_depth(tree, plan, asbuilt)
    _pt.mark("ABSPATH")
    if "ABSPATH" not in skip:                            # ABSPATH-1122: inputs that die with a snapshot tree
        findings += abspath_findings(plan, tree, sidecar, abspath_level, already="\n".join(findings))
    _pt.mark("KITFIT")
    if "KITFIT" not in skip:                             # KITFIT-1116: every hard core at its kit offset (origin + track_offset), every type
        sys.path.insert(0, str(Path(__file__).resolve().parent))          # -I drops the script dir
        import kit_fit as KF
        findings += ["FAIL " + m for m in KF.findings((_load(plan) or {}).get("partition_types") or {}, halo)]
    _pt.mark("BIND_ROWCHECK")
    if not set(skip) >= {"FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "RELAYSINK"}:       # BIND-SPEED-1118: bind_rowcheck.py, seconds
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bind_rowcheck as RC
        findings += RC.check_all(tree, plan, _load(plan), asbuilt, elab_dir, ref_tools, skip, toolstale_level)
    _pt.mark("DERIVED_DROP")
    if {"RSTREACH", "DERIVEDNAME", "ENTRYFOOT"} - skip:              # DERIVED-DROP-1123: derived sections a re-floor / tap rewrite left stale
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import derived_drop as DD
        try:
            params = __import__("inspect").signature(DD.findings).parameters
            _ddkw = {"scope": _SCOPE} if _SCOPE is not None and "scope" in params else {}
            raw = _load(plan) or {}
            warmed = warmed_plans.get("plan")
            # A row gate can refresh its candidate while PRE runs. Reuse the wavefront only for the exact snapshot
            # and plan-relative input directory DERIVED_DROP would read, with the same pinned tree.
            if warmed is not None and "plan_obj" in params:
                root = Path(tree).resolve() if tree and Path(tree).is_dir() else Path.cwd()
                if warmed.path.parent.resolve() == (root / Path(plan).parent).resolve() and warmed.raw == raw:
                    _ddkw["plan_obj"] = warmed
            findings += DD.findings(raw, plan, tree, [c for c in DD.CLASSES if c not in skip],
                                    bind_rtl=DD.default_bind_rtl(plan, elab_dir), base=rb or baseline, **_ddkw)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, it never passes silently
            findings.append(f"WARN RSTREACH not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("STNXREF")
    if "STNXREF" not in skip:                            # STATION-MOVE-HELPER 11-24: station-derived records, report only (r703)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import station_xref as SX
            _sb = rb or baseline
            findings += SX.findings(_load(plan) or {}, _load(_sb) if _sb else None, plan)
        except Exception as e:  # noqa: BLE001 - a checker crash names itself
            findings.append(f"WARN STNXREF not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("LATPKG")
    if "LATPKG" not in skip:                             # STATION-MOVE-HELPER 11-24: copied-forward latency packages, report only
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import latpkg_check as LPK
            findings += LPK.findings(_load(plan) or {}, plan, tree)
        except Exception as e:  # noqa: BLE001
            findings.append(f"WARN LATPKG not checked: {type(e).__name__}: {str(e)[:200]}")
    _pt.mark("RSTNAMES")
    if "RSTNAMES" not in skip:                           # RST-NAMES-1124: report only
        findings += rstnames_findings(tree, plan, rb or baseline)
    _pt.mark("RSTPIN")
    if "RSTPIN" not in skip:                             # PIN-REACH-1124: report only, never a FAIL
        findings += rstpin_findings(tree, plan)
    _pt.mark("INOUTLINE")
    if "INOUTLINE" not in skip:                          # FP-CONVERGE-S81 11-25 (COORD 06:2x): a coordinate outside the outline is a FAIL
        findings += inoutline_findings(plan)
    _pt.mark("SITE-OFF-OUTLINE")
    if "SITE-OFF-OUTLINE" not in skip:                   # COORD K10 11-25: a site / port pin / clock tap off the outline is a FAIL, never a WARN
        findings += site_off_outline_findings(plan)
    _pt.mark("VIEWOBS")
    if "VIEWOBS" not in skip:                            # C-VIEW-NO-OBS 11-26: a hard-macro LEF with no OBS / no PG pins is a FAIL
        findings += view_obs_findings(plan)
    _pt.mark("ADVISORY")
    if "ADVISORY" not in skip:                           # PRECHECK-R2: static estimator lines (WARN ADV-*), never a FAIL
        findings += advisory_lines(tree, plan, asbuilt, baseline=rb or baseline, scope=_SCOPE,
                                   reset_plan=warmed_plans.get("plan"))
    _pt.mark(None)
    findings.append(pre_mode(elab_dir, skip))                       # PRE-MODE-1124
    findings.append(_pt.line())                         # PRE-TIME-1124: where the PRE time went
    if _warm:
        findings.append(reset_cache_line())
    if rb:
        findings.append(f"LIST REMAP-BASE {rb} ({rb_how})")      # which base LANDREMAP / ISTCYC used (REMAP-BASE-1122)
    return promote_crashes(findings)


INST_NAME = re.compile(r"^\s*(?:\(\*[^*]*\*\)\s*)?([A-Za-z_]\w*)\s*(?:#|[A-Za-z_\\][\w$]*\s*[\(\[])", re.M)


NETLIST_INST = re.compile(r"^\s*([A-Za-z_]\w*)\s+(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?([A-Za-z_]\w*|\\\S+)\s*\(", re.M)



_SCOPE = None            # FP-CONVERGE-S81 11-25: --types: the set of type names this PRE judges (None = every type)


def _in_scope(tn):
    return _SCOPE is None or tn in _SCOPE


# PRE-SPEED-1125 (FLOW-0930 S-04: scoped ROW-PRE 6942-9308 s vs ~1035 s unscoped; pre_S 47 types: STARTSETTLE 3649 s, LANDREMAP 2412 s,
# RESET-TREE-CACHE "416 solved on demand"): --types cut the reset-tree prewarm to the scope while STARTSETTLE (wf_plan solves every soft
# type: a die-wide bound) and LANDREMAP / DERIVED_DROP (every moved / derived type) still read every tree, so ~460 trees were solved
# serially on demand instead of in the pool.  Now a die-wide class keeps all its types in the prewarm, and the per-type classes
# (LANDREMAP, DERIVED_DROP) only judge the scope (their out-of-scope lines were dropped by scope_lines anyway).
DIE_WIDE_RESET = ("STARTSETTLE",)


def scope_selection(sel, scope):
    """the reset_solve_types selection a scoped PRE prewarms: scope types, plus every type a die-wide class (DIE_WIDE_RESET) reads"""
    if scope is None:
        return sel
    wide = DIE_WIDE_RESET
    if os.environ.get("OT_PRE_ADV_SCOPE") == "full" or os.environ.get("OT_ADV_RESETNAME_TYPES"):
        wide += ("RESET-NAME",)
    return {side: {tn: v for tn, v in d.items() if tn in scope or any(c in wide for c in v)} for side, d in sel.items()}


def parse_types(spec, names):
    """'a*,b' / '@file' -> the set of plan type names matching any fnmatch glob (a glob matching nothing is an error)"""
    import fnmatch
    globs = []
    for g in str(spec).split(","):
        g = g.strip()
        if g.startswith("@"):
            globs += [x.strip() for x in Path(g[1:]).read_text().replace(",", "\n").split() if x.strip()]
        elif g:
            globs.append(g)
    out = set()
    for g in globs:
        hit = {n for n in names if fnmatch.fnmatchcase(n, g)}
        if not hit:
            raise ValueError(f"--types {g!r} matches no type of the plan")
        out |= hit
    return out


def scope_lines(lines, scope, names):
    """drop a finding line whose subject types are ALL outside scope; a line naming no type (whole-plan) or one in scope stays"""
    out = []
    for x in lines:
        toks = set(re.findall(r"[A-Za-z0-9_]+", x)) & names
        if toks and not (toks & scope):
            continue
        out.append(x)
    return out


_EXC_RE = re.compile(r"\b[A-Za-z_]*(?:Error|Exception|Exit|Interrupt)\b")


def promote_crashes(lines, env=None):
    """P-FALSE-GREEN-1126 (HEAD-INT-R2, FABLE-INDEP 08:46: MONLEG-REACH-UNCHECKED KeyError 'index' and ADV-RESET-NAME KeyError
    sp5 ended in PASS): a check that CRASHED has judged nothing.  Every WARN line that names an exception class and says
    UNCHECKED / "not checked" becomes FAIL <CHECK>-UNCHECKED, the existing verdict of the other crash-FAILs (TAPNAME, RESETPUB,
    DEPTH, LANDREMAP): PLAN-GATE-PRE UNCHECKED, exit 1, never a reusable PRE record.  Declared coverage limits (a budget or
    cap, no exception named: GENDRY over , ADV budget) stay WARN.  Default ON because a crash is not a
    verdict; OT_PRE_CRASH_WARN=1 restores the old WARN for a lane that must see the other findings of a plan whose check
    cannot run (the line is still printed as UNCHECKED, and the PRE record is marked crash_warn)."""
    env = os.environ if env is None else env
    if env.get("OT_PRE_CRASH_WARN") == "1":
        return lines
    out = []
    for x in lines:
        if x.startswith("WARN ") and len(x.split()) > 1 and _EXC_RE.search(x):
            tok = x.split()[1].rstrip(":")
            if tok.endswith("-UNCHECKED"):
                x = "FAIL " + x[5:]
            elif "not checked" in x:
                x = f"FAIL {tok}-UNCHECKED" + x[5 + len(x.split()[1]):]
        out.append(x)
    return out


def check(tree, plan, sidecar=None, asbuilt=None, compose_tree=None, baseline=None, proofs=(), rows_files=(),
          skip=(), want_list=False, require_asbuilt=False, strict_cores=False, halo=0.0, elab_dir=None, ref_tools=None,
          toolstale_level="FAIL", abspath_level=None, remap=None, gendry=False, types=None):
    """_check_unscoped, restricted to the types of `types` (glob list / @file): the per-type classes only solve those types
    (reset-tree prewarm, TAPOFF), every finding line naming only other types is dropped; whole-plan classes (SCHEMA, INPUT, TREEPRE,
    TOOLS ...) run in full.  types=None is the unscoped PRE."""
    global _SCOPE
    if not types:
        return _check_unscoped(tree, plan, sidecar, asbuilt, compose_tree, baseline, proofs, rows_files, skip, want_list,
                               require_asbuilt, strict_cores, halo, elab_dir, ref_tools, toolstale_level, abspath_level, remap, gendry)
    names = set((json.loads(Path(plan).read_text()).get("partition_types") or {}))
    scope = parse_types(types, names)
    _SCOPE = scope
    try:
        f = _check_unscoped(tree, plan, sidecar, asbuilt, compose_tree, baseline, proofs, rows_files, skip, want_list,
                            require_asbuilt, strict_cores, halo, elab_dir, ref_tools, toolstale_level, abspath_level, remap, gendry)
    finally:
        _SCOPE = None
    return scope_lines(f, scope, names) + [f"LIST PRE-SCOPE {len(scope)} of {len(names)} types"]


def netlist_roots(ab, base, raw, idx):
    """DEPTH-NETLIST-1124: {module: {plan type, ...}} of the modules the as-built die netlist(s) (ab["netlist"], .v or .v.gz) instantiate.
    Most plan type modules (qfd_qc_<type>_part) are bind-generated wrappers that no RTL root defines, so the die netlist is where the
    bound logic is named (QC C1g: tt_ctlm = qfd_tt_ctlm_..._f5_cpub39_1 is instanced only there).  An instance is attributed to the type
    of the plan partition with its name, else to every type listing it in contents[] / hard_cores[], else to "<die netlist>"."""
    import gzip
    import bind_elab as E
    if not isinstance(ab, dict) or not ab.get("netlist"):
        return {}
    ptype = {q.get("name"): q.get("type") for q in raw.get("partitions") or [] if isinstance(q, dict)}
    cont = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        for c in (t.get("contents") or []) + (t.get("hard_cores") or []) if isinstance(t, dict) else []:
            if isinstance(c, dict) and c.get("inst"):
                cont.setdefault(c["inst"], set()).add(tn)
    out = {}
    nl = ab["netlist"] if isinstance(ab["netlist"], list) else [ab["netlist"]]
    for f in nl:
        fp = Path(f) if Path(f).is_absolute() else Path(base) / f
        if not fp.is_file() and fp.suffix != ".gz" and Path(str(fp) + ".gz").is_file():
            fp = Path(str(fp) + ".gz")
        with (gzip.open(fp, "rt", errors="replace") if fp.suffix == ".gz" else open(fp, errors="replace")) as h:
            body = E._strip(h.read())
        named = set()
        for m in NETLIST_INST.finditer(body):
            mod, inst = m.group(1), m.group(2).lstrip("\\")
            if mod not in idx:
                continue
            named.add(mod)
            tys = ({ptype[inst]} if ptype.get(inst) else set()) or cont.get(inst) or {"<die netlist>"}
            out.setdefault(mod, set()).update(tys)
        for mod in E.instantiated(body, idx) - named:              # a form the instance regex did not parse: still a root
            out.setdefault(mod, set()).add("<die netlist>")
    return out


def depth_netlists(tree, plan, asbuilt=None):
    """-> (generated netlist files the plan's RTL reaches, how).  With an as-built (rtl_roots / files / prefer): the modules of the plan's
    types and hard cores, closed over instantiation through bind_elab.module_index; without one: every generated file under <tree>/rtl."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import logic_depth as LD
    raw = _load(plan) or {}
    ab = _load(asbuilt) if asbuilt else raw.get("asbuilt")
    root = Path(tree) if tree else plan_tree_root(plan)
    if not isinstance(ab, dict) or not root:
        base = Path(root or ".") / "rtl"
        files = sorted(str(p) for p in base.rglob("*.sv") if LD.is_generated(p)) if base.is_dir() else []
        return files, f"every generated netlist under {base}", {}
    import bind_elab as E
    import bind_rowcheck as RC
    b = RC._base(plan, ab, asbuilt) or str(root)
    idx = E.module_index(ab.get("rtl_roots", ["rtl"]), list(ab.get("files", [])) + list(ab.get("prefer", [])), b)
    seen, reach, kids = set(), {}, {}

    def children(p):
        if p not in kids:
            try:
                txt = Path(p).read_text(errors="replace")
            except OSError:
                txt = ""
            kids[p] = [x for x in set(INST_NAME.findall(txt)) if x in idx]
        return kids[p]
    seeds = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):        # per type: which generated netlists it reaches (DEPTH-HELD)
        if not isinstance(t, dict):
            continue
        seeds.append((tn, [t.get("module")] + [c.get("module") for c in (t.get("contents") or []) + (t.get("hard_cores") or [])
                                                if isinstance(c, dict)]))
    nroots = netlist_roots(ab, b, raw, idx)                                 # DEPTH-NETLIST-1124: the die netlist's instances are roots too
    for mod, tys in sorted(nroots.items()):
        for tn in sorted(tys):
            seeds.append((tn, [mod]))
    for tn, todo in seeds:
        mine = set()
        while todo:
            m = todo.pop()
            if not m or m in mine or m not in idx:
                continue
            mine.add(m)
            for p in idx[m]:
                reach.setdefault(p, set()).add(tn)
                todo += [x for x in children(p) if x not in mine]
        seen |= mine
    files = sorted(p for p in reach if LD.is_generated(p))
    nl = f" + {len(nroots)} die-netlist instance module(s)" if nroots else ""
    return files, f"{len(seen)} module(s) reached from the plan's types{nl}", {p: reach[p] for p in files}


def _plan_modules(node, hard, soft):
    """every plan dict that names a "module": hard = those with a bound (signed) view (lef), soft = the rest"""
    if isinstance(node, dict):
        m = node.get("module")
        if isinstance(m, str) and m:
            (hard if node.get("lef") else soft).add(m)
        for v in node.values():
            _plan_modules(v, hard, soft)
    elif isinstance(node, list):
        for v in node:
            _plan_modules(v, hard, soft)


def depth_cover(tree, plan, asbuilt, modules):
    """QC-DEPTH5 11-24 (COORD): {module: reason} for the flagged modules that cannot bind a depth miss.
    'signed hard core' = every path from the plan's soft modules to it goes through a plan module bound to a signed view (lef): its depth is met
    inside that macro.  'not reachable from the plan' = no plan module reaches it at all (e.g. qfd_sys_face_n32_*).  Anything else: not covered."""
    import bind_elab as E
    raw = _load(plan) or {}
    ab = _load(asbuilt) if asbuilt else raw.get("asbuilt")
    root = Path(tree) if tree else plan_tree_root(plan)
    if not root:
        return {}
    roots = (ab or {}).get("rtl_roots", ["rtl"]) if isinstance(ab, dict) else ["rtl"]
    extra = (list(ab.get("files", [])) + list(ab.get("prefer", []))) if isinstance(ab, dict) else []
    idx = E.module_index(roots, extra, str(root))
    kids = {}

    def children(m):
        if m not in kids:
            out = set()
            for pth in idx.get(m, []):
                try:
                    out |= {x for x in INST_NAME.findall(Path(pth).read_text(errors="replace")) if x in idx}
                except OSError:
                    pass
            kids[m] = out
        return kids[m]
    hard, soft = set(), set()
    _plan_modules(raw, hard, soft)
    if isinstance(ab, dict) and ab.get("netlist"):                 # DEPTH-NETLIST-1124: what the die netlist instantiates is in the plan too
        import bind_rowcheck as RC
        soft |= set(netlist_roots(ab, RC._base(plan, ab, asbuilt) or str(root), raw, idx)) - hard
    if not (hard or soft):                                  # a plan that names no module: reachability is unknowable, keep the FAIL
        return {}

    def closure(starts, stop_at_hard):
        seen, todo = set(), [m for m in starts if m in idx]
        while todo:
            m = todo.pop()
            if m in seen:
                continue
            seen.add(m)
            if stop_at_hard and m in hard and m not in starts:
                continue
            todo += list(children(m))
        return seen
    soft_only = closure(soft - hard, True)                  # reached without entering a signed macro
    everything = closure(soft | hard, False)
    out = {}
    for m in modules:
        if m in soft_only:
            continue
        if m in everything:
            out[m] = "signed hard core: reached only through a plan module bound to a signed view (lef/lib), its depth is closed inside that macro"
        else:
            out[m] = "not reachable from the plan: no plan type, core or glue module instantiates it"
    return out


def check_depth(tree, plan, asbuilt=None, max_list=12):
    """FAIL DEPTH per generated constructor netlist with flops at logic depth >= the 833 ps budget (DEPTH-PRE-1123, logic_depth.py)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import logic_depth as LD
    try:
        files, how, reach = depth_netlists(tree, plan, asbuilt)
        raw = _load(plan) or {}
        held = LD.held_rules(raw)
        die = (raw.get("die") or {}).get("name") if isinstance(raw.get("die"), dict) else None
        budget = LD.levels(die)
    except Exception as e:  # noqa: BLE001 - a check that cannot run must fail (BPC-UNDEF / LANDREMAP class)
        return [f"FAIL DEPTH-UNCHECKED generated netlists not resolved ({type(e).__name__}: {str(e)[:200]})"]
    out, warn, n_deep, n_held, pend = [], [], 0, 0, []
    for p in files:
        try:
            r = LD.census(p, budget)
        except Exception as e:  # noqa: BLE001
            out.append(f"FAIL DEPTH-UNCHECKED {p}: {type(e).__name__}: {str(e)[:160]}")
            continue
        x = LD.finding(r)
        if not x:
            continue
        why = LD.held_why(held, r["module"], reach.get(p) or set())
        if why:                                          # DEPTH-HELD-1123 (COORD 19:40): a known, held cause reports, never refuses
            n_held += r["deep"]
            warn.append("WARN DEPTH-HELD" + x[len("FAIL DEPTH"):] + f" [HELD: {why}]")
        else:
            n_deep += r["deep"]
            out.append(x)
            pend.append((len(out) - 1, r))
    if out:                                                  # QC-DEPTH5: signed-hard-core / not-in-plan findings are WARN with the reason
        try:
            cov = depth_cover(tree, plan, asbuilt, {r["module"] for _, r in pend})
        except Exception as e:  # noqa: BLE001 - cannot decide -> keep the FAIL
            cov = {}
            print(f"depth_cover unavailable: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        keep = []
        for i, x in enumerate(out):
            r = next((r for j, r in pend if j == i), None)
            why = cov.get(r["module"]) if r else None
            if why:
                n_deep -= r["deep"]
                warn.append("WARN DEPTH-COVERED" + x[len("FAIL DEPTH"):] + f" [{why}]")
            else:
                keep.append(x)
        out = keep
    head = out[:max_list] + ([f"FAIL DEPTH ... {len(out) - max_list} more netlist(s)"] if len(out) > max_list else [])
    return head + warn[:max_list] + [f"WARN DEPTH-SUMMARY {len(files)} generated netlist(s) ({how}); {len(out)} over budget, {n_deep} deep "
                                     f"flop(s); {len(warn)} HELD ({n_held} flops); budget {budget} levels (depth_config.json / $OT_PRE_DEPTH_LEVELS)"]


def rstnames_findings(tree, plan, base):
    """RST-NAMES-1124: WARN RSTNAMES when the wavefront reset solve of PLAN differs from BASE (the bound / baseline plan): every
    part whose solved parent changed and every type whose rst_o site set changed renames reset relays / raw branches in the
    bound tree (HEAD-WEST hd_spn_end 11-24: 15 of 576 relay names not emitted, 13 raws gone after the nearest-first attach
    change).  Report only, wavefront plans with a readable BASE only; --skip RSTNAMES or OT_RSTNAMES=off."""
    if os.environ.get("OT_RSTNAMES") == "off" or not base:
        return []
    raw = _load(plan) or {}
    if (raw.get("reset") or {}).get("release") != "wavefront":
        return []
    try:
        braw = _load(base)
    except (OSError, ValueError):
        return []
    if not braw or (braw.get("reset") or {}).get("release") != "wavefront":
        return []
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import reset_tree as RT
        import schema

        def solve(r, p):
            P = _shared_plan(p, r) if p == plan else schema.Plan(json.loads(json.dumps(r)), Path(p).absolute())
            return _in_tree(tree, lambda: RT.wf_solve(P))
        a, b = solve(raw, plan), solve(braw, base)
    except Exception as e:  # noqa: BLE001 - a checker crash names itself
        return [f"WARN RSTNAMES not checked: {type(e).__name__}: {str(e)[:200]}"]
    pa, pb = a["parent"], b["parent"]
    moved = sorted(p for p in set(pa) & set(pb) if (pa[p] or (None,))[:1] != (pb[p] or (None,))[:1]
                   or (pa[p] or (None, None))[1:2] != (pb[p] or (None, None))[1:2])
    types = sorted(t for t in set(a["outs"]) & set(b["outs"]) if a["outs"][t] != b["outs"][t])
    if not moved and not types:
        return []
    return [f"WARN RSTNAMES {len(moved)} part(s) solve a different reset parent / site than {Path(base).name} "
            f"({', '.join(moved[:6])}{' ...' if len(moved) > 6 else ''}); {len(types)} type(s) change their rst_o site set "
            f"({', '.join(types[:6])}{' ...' if len(types) > 6 else ''}): their relay names / landing_raw_branches in the bound tree "
            f"are renamed (re-bind / landing_remap) -- a plan edit that only meant to move one part must not do this"]


def rstpin_findings(tree, plan):
    """PIN-REACH-1124: WARN RSTPIN per reset.parent_pins entry whose pinned parent has no rst_o site within the hop of the
    part's reset input (the part is unreachable and the solver then attaches it to the nearest reached part; c8: s_2S_x00 ->
    s_3S_L2 at 283 um > 275 um took 11 parts with it, fW0_p1_b0 hung 7.7 mm away).  Report only; [] unless a wavefront plan has pins."""
    raw = _load(plan) or {}
    rs = raw.get("reset") or {}
    if rs.get("release") != "wavefront" or not rs.get("parent_pins"):
        return []
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import reset_tree as RT
        rows = _in_tree(tree, lambda: RT.pinned_out_of_reach(_shared_plan(plan, raw)))
    except Exception as e:  # noqa: BLE001 - a checker crash names itself
        return [f"WARN RSTPIN not checked: {type(e).__name__}: {str(e)[:200]}"]
    out = [f"WARN RSTPIN {p}: pinned parent {q} is {d} um from its reset input, over the hop; the part is unreachable and attaches to "
           f"the nearest reached part instead (fix: re-pin to a part within the hop or drop the pin)" for p, q, d in rows]
    if len(out) > 40:
        out = out[:40] + [f"WARN RSTPIN ... {len(rows) - 40} more"]
    return out


INOUTLINE_TOL_UM = 1.0
_LC_XY_KEYS = ("xy", "xy_um", "pin_xy_um", "pin_um", "root")


def _lc_points(lc):
    """[(category, x, y)] of every xy a landing contract carries: bands are rects (adv_fpconv), here the collector tree (root, outs,
    relays, core_resets), collector_children / collector_local_sources and the pins."""
    out = []

    def xy(v):
        return isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in v)

    def walk(o, cat):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in _LC_XY_KEYS and xy(v):
                    out.append((cat, float(v[0]), float(v[1])))
                else:
                    walk(v, cat)
        elif isinstance(o, list):
            for v in o:
                walk(v, cat)
    ct = lc.get("collector_tree") or {}
    for k, v in ct.items():
        if k == "outs" and isinstance(v, list):
            out += [("collector out", float(a[0]), float(a[1])) for a in v if xy(a)]
        elif k == "root" and xy(v):
            out.append(("collector root", float(v[0]), float(v[1])))
        else:
            walk(v, f"collector {k}")
    for k in ("collector_children", "collector_local_sources", "pins"):
        walk(lc.get(k), f"landing {k}")
    return out


def inoutline_findings(plan, block=None):
    """FP-CONVERGE-S81 11-25 (COORD 06:2x, Fable flow review): BLOCKING.  One FAIL INOUTLINE line per type whose planned coordinates
    lie outside its outline_um by more than 1 um: station regs / bit-site footprints, relay sites, reach/sink sites, added taps, landing
    bands (adv_fpconv.in_outline), ft_slots regs and bit sites (adv_ft_outside.type_hits), and the landing contract's collector root,
    outs, relays, core resets, local sources and pins.  Violations that a --base plan already has are inherited by PRE-DIFF
    (LIST PRE-INHERITED), so only NEW or CHANGED lines block a row; a plan gated without --base blocks on all of them.  Seconds."""
    if block is None:
        block = os.environ.get("OT_PRE_INOUTLINE_BLOCK") == "1"          # COORD 05:4x: opt-in, set only for the c11 cut's PRE
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import adv_fpconv as AF
        import adv_ft_outside as FO
    except ImportError as e:
        return [f"WARN INOUTLINE-UNCHECKED {e}"]
    try:
        raw = _load(plan)
    except Exception as e:  # noqa: BLE001
        return [f"WARN INOUTLINE-UNCHECKED {type(e).__name__}: {str(e)[:120]}"]
    out, n = [], 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        o = t.get("outline_um")
        if not o or not isinstance(t, dict):
            continue
        W, H = o
        bits = []
        for name, cnt, worst in AF.in_outline(t, tn, raw):
            if worst > INOUTLINE_TOL_UM:
                bits.append(f"{cnt} {name}(s) worst +{worst:g} um")
        nsite = nreg = 0
        worst = 0.0
        for _slot, ns, nr, w in FO.type_hits(t):
            nsite += ns
            nreg += nr
            worst = max(worst, w)
        if worst > INOUTLINE_TOL_UM:
            bits.append(f"{nsite} ft bit site(s) + {nreg} ft reg(s) worst +{worst:g} um")
        by = {}
        for cat, x, y in _lc_points((t.get("clock") or {}).get("landing_contract") or {}):
            ov = max(-x, -y, x - W, y - H)
            if ov > INOUTLINE_TOL_UM:
                c, m = by.get(cat, (0, 0.0))
                by[cat] = (c + 1, max(m, ov))
        bits += [f"{c} {cat} point(s) worst +{round(m, 2):g} um" for cat, (c, m) in sorted(by.items())]
        if bits:
            n += 1
            out.append(f"{'FAIL' if block else 'WARN'} INOUTLINE {tn}: outside the {W:g}x{H:g} outline: " + "; ".join(bits)
                       + " (fix: clamp inside, 0 cycles; ADV-IN-OUTLINE / ADV-FT-OUTSIDE detail)")
    if n:
        out.append(f"LIST INOUTLINE-SUMMARY {n} type(s) with coordinates outside the outline"
                   + ("" if block else " (report only; $OT_PRE_INOUTLINE_BLOCK=1 makes them FAIL, set for the c11 cut)"))
    return out


def view_obs_findings(plan):
    """C-VIEW-NO-OBS (S81-GATE-LINT 11-26): view_lint.findings -- FAIL VIEW-NOOBS per hard-core LEF without OBS or without PG pins.
    ot_s81dv_norm_finish (576 M5 pins, no OBS, no PG) reached place with 515 floating pins.  A crashed check is a FAIL, never a pass."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import view_lint as VL
        return VL.findings(_load(plan), str(plan), repo=os.environ.get("OT_REPO") or None)
    except Exception as e:  # noqa: BLE001
        return [f"FAIL VIEW-NOOBS not checked: {type(e).__name__}: {str(e)[:160]}"]


def site_off_outline_findings(plan):
    """COORD K10 11-25 (FABLE-RC-KV SITE-OFF-OUTLINE): BLOCKING, no opt-in.  FAIL ADV-SITE-OFF-OUTLINE per type with a station site,
    relay / CLAND seat (collector local source, reset tap), port pin or clock tap outside its outline (adv_site_in_macro.off_outline_findings).
    KV D29 pv_v1e died at GRT-0209 on such a port.  With --base only NEW or CHANGED lines block (PRE-DIFF)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import adv_site_in_macro as SM
    except ImportError as e:
        return [f"FAIL ADV-SITE-OFF-OUTLINE not checked: {e}"]
    try:
        return SM.off_outline_findings(_load(plan))
    except Exception as e:  # noqa: BLE001 -- an unreadable plan cannot be judged: refuse, never a silent pass
        return [f"FAIL ADV-SITE-OFF-OUTLINE not checked: {type(e).__name__}: {str(e)[:160]}"]


# PRE-SPEED-1125 (S-04): a scoped PRE ran every advisory on the whole die (S81 v3 2 types: 1038 s, REF-SITE alone 1022 s) and then dropped
# the out-of-scope lines.  Scoped, the per-type advisories run on a scope view of the plan (partition_types and partitions of the scope
# types; 58 s, same or more in-scope lines since the per-check caps no longer fill with other types); the lane-context checks
# (ADV_DIE_CONTEXT: their per-type lines read the far end of each lane) still run on the whole plan.  OT_PRE_ADV_SCOPE=full: old behaviour.
# P-FALSE-GREEN-1126: RESET-NAME solves the die reset wavefront (reset.root_part e.g. sp5 is a partition of ANOTHER type), so on a scoped
# view it died with KeyError 'sp5' and the crash ended in PASS; it runs on the whole plan, limited to the scope's types (OT_ADV_RESETNAME_TYPES).
# P-SCOPE-VIEW-KEYOUT (S81-PRE-KEYERR 11-26): REF-SITE solves the same die reset wavefront (reset.keep_outs names types outside the scope:
# S81 col_h10_r1/r2 died with KeyError col_h10_r0_p1, NOT-EVALUABLE); it too runs on the whole plan, limited by OT_ADV_REFSITE_TYPES.
# Never filter keep_outs / partitions instead: a wavefront solved on part of the die is another die (wrong relay names, false clean).
ADV_DIE_CONTEXT = ("G0-HOPS", "LANE-STATIONS", "STN-DEADLANE", "RESET-NAME", "REF-SITE", "BOUNDARY-REG-50")
ADV_SCOPE_ENV = ("OT_ADV_REFSITE_TYPES",)


def scope_view(raw, scope):
    """a copy of raw holding only the scope's partition_types and partitions (everything else shared, unchanged)"""
    v = dict(raw)
    v["partition_types"] = {k: t for k, t in (raw.get("partition_types") or {}).items() if k in scope}
    v["partitions"] = [x for x in raw.get("partitions") or [] if not isinstance(x, dict) or x.get("type") in scope]
    return v


def advisory_lines(tree, plan, asbuilt=None, baseline=None, scope=None, reset_plan=None):
    """PRECHECK-R2: plan_advisory.run() lines, each forced to a WARN (an estimator never refuses); [] when the tree has no module."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))          # -I drops the script dir
    try:
        import plan_advisory as PA
        import adv_reset_names as RN
    except ImportError:
        return []
    checks = [c for c, _ in PA.CHECKS if c not in ("IST-PRICE", "IN-OUTLINE", "FT-OUTSIDE", "RESET-NAME")]
    try:
        raw = _load(plan)
        scoped = scope is not None and raw and os.environ.get("OT_PRE_ADV_SCOPE", "view") != "full"
        lines = []
        if scoped:
            _vchecks = [c for c in checks if c not in ADV_DIE_CONTEXT]
            if _vchecks:                                      # an empty list would mean ALL checks to PA.run
                lines = PA.run(scope_view(raw, scope), plan, tree, checks=_vchecks, asbuilt=asbuilt, baseline=baseline)
            _dchecks = [c for c in checks if c in ADV_DIE_CONTEXT]
            _set = [k for k in ADV_SCOPE_ENV if os.environ.get(k) is None]
            for k in _set:
                os.environ[k] = ",".join(sorted(scope))
            try:
                if _dchecks:
                    lines += PA.run(raw, plan, tree, checks=_dchecks, asbuilt=asbuilt, baseline=baseline,
                                    boundary_reg_types=scope)
            finally:
                for k in _set:
                    os.environ.pop(k, None)
        elif checks:
            lines = PA.run(raw, plan, tree, checks=checks, asbuilt=asbuilt, baseline=baseline)
        reset_scope = RN.configured_types(scope if scoped else None)
        if ("RESET-NAME", "adv_reset_names") in PA.CHECKS and RN.candidates(raw, reset_scope):
            # Use RESETWARM's Plan, repository context and environment. The scope
            # is an argument so advisory-only filters cannot invalidate tree cache keys.
            P = reset_plan if reset_plan is not None else _shared_plan(plan, raw)
            lines += _in_tree(tree, lambda: PA.run(raw, plan, tree, checks=("RESET-NAME",),
                                                   reset_plan=P, reset_types=reset_scope))
    except Exception as e:  # noqa: BLE001
        return [f"WARN ADV not run: {type(e).__name__}: {str(e)[:200]}"]
    return [x if x.startswith("WARN ") or x.startswith(PA.FAIL_KEEP) else "WARN " + x for x in lines]



_LANE_SLOT = []


def lane_slot(tree, env=None, out=None):
    """FLEET-OPS 11-25 (epyc12 load 293 on 96 cores: 35 concurrent PRE checks, 153 processes, 18 from one lane): while the HOST is overloaded
    (load1 > $OT_PRE_LOAD_X (1.5) x cores) at most $OT_PRE_LANE_CAP (3, 0 = off) PRE checks of one lane (the claude/<lane> dir of the tree) run on this host at once;
    the others wait for a flock slot in $OT_PRE_SLOT_DIR (/tmp/ot-pre-slots) for at most $OT_PRE_LANE_WAIT_S (900 s), then run anyway (never starved).
    The flock dies with the process, so a killed check frees its slot.  An idle host is never gated.  -> slot index, or None when not gated / not waited"""
    import fcntl
    import time as _t
    env = os.environ if env is None else env
    out = out if out is not None else sys.stderr
    try:
        cap = int(env.get("OT_PRE_LANE_CAP", "3"))
        if cap <= 0:
            return None
        if os.getloadavg()[0] <= float(env.get("OT_PRE_LOAD_X", "1.5")) * (os.cpu_count() or 1):
            return None
        m = re.search(r"/claude/([^/]+)", os.path.realpath(tree))
        lane = m.group(1) if m else "other"
        d = env.get("OT_PRE_SLOT_DIR", "/tmp/ot-pre-slots")
        os.makedirs(d, mode=0o1777, exist_ok=True)
        t_end = _t.time() + float(env.get("OT_PRE_LANE_WAIT_S", "900"))
        told = False
        while True:
            for i in range(cap):
                fd = os.open(os.path.join(d, f"{re.sub(r'[^A-Za-z0-9_.-]', '_', lane)}.{i}"), os.O_RDWR | os.O_CREAT, 0o666)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    _LANE_SLOT.append(fd)
                    return i
                except OSError:
                    os.close(fd)
            if _t.time() >= t_end:
                print(f"PRE-LANE-SLOT lane {lane}: no slot in {env.get('OT_PRE_LANE_WAIT_S', '900')} s, running anyway", file=out)
                return None
            if not told:
                print(f"PRE-LANE-SLOT lane {lane}: host load {os.getloadavg()[0]:.0f} over {os.cpu_count()} cores, {cap} PRE checks of this lane already running; waiting", file=out)
                told = True
            _t.sleep(5)
    except OSError:
        return None


# PRE-REUSE-1125 (FLOW-0930 F-18: the bind re-ran the full PRE inside itself: c10 79 min standalone + 84 min in-bind; KV in-bind PRE 874 s,
# 493 s ADVISORY): every `check` writes a PRE record (plan / as-built / baseline sha256, scope, skipped classes, FAIL lines, result) to
# --json and to the record store ($OT_PRE_RECORD_DIR, else <scratch>/claude/.cache/pre-record, else ~/.cache/ot-pre-record;
# $OT_PRE_RECORD=off: not stored).  bind.py reuses a record whose plan, as-built and baseline sha match (bind._pre_record_find) and then
# runs only the classes that read its own elab (ELAB_CLASSES).
PRE_RECORD = "PRE-RECORD-1125"
RECORD_STORE = "/srv/opentallas-scratch2/claude/.cache/pre-record"
ELAB_CLASSES = ("FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "RELAYSINK")


def file_sha(p):
    if not p:
        return None
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def record_store(env=None):
    env = os.environ if env is None else env
    if env.get("OT_PRE_RECORD_DIR"):
        return Path(env["OT_PRE_RECORD_DIR"])
    if os.path.isdir(os.path.dirname(os.path.dirname(RECORD_STORE))):
        return Path(RECORD_STORE)
    return Path.home() / ".cache" / "ot-pre-record"


def reset_forms_of(plan, scope=None):
    """P-RESET-RECEIPT-1126: {type: reset form sha256} of the judged types (reset_form.py); {} when the plan cannot be read"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import reset_form as RF
        return {k: v["sha256"] for k, v in RF.forms(_load(plan) or {}, sorted(scope) if scope is not None else None).items()}
    except Exception:  # noqa: BLE001 the record is still written; the missing forms are visible as {}
        return {}


def pre_record(plan, asbuilt, baseline, scope, skip, lines, seconds=None, tree=None):
    """the PRE-RECORD-1125 dict of one check's final lines (after PRE-DIFF)"""
    fails = [x for x in lines if x.startswith("FAIL ")]
    warns = [x for x in lines if x.startswith("WARN ") and not x.startswith("WARN ADV")]
    return {"record": PRE_RECORD, "tree": str(tree) if tree else None, "plan": str(plan), "plan_sha256": file_sha(plan),
            "asbuilt": str(asbuilt) if asbuilt else None, "asbuilt_sha256": file_sha(asbuilt),
            "baseline": str(baseline) if baseline else None, "baseline_sha256": file_sha(baseline),
            "types": sorted(scope) if scope is not None else None, "skip": sorted({s.upper() for s in skip or ()}),
            "tools": str(Path(__file__).resolve().parent), "result": "FAIL" if fails else "PASS", "fails": fails, "warns": warns,
            "advisories": sum(1 for x in lines if x.startswith("WARN ADV")), "seconds": seconds, "time": round(time.time()),
            "reset_forms": reset_forms_of(plan, scope), "crash_warn": os.environ.get("OT_PRE_CRASH_WARN") == "1"}


def store_record(rec, env=None):
    """write rec into the record store (<store>/<plan sha 16>/<record sha 16>.json, atomic) -> path, or None"""
    env = os.environ if env is None else env
    if env.get("OT_PRE_RECORD", "on") == "off" or not rec.get("plan_sha256"):
        return None
    if "PYTEST_CURRENT_TEST" in env and not env.get("OT_PRE_RECORD_DIR"):     # tests never write the shared store
        return None
    try:
        body = json.dumps(rec, indent=1) + "\n"
        d = record_store(env) / rec["plan_sha256"][:16]
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{hashlib.sha256(body.encode()).hexdigest()[:16]}.json"
        tmp = p.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(body)
        os.replace(tmp, p)
        return p
    except OSError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plan_gate_pre", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--tree", required=True)
    c.add_argument("--plan", required=True)
    c.add_argument("--sidecar")
    c.add_argument("--asbuilt")
    c.add_argument("--compose-tree")
    c.add_argument("--baseline-plan")
    c.add_argument("--remap-base", help="REMAP-BASE-1122: base plan for LANDREMAP / ISTCYC only (default: --baseline-plan, $OT_PLAN_REMAP_BASE, <plan dir>/bind_of_record)")
    c.add_argument("--rows-proof", action="append", default=[])
    c.add_argument("--rows", action="append", default=[])
    c.add_argument("--skip", action="append", default=[], choices=CLASSES)
    c.add_argument("--require-asbuilt", action="store_true", help="a plan without an as-built section is a FAIL")
    c.add_argument("--strict-cores", action="store_true", help="GEOM: also refuse sites over the planned head/pvg cores")
    c.add_argument("--site-halo-um", type=float, default=0.0, help="GEOM: grow every core box by this margin")
    c.add_argument("--elab-dir", help="bind OUT dir holding the elab's asbuilt.json (enables ROWSINK / the elab half of MODULES)")
    c.add_argument("--ref-tools", help="live reference tree for TOOLSTALE; \"auto\" = $OT_RT_CURRENT or <scratch>/claude/rt/current (default: not run)")
    c.add_argument("--list", action="store_true", help="print the resolved input paths (cleanup keep set)")
    c.add_argument("--json")
    c.add_argument("--quiet", action="store_true")
    c.add_argument("--types", help="FP-CONVERGE-S81: judge only these types (fnmatch globs, comma list or @file); per-type classes solve only them, "
                                   "findings naming only other types are dropped, whole-plan classes run in full; with --base the base check is scoped the same")
    c.add_argument("--base", help="PRE-DIFF (COMPOSE-FAST 11-25): fail only on findings NEW against this base plan (pre_diff.py); "
                                   "also the --baseline-plan when none is given.  Relative paths of the base run resolve in --base-tree")
    c.add_argument("--base-tree", help="PRE-DIFF: the tree the base findings are taken in (default --tree)")
    c.add_argument("--no-base-cache", action="store_true", help="PRE-DIFF: re-run the base check even when cached")
    c.add_argument("--reset-receipts", help="P-RESET-RECEIPT-1126: a reset_form.py emit file of the plan the types were signed on (or {types:{T:{form_sha256}}}); "
                   "a type whose reset form differs is LIST RESET-RECEIPT RE-SIGN-REQUIRED (per-type flag in pre.json, never a PRE FAIL)")
    lz = sub.add_parser("localize", help="ABSPATH-1122: copy outside absolute inputs into <plan dir>/inputs/, rewrite tree-relative")
    lz.add_argument("--plan", required=True)
    lz.add_argument("--out", required=True)
    lz.add_argument("--tree")
    rp = sub.add_parser("reprice", help="ISTCYC-1122: re-price fixed_cycles of the lanes whose station count changed vs BASE")
    rp.add_argument("--plan", required=True)
    rp.add_argument("--baseline-plan", required=True)
    rp.add_argument("--out", required=True)
    m = sub.add_parser("mkproof")
    m.add_argument("--plan", required=True)
    m.add_argument("--baseline-plan")
    m.add_argument("--lane", required=True)
    m.add_argument("--evidence", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--result", default="pass", choices=("pass", "fail", "withdrawn"))
    a = ap.parse_args(argv)
    if a.cmd == "reprice":
        d = reprice(a.plan, a.baseline_plan, a.out)
        print(f"reprice: {len(d)} lane(s) re-priced; wrote {a.out}" + "".join(f"\n  {k}: fixed_cycles {o} -> {n}" for k, (o, n) in sorted(d.items())))
        return 0
    if a.cmd == "localize":
        n, left = localize(a.plan, a.out, a.tree)
        print(f"localize: {n} outside input file(s) copied into {Path(a.plan).absolute().parent / 'inputs'}; wrote {a.out}"
              + (f"; NOT localized (missing / not a file): {'; '.join(left[:8])}" if left else ""))
        return 1 if left else 0
    if a.cmd == "mkproof":
        pr = mkproof(a.plan, a.baseline_plan, a.lane, a.evidence, a.result)
        Path(a.out).write_text(json.dumps(pr, indent=1) + "\n")
        print(f"{a.out}: {len(pr['types'])} types, result {a.result}")
        return 0
    lane_slot(a.tree)
    _t0 = time.time()
    brun = None
    if a.base:                                           # PRE-DIFF: the base check runs beside the row check (or comes from the cache)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import pre_diff as PD
        a.baseline_plan = a.baseline_plan or a.base
        brun = PD.BaseRun(a.base, a.base_tree or a.tree, a.asbuilt, None, a.skip, use_cache=not a.no_base_cache,
                          checker=Path(__file__).resolve(), types=a.types)
    try:
        f = check(a.tree, a.plan, a.sidecar, a.asbuilt, a.compose_tree, a.baseline_plan, a.rows_proof, a.rows, a.skip,
                  a.list, a.require_asbuilt, a.strict_cores, a.site_halo_um, a.elab_dir, a.ref_tools, remap=a.remap_base,
                  gendry=os.environ.get("OT_PRE_GENDRY", "1") != "0", types=a.types)
    except (OSError, ValueError) as e:
        print(f"plan_gate_pre: cannot read input: {e}", file=sys.stderr)
        return 2
    pdiff = None
    if brun is not None:
        bf, how = brun.result()
        if bf is None:
            f.append(f"FAIL PRE-DIFF-UNCHECKED base {a.base}: {how}")
        else:
            rf = [x for x in f if x.startswith("FAIL ")]
            pdiff = PD.diff(rf, bf, PD.subs_for(a.plan, a.base, a.tree, a.base_tree), PD.subs_for(a.base, None, a.base_tree or a.tree))
            f = PD.lines(pdiff, a.base, how) + [x for x in f if not x.startswith("FAIL ")] + pdiff["new"] + pdiff["changed"]
    resign = {}
    if getattr(a, "reset_receipts", None):          # P-RESET-RECEIPT-1126: per-type flag, not a die-gate finding
        try:
            import reset_form as RF
            _plan = _load(a.plan) or {}
            _sc = parse_types(a.types, set(_plan.get("partition_types") or {})) if a.types else None
            _rc = json.loads(Path(a.reset_receipts).read_text()).get("types") or {}
            resign = {k: v for k, v in RF.compare(RF.forms(_plan, sorted(_sc) if _sc is not None else None), _rc).items() if v["verdict"] != "SAME"}
            f += ["LIST " + RF.line(k, v) for k, v in sorted(resign.items())]
        except Exception as e:  # noqa: BLE001 a receipt file that cannot be read is named, never silently skipped
            f.append(f"FAIL RESET-RECEIPT-UNCHECKED {type(e).__name__}: {str(e)[:200]}")
    lst = [x for x in f if x.startswith("LIST ")]
    fails = [x for x in f if x.startswith("FAIL ")]
    warns = [x for x in f if x.startswith("WARN ")]
    adv = [x for x in warns if x.startswith("WARN ADV")]
    if not a.quiet:
        for x in lst + fails + warns:
            print(x)
    else:
        for x in adv:                                    # PRECHECK-R2: advisories reach the plan lanes even from --quiet callers
            print(x)
    unchecked = [x for x in fails if x.split()[1].endswith("-UNCHECKED")]
    try:
        _scope = parse_types(a.types, set((_load(a.plan) or {}).get("partition_types") or {})) if a.types else None
    except ValueError:
        _scope = None
    prec = pre_record(a.plan, a.asbuilt, a.baseline_plan, _scope, a.skip, f, round(time.time() - _t0), a.tree)
    if not unchecked:                                    # PRE-REUSE-1125: an UNCHECKED PRE is never reused
        sp = store_record(prec)
        if sp:
            print(f"LIST PRE-RECORD {sp} plan_sha256 {prec['plan_sha256'][:12]} result {prec['result']}")
    print(f"PLAN-GATE-PRE {'UNCHECKED' if unchecked and len(unchecked) == len(fails) else 'FAIL' if fails else 'PASS'} tree={a.tree} plan={a.plan} findings={len(fails)}"
          + (" classes=" + ",".join(sorted({x.split()[1].split('-')[0] for x in fails})) if fails else "")
          + (f" advisories={len(adv)}" if adv else "")
          + (f" base={a.base} inherited={len(pdiff['inherited'])} gone={len(pdiff['gone'])}" if pdiff is not None else ""))
    if a.json:
        rec = {"tree": a.tree, "plan": a.plan, "plan_sha256": prec["plan_sha256"], "result": prec["result"], "findings": fails,
               "advisories": adv, "pre_record": prec, "reset_forms": prec["reset_forms"],
               "reset_receipt": {"resign_required": sorted(k for k, v in resign.items() if v["verdict"] == "RE-SIGN-REQUIRED"),
                                 "no_receipt": sorted(k for k, v in resign.items() if v["verdict"] == "NO-RECEIPT")}}
        if pdiff is not None:
            rec.update(base=a.base, inherited=pdiff["inherited"], gone=pdiff["gone"], changed=pdiff["changed"])
        Path(a.json).write_text(json.dumps(rec, indent=1) + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
