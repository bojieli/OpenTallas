# Geometry / disk checkpoint — 2026-11-02 01:58 PST request

This is a checkpoint, not a Claude reset or a stop. Agent `/root/geometry_disk` remains active. All jobs are untouched. No main merge was performed by this agent. No owner dialog was opened. No foreign job was killed or worktree edited.

## Branches and review evidence

Own geometry worktree: `/srv/opentallas-scratch/claude/wt/codex-geom-1101`, branch `codex/geom-1101`, latest pushed **4b8e18fd5**. Review evidence is under `results/geom_review/codex_takeover_1101/`.

Important ancestors, all included in that tip:

- **009d3d5e6**: approved GEOM106/108 `5_1_grt` classification fix in `tools/autopilot/geom_rules.py`: CTS rule set only when actual clock cells exist; real GRT0 makes demand proxies INFO in the approved scope. Data reach, actual leaf reach and rooted-clock gates remain. 35 tests passed. No later production geometry-rule changes.
- **0a7ea64e1 / d55977d1a**: native Tnode initial GRT/GEN reviews; BFQG GEN/initial PLACE; hroot FF-band PREP and old START caveat.
- **0372d9206 / f6763a7e7**: current already-approved singleton `[0]` START helper and current native Tcl packer witness. No custom source/protocol change.
- **66387dd4a / bb6b86a79**: HBM full-consumer union PREP, rejected L1 BUF trial, native Tnode CTS and QBS M5 centre event.
- **9b18f7fa7 / 4dd92fc7a**: RED native CTS/PG classification, original SC failure and exact port traces, L1 LVT PREP, Tnode first postCTS GRT, SU31 NE contacts.
- **86170ca6a**: completed actual hroot FF-only PLACE, guards, all19 comparison and images; precise L1 route-diagnostic scope; correct B001556 label.
- **fc50d1be0 / f44d84721 / 28ea9012b**: SC corrected actual LOOK/GRT0 capacity ruling; hroot static guide/window comparison and current-graph relocation mismatch; latest scoped HBM/QBS LOOKs.
- **fb5196fb1 / 6a7d8dac3 / 0f77ec7f9 / cdfc037a6**: exact guide memberships and PG-safe input-window reach; local preCTS clock gap; current 391um endpoint LP and coupled clock failures; preferred five-native-chunk comb guide PREP.
- **9bb5ad08c / 4b8e18fd5**: QUERY disabled full-event independent LOOK, exact BFQG saved-access/PG diagnosis, explicitly non-dispatchable hroot COMB capsule PREP.

Own S81 census worktree: `/srv/opentallas-scratch/claude/wt/codex-s81-kvleaf2-census-2058`, branch `codex/s81-kvleaf2-census-2058`, latest pushed **9b537aa4a** (ancestor **6797dbbb1**). Evidence: `results/geom_review/s81_kvleaf2_capacity_2058/`. The latest fixes 15 repeated HCpost parameter-receipt strings that had greedily spanned previous instances. OLD malformed receipt is preserved. Exact per-instance declaration parsing confirms all23 selected profiles unchanged and matching native GEN. No source/plan conclusion changed.

## Disk work completed

Intel2 initially had about125GB free/97% used. Under the existing retired-canary authorization, deleted only1326 generated `.odb/.spef/.def` files, **136.623GB**, after active/reference/protection checks. Source/netlists/reports/meta/receipts retained; no foreign jobs or WTs touched. Free space rose to224GB/94% and later declined with active work. Exact receipts: Intel2 `/srv/opentallas-scratch2/claude/prune-1101b/`. No further generic disk scans or deletions are underway. Original Claude PRUNE-H did scans only, no hidden cleanup/job to adopt.

## LIVE own S81 source-only sizing jobs

### Whole-KV bridge — sole producer

- ROOT-authorized normal **SYNTH-only** exact native CNIK1/CP1/HARD_RQ0, CNIK_MUT0/CP_MUT0. 707 functional bits/709 total with clock/reset; no FF/cycle added. No PLACE/STA or physical adoption.
- Source: exact old native kit readset `intel1:/srv/opentallas-scratch2/claude/kit-wave/s81/e8cbe5f6c70/items/ot_s81sl_kv_leaf__t2/gen/ot_s81sl_kv_leaf__t2/rtl`. Standalone source top `ot_s81sl_kv_bridge_size_top` wraps the exact native whole-KV module; unused two parent wrapper files excluded from this job's readset.
- Local runtime: `/srv/opentallas-scratch/claude/codex-s81-kvbridge-size-2111`.
- Remote runtime on Intel2 (also staged Intel1/EPYC2): `/srv/opentallas-scratch2/claude/codex-s81-kvbridge-size-2111`.
- Entry was through Intel2 `ot-run`, automatic fleet, normal32GB/8T. **Actual Intel2 unit `oth-ubuntu-1159241-1793599785`**, container **`codex-kvbridge-size-2111-1181066`**. Original controller tool session96923; hub controller PID531393 from earlier collection.
- RTL_LINT **PASS**. Actual ORFS SYNTH passed long OPT (3.8.191) and is in **3.9.1 FSM_DETECT**. Latest check:17.1GiB/32GiB,99.82% CPU. The FSM log has not advanced since01:11 but native Yosys remains CPU-active; do not label it terminal or rerun.
- Collect `synth.log`, `rtl_lint.json`, `synth_exit.txt`, `exit.txt`, `mapped_count.json` and `mapped_count.log` in remote runtime. Local `otrun.log` identifies admission. `count_mapped.py` runs after successful SYNTH, weights actual retained hierarchy, checks expected144 store +32 KVQ SRAMs, and reports unknown leaf types.
- Actual peak is ot-heavy/cgroup peak, not Docker client's `/usr/bin/time`: `/var/tmp/ot-heavy/peaks.tsv` and live `reconcile.state.json` on executing host.
- Important: **358423/343423 is explicitly a missing-model fallback, never an actual measurement**. No mapped terminal count yet.

### Parent residual — distinct minimal vehicle, newly admitted

- Uses ROOT's separate authorization to measure the parent residual with the23 matched source hard cuts; additionally abstracts the whole-KV boundary so it does not duplicate the active whole-KV synthesis.
- Local runtime: `/srv/opentallas-scratch/claude/codex-s81-parent-residual-PREP-0148`.
- Remote common runtime staged Intel1/Intel2/EPYC2: `/srv/opentallas-scratch2/claude/codex-s81-parent-residual-0148`.
- **Actual EPYC2/dear-crayfish unit `oth-ubuntu-1063615-1793613514`**, container **`codex-s81-parent-residual-0148-1063845`**. Controller tool session **16565**. Normal16GB/4T/disk8GB via `ssh intel2 ~/.local/bin/ot-run --mem16 --threads4 --disk8 --dir ... -- bash run_synth.sh` (actual command has spaces after option names).
- Exact materializer `materialize.py` creates24 unique source-only alias masters. It copies exact native ANSI headers, specializes declared integer defaults to exact selected profiles, and renames ONLY those24 direct bound instance types; original module bodies are untouched. Nine module families,16 repeated HCpost profiles. Aliases are abstract sizing boundaries, **not physical LEF/timing hard views**.
- Uses native GEN bound source SHA `9b3766c3...`; exact direct23 parameter/instance join to the bind census is confirmed. Remaining parent cohort/body join and physical adoption are held. The metadata openly records that GEN bound hash differs from bind_ev2's `ddfd01...`.
- Top `s81p_ot_s81sl_kv_leaf__t2`,98 readset files, current native helpers, normalRTL_LINT→ORFS SYNTH, no die re-ELAB/PLACE/STA. Proposed16GB was conservative, no prior measured residual peak.
- Latest: **RTL_LINT PASS**, actual SYNTH active OPT3.10.17,2.076GiB/16GiB,100% CPU. No mapped count yet.
- Collect same `synth.log`, `rtl_lint.json`, `synth_exit.txt`, `exit.txt`, `mapped_count.json`. Counter separates std cells,24 alias cuts, remaining memories, unknown leaves and verifies all24 cuts retained. This must not be presented as whole-parent flattened count or physical cut adoption.
- Materializer initially rejected comment text and the malformed old census parameter field before any native dispatch; both were corrected. Actual profile parsing now uses the exact single selected declaration line. No native failure was hidden.

## Hroot: actual failure versus current PREPs

### Completed actual FF-only PLACE

Own runtime local `/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338`; actual EPYC2 remote `/srv/opentallas-scratch2/claude/codex-hroot-ff-place-2338`.

ROOT authorized ONE normal FF-band PLACE-only capsule after KV confirmed no competing variant. First initialization attempt failed absolute-path load_design before DB load/placement; receipt retained. Corrected sole actual producer **EPYC2 unit3429395-1793605511** completed exit0.

-1585 existing target FFs packed into one86.4um band;5350 target comb released; all22411 FFs held during GPL/DPL;20826 unrelated FF original poses/status restored.
- Actual full and target images personally VIEWED before GPL and after completion. Full213407-instance master/DNT and complete DATA/CLOCK/PG graph/BTerm guard PASS, graph hash unchanged `e69e542e...`.
- Column proxy3.691→**2.826** (23.4% improvement), still FAIL; target comb remains under about28um input window.
- **All19 old r2r distances individually unchanged**, max1010.34/19; pinp90 134.12→134.23, max246.28 unchanged; nearest clock267.89/unbuilt own-leaf2512.71 unchanged. No GRT/CTS/STA run or released.

### Preferred guide-only PREP

Runtime `/srv/opentallas-scratch/claude/codex-hroot-comb-compare-next`, committed packet `hroot_static_comb_window/`.

- Original ten native64-bit/write-read role guides selected3409 cells; improved **five whole native64-bit chunk guides select4609/5350 comb cells (86.1%)**, preserving1200 real shared write/read cells in chunk affinity.84 crosschunk shared and657 output/unowned remain explicit. No real clock-cone cell selected.
- Exact literal-prefix expansion selects only intended disjoint cells; conservative current-body occupancy max30.6%. TSV omits TAP/FILL, so native capacity/legal-site/PG membership remains required.
- Personally VIEWED `chunk_guides.png`; concrete `chunk_guide_spec_PREP.tcl` uses standard `macro_reg_guide.tcl` inclusive GPL guides, then standard release before DPL. Actual membership may drift after release and must be measured.
- Preferred lower-scope diagnostic compared with real pin event: hold ALL FFs/pins/source/clock incidence, spread only existing comb. All19 reach/clock failures stay explicit, GRT blocked.
- Candidate normal capsule PREP local `/srv/opentallas-scratch/claude/codex-hroot-chunk-place-PREP-0134`, committed `hroot_chunk_capsule_PREP/`. It is **unconditionally NOT_DISPATCHABLE** pending ROOT and native PG-birth capability approval. No inputODB transfer/job. Source would be own completed FF-only `3_place.odb`, normal ORFS load, exact4609 mobile cells, every other instance held, actual preGPL LOOK pause, postDPL graph/pose/PG guards.
- **pg_birth explicitly says v1 native admission only repair_design/timing; GPL remains unadmitted. Do not bypass via wrapper or disabled timing flags.**

### Wider real input window PREP and interface cost

Current W window1352.0957..1380.6717 (299data+epoch). Centered86.4um widening collides with return L1594_0 at1380.9274..1406.8474. Left-only1294.2717..1380.6717 has no current paired interval overlap (gap0.2557um).

Production schema allocator: all300 old coordinates match native pins; left-only candidate has0 PG-blocked tracks and max132.183um to all1200 existing storage-slot FFs (old126.435),0>150. This excludes PC source/last-relay/forward-clock/START qualification.

All four paired PCv3–hroot seams would change:1200bit locations/2400 pads. Proposed0new pins/FF/cycles; forwarded controls/clock, bands and provider dictionaries must update coherently. Q12 hroot+1 interface compatibility remains unknown, ROOT/KV tracing. No canonical plan/source/pin edit. Source-event physical requires G0C zero new/bind0 and new review.

### Existing endpoint relocation and all19 closure cost

Prior `/home/ubuntu/coord/tmp/codex-kv-hroot/relocA/B` PREP (not adopted/superseded by KV) had41 endpoint moves, FAN landing down146.88/151.2um, fch/fo landing east172.8/181.44um, paired hub/PC windows and PCv3 existing relay shifts, seven PC stages unchanged. Old countb397.98/0 does not transfer.

Current actual graph replay matches all41 names but leaves17 failures/max757.08. Fresh current LP:

- Old53 allowed endpoints infeasible.
- Add existing shared reset101 relocation: feasible but3 payload captures remain441.02.
-57 allowed endpoints/46 actually moved: fullgraph405.00/0 but zero margin.
-80 allowed existing endpoints including current >390 captures: minimum common touching-edge radius390.204um. At391 target: **65 actual existing endpoint moves, fullgraph391.00/0** for both landing variants,14um continuous margin. Image personally VIEWED. No FF/cycle added.
- This is continuous geometry only, no row/TAP/PG/pin legality or source/parent adoption. Largest endpoint move about472um; shared reset101 moves over250um.
- Revised391 geometry plus baseline raw_o_5 contact fix produces19 grid reach failures/max245.037, maxload1476. A finite second-contact trial trades them for2 reach failures/max224.211 and maxload1533: **failed**, preserved. Coherent structured clock regeneration is required, not another blind PLACE.

Clock census on unchanged actual FF-only geometry: zero built clockcells;39 grid ports cover13185 non-landing sinks, maxload1475. Exactly one nearest-grid sink over220: raw_o_5 (189.648,293.625)→clk_t19 (241.44,509.728)=267.895. Static same-name clk_t19 y−51.84 gives216.055 global nearest reach on that unchanged geometry; personally VIEWED but not adopted. Dedicated landing fclk roots remain separate (KVSctl4502 sinks).2512.71 own-leaf is the direct-root preCTS graph, not a measured CTS tree.

## Inherited hroot GRT producers — collect, do not kill/repeat

All Intel1, foreign inherited jobs, no ownership of termination/cleanup.

- `/srv/opentallas-scratch2/claude/geom100/kv_hroot_g2`: terminal GRT50 **9224 overflow**,94271 nets, runtime20:21:26; layersM2..M7=1197/2481/1754/1661/1378/753. Actual image copied and personally VIEWED local `codex-hroot-inherited-finals/geom2.png`; same old19/max1010.34 and col3.691. Recorded in geometry branch.
- `/srv/opentallas-scratch2/claude/kit-wave/qwen_kvsys/event28w_c/items/kv3_hroot/geom`: **newly terminal** old container `ap-ageom-kw-kv3-hroot-grt-3638353`, `OT_GRT_DONE`,50 iterations, same9224 overflow/table and94271nets/5132710um wire, runtime21:05:16. Do not count this as an independent improved placement. Need final image/JSON collection if not already present.
- `/srv/opentallas-scratch2/claude/die-kv-60/hroot3/geomr_count`: LIVE extra50/50, container `ap-ageom-kv60-hroot3-count-grt-319474`.
- Same `/geomr_countb`: LIVE extra49/50, container `ap-ageom-kv60-hroot3-countb-grt-155295`.
- Last CPU check all about98–100%/8.49GiB/24GiB. Logs advance slowly; no terminal count/countb result claimed. ROOT/KV notified I own collection. No kills or duplicate CAD.

## QC SC / RED / L1

### SC actual correction and routing capacity

Owner `/root/qc_head_signoff/qc_sc_red`, no competing CAD by this agent.

Original TAP-aware PLACE realFAIL r2r600.453/1133, pin308.96/aspect2.102.1088 failures share dn_i45 launch u15646; single-launch move infeasible against current pin diamond by50.097um. Remaining45 traced to6dn inputs/39up output FFs. Reset first-reg failures classified separately. V1 central candidate failed hidden alternate412.587 and col1.681; preserved.

V2 native correction completed after an observer `::gd_u` failure resumed DPL only. Final dump EPYC2 `/srv/opentallas-scratch2/claude/codex-qc-sc-red-1101/sc_place_correction_r3/sc_final_place_geom.tsv`, retainedODB adjacent. All FF/clock/pin/source guards PASS, PG751910/open0. Personally VIEWED local `codex-sc-place-review-2322/final_native.png`.

Actual r2r404.92/0, pin11.3/41.44, rooted0/42665FF, ownleaf32um/maxleaf42. Raw col1.09/aspect2.102 preserved.

ROOT-authorized exact-placement full CLOCK+SIGNAL GRT50 probe **unit4070850-1793609927**, runtime `.../sc_route_probe`: terminal native overflow0,370320/370320 nets guided including2390CLOCK, missing0/noaboveM5; full poses/source/graph/PG unchanged. Actual GRT resolves capacity proxy for this finite geometry; no CTS/DRT/closure credit.

Subsequent actual timing diagnostic: **TT−411.17** caused by collapsed valid-control repeater chain, not math. `dn_i[47]` valid capture `u.g_sc_shared_rst_1.u_pin/Q` at237.168,6.615 (name misleading)→three existing BUFx6f clustered near103,318→INV102.141,318.465. First hop444.69um,64.67fF,359.26ps wire/1136.64ps slew; BUF delay138.2ps.

Concrete PREP `/srv/opentallas-scratch/claude/codex-qc-sc-red-1101/sc_buffer_eco_prep`: targets203.418/84.645,169.668/162.675,136.026/240.705; actual0.54×0.27 bodies/legal rows/TAP avoidance, all four chain edgesfanout1, new hops≤111.78um. Personally VIEWED targets.png/JSON. CONCUR static3-existing-buffer repair. Recommended ROOT ONE native import/check-placement/PG0/fullprotectedgraph capsule, then actual tail LOOK before separate bounded GRT/TTFF replay. No FF/pin/clock/source changes, no new cells/GPL/resize/CTS needed. **No ECO/CAD dispatched by us**; owner preparing, route still needs ROOT scope.

### RED

Full saved nativeCTS LOOK completed:34225FF/8269clocknodes, zero displacement; pin6.85/118.94,r2r307.58/0,col.263,ownleaf16.31/rooted0. PG976 opens=488 existing buffers; persisted global_connect saved-copy repair→PG465238/open0, complete protected DATA/CLOCK/pose/master/status/DNT/BTerm guards unchanged. Released ONE normal fullGRT50 after PG closure, no duplicated STA. Owner progressing normal post-GRT repair/final50; collect through QC, no duplicate extraction/job.

### L1

Near-driver BUF trial **rejected**: TT−15.605073 versus−11.755041, worsened3.850032ps; FF unchanged+5.851819, nativeGRT0/25. No further BUF variants.

Two same-function/identical routing-PIN/OBS/site/area RVT→LVT masters on OR4_279614 and XNOR_279616, from better3-edit baseline without BUF: actual native pose/master/net guards and PG545838/open0, image personally VIEWED. Parser39448 vs39446 sink-label drift reproduced on matched old checkpoint, no source/clock change.

One incremental DATA GRT actual **TT+0.061/FF+5.852**. Fresh actual GRT image VIEWED; r2r404.46/0, ownleaf53.14,pin9.05/81.91. Coverage1936/1936CLOCK +277231/277231SIGNAL, zeroSPECIAL/missing, PG0, but wire0 and no fresh full overflow table in incremental log. Do not claim freshGRT0/realCLOCKwire from that image.

Inherited partialface2 source is active fraction/density heuristic, not globally obsolete. Narrow frozen-contract classification: W760pins44%faceavg6.3, S221pins10%avg5.5; actual per-layer peak7WARN versus6budget. ROOT ONE ordinary route/signoff **diagnostic** permitted after this scoped LOOK/classification, no blanket waiver or SIGNED claim. Owner has route/signoff scope. Native access/DRC/fullCLOCKrouting/matchedTTFF/PG/proofs decide closure.

HEAD STmD old pin-failure request was stale; actual TT111.12/FF7.77/DRV0/DRC0/PG0/EQ1734KEEP856/native295pinPASS already collected. Do not rebuild it; parent receipt gap remains with QC/HEAD owner.

## HBM core and clock PREPs

### Tnode

Native compact125.28×95.04/1341pins/two actual SRAMs; sourceeb2 EQ4730/KEEP358/USED4, fresh native4 proof. Initial raw channel_h.797 preserved; real preCTS GRT50 and postCTS GRT50 each0overflow, coherent rails/clock actual LOOKs personally VIEWED.

Initial target250 postCTS RC TTpinreg274.16/dev24.16 FAIL; FF215.84/dev13.34PASS, actual setup109.31, hold_est−13.55. ROOT physical target235 compensation (unchanged250/202.5 contracts, source/reset/period) produced nativeCTS placementRC240.69/188.91PASS; actual target235 image VIEWED.

Latest normal target235 **route-only** EPYC2 `/srv/opentallas-scratch2/claude/codex-hbm-tnode-target235-routeonly-0010/RESULT.json`, owner evidence159a307e2: fullCLOCK+SIGNAL50 overflow0,13329nets/182325um, total32.38%/M241.96%; no newcells/repair and exact structure/pose/status/netflag/BTerm guards. PG27482/open0 pre/post/freshsaved. Actual globalRC TT251.75/dev1.75 and FF199.26/dev3.24 PASS. TTsetup109.0/FFhold−72.46 remain. **FF failure class unknown**, retained0010 has scalarWNS/means only, no endpoint/count report. Owner/flow next production hold-repair after PG-birth closure must emit paths/counts; no new diagnostic STA or blind target trial by us. No DRT/SIGNED/parent-source release.

### BFQG

Native259.2×220.32/1340pins/20clocks/eight actual SRAMs. Fresh component8650EQ/reset4. Initial raw congestion GRT50 **FAIL3193**,32m27s, M2..M5=1428/1159/522/84;2536 zero-capacity-edge overflow. Actual image VIEWED. Right-middle bank6/7 MY read captures were spilled central/west, causing body detours.

Standard inclusive guides for exact514 existing CQ256+rp_sel perbank6/7, no overlap1322 protected public/reset FFs. PREP conservative all4635pairenvelope397.992/0; personally VIEWED. ROOT corrected nativePLACE unit3909038 completed; actual image VIEWED: r2r357.59/0,pin8.4/68.14,rooted3898/no overlap/partialface; rawh.858/v1.04/col.959/9unreg/GRTNA retained.

Only168/257 and176/257 members remained strictly inside soft guide boxes after release/DPL; actual CQ macro clearances2.538/2.808, not4.32. No universal4.32 STD keepout rule exists here. Actual native tapcell logs2um halo; macroplacement4.32 and soft guide are distinct. No speculative rowcut/rebuild.

Exact frozen LEF inventory correction:819 non-PG signal/clock pins,410W/409E. All256 read outputs W (E on MY6/7), but wd137W/119E, masks256E and repair controlsE. No all-pin-side claim from CQ repair.

Saved correctedPLACE access export `/home/ubuntu/coord/tmp/codex-bfqg-guides-access-pg-0035/access.json`: bothfaces confirmed, nearest active2.16um/TAP2.052um, same-layer PG-metal/signal-pin bbox overlaps0;67553vias notexpanded, legal pinaccess unproved.

**New concrete PGFAIL4680 open VDD/VSS pins across2340 buffers/32782checked**, all actualnets empty/OT_PG_FINAL_BINDING. Existing two persisted VDD/VSS rules already cover them. Guarded saved-copy existing-rule global_connect is the fix; coordinate hbm_cores/pg_birth. Native installer refuses old defects. No GRT launched. After PG0/full source/pose/graph guards, geometry supports ROOT one corrected raw fullCLOCK+SIGNAL GRT50 diagnostic;9unregistered/source/CTS/timing holds remain separate.

Nine raw registration flags have exact source-qualified unique capture DFFs behind AND2 reset qualifiers, actual resetrelay only; generic comb waiver not granted. Single native grid root is INFO when fewer than2 grid taps, not automatically1500 hardFAIL.

### QUERY newly reviewed

Personally VIEWED `/home/ubuntu/coord/tmp/codex-hbm-query-native-event-0135/native_event.png`, parsed model/join/event. CONCUR disabled PREP only:170.64×164.16/1630pins/five real SRAMs, central/right streets; activeM5(86.376,82.08)≥12.414um fromnearestbody. One actualclk plus six unusedcompatclocks, no seven-domain claim. Exact reverse head5 normalization proves correspondence only. Six wrapper/eightcarrier/24physicalconstant-bit prune requires paired ABI/pins/proofs and actual cuts before logical8 restore. Clock311.5/262.6 vsGEN250/202.5 UNSELECTED, q1 real0.504um bridge, nativePG/contact/clock/actualreach/source-parent joins held. No physical/default/adoption release.

### Scoped HBM clock/bank PREPs already LOOKED

- q_b101 latF bays initially collided with actualFT; rawFAIL retained. RevisedlatK actualFT12832/12276 body0/duplicate0, first-hop391.23/396.36,89PGsafe contacts, cap1244/radii196.037/145.847: staticCONCUR only, no source/P&R credit.
- entryK lower local clocks failed fullconsumerunion2848; corrected entryO fullunion6types0 findings, SU00local61each/+74parentinputs, B11320/B001240 retained, cap1500/radius≤215.873/reset5/3/1 identities. VIEWED scopedPREP; source/provider/parent/START/currentviews held.
- SU31NE71local+4early,61777softFF+3reset,max1494/radius211.905,+51parent/type; NW73+4early,64503+3,max1307/radius176.896,+53parent/type. Fullunion9bodies/8.64halo0/FT0/nativeidentity, images/auditsVIEWED. Native66START/source/provider/parent/builtclock held.
- Restored upper SU00 both63local+11early,max1500/radius169.633,+78parentinputs; VIEWED and canonicalFT/fullmacro0. Distinct from lowerentryO61/+74. Final17-type fullcontrol/nativepin/PG/fullunion census/START/source-provider/parent event held.
- Restored upper B11320names kept,max529/radius50.96,two real one-sink controls; VIEWED. Prior lower emptyt5 retained.
- **Original native556um hop belongs to B001L730x2, not B113.** Static52ce two-bank repair381.51 is not native source/view closure. B113 directctl/store SOURCE13 frontier remains distinct and held.
- Calendar a4 existing G7 macro-heavy/aspect standing class applied by flow; enqueued, raw flags preserved. No new waiver or CTS/timing credit.

## S81 QBS / hist / pending review queue

QBS3 centreM5 event at21.612,38.892/.048×.48 clearPG/bay,191occurrences/26types coherent refs, source/reset/outline/cycles unchanged. OldM4preflightFAIL retained. Actual3 freshPLACE images VIEWED,1972/1972/1978 sinks/bay0occupied. Fourregional clock model493each (NN494/495),12fixedclockcells, calibrated40ps model TTmeans241.25..241.54/max254.06, FF185.44..185.68/max196.54; invalid2leaf/TT159 retained. Scoped treeinstall/PLACE review only. S81 owns LLfu/NNfu actualCTS/audits; LLfd membership-only defaultOFF helper. Requested actual packets, no duplicate CAD.

Hist source owner `/root/s81_ds/s81_wave_failures` owns ROOT ONE comb-onlyPLACE on exact anchoredFP6ea, allFF/TAP/macros/clockbay/sourceendpoint guard. Sourceproof current051 still held, noCTS before structuredclock/proof. Parent personallyVIEWED existing actualFP; await actual combPLACE image/model for independent LOOK. No hist job owned here.

Old GEOM107 t41/t51 stnbank NW/ftstrip review and serdes t3/t13 remain pending actual images/current source; no blind re-PLACE from stale requests. S81 parent knows these waits.

## Immediate next actions

1. Collect sole wholeKV and new parent-residual native SYNTH terminal/mapped counts and actual peaks; diagnose failures, no duplicate/custom ABC replay. Never use fallback358423 as measurement.
2. Collect inherited count/countb terminal GRTs; preserve allthree old producers. Originalevent28w just terminal9224 needs final image/JSON record; no newCAD.
3. SC three-BUF native import/actualLOOK and then ROOT-scoped route/timing only; keep TT−411.17 rawfailure until measured.
4. BFQG guarded PG-onlysavedcopy closure, then ROOT's corrected rawaccess/GRT choice; no rowcut/globalhalo invention, source/9registration/CTS held.
5. Tnode production hold stage after nativePG-birth closure must emit actual FF endpoints/counts, not another blind target sweep.
6. Hroot preferred5chunk guide physical trial stays held pending ROOT revisedLOOK and nativeGPL PG capability; source-event current391 LP/pin/clock costs remain PREP/Q12-held. No unrelated source/pin/cycle adoption.
7. Await QBS actualCTS and hist actualcombPLACE packets; review actual images, no duplicate extraction/job.

No new owner-blocking dialog/question. Technical holds are recorded above; ROOT owns the cross-lane Q12/clock/source scope choices. Continue working until explicitly told Claude reset; this checkpoint does not change that instruction.

## Post-write milestone — SC actual three-BUF LOOK completed

The authorized native import completed EPYC2 unit1067116-1793613522, exact runtime `.../sc_buffer_geometry`, native saved `SC_DATA_GEOMETRY_CHECKPOINT.odb`. Actual dump copied to local `/srv/opentallas-scratch/claude/codex-sc-buffer-actual-review-0158/geom.tsv`; full `auto_geom.png` and `actual_tail.png` rendered and personally VIEWED. Actual pin hops112.4965/112.091/111.983/111.824um, all fanout1. Full all-other-cell/FF/pin/CLOCK/status/DNT/graph guards, native body check and PG751910/open0 PASS. R2r404.92/0, pin11.3/41.44 and ownleaf32 unchanged; rawcol1.091/aspect2.102/GRTNA retained. Concurred ROOT's standing ONE fresh same-deck fullCLOCK+SIGNAL GRT50+TTFF replay; owner may launch, no GPL/resize/CTS/DRT/source changes or predicted timing pass.

pg_birth requested a concrete scoped Hroot GPL canary vehicle: provided own completed FF-only input/config/SDC/normalflags and the explicitly NOT_DISPATCHABLE five-chunk COMB capsule PREP. No new GPL job. Requires ROOT review plus native PG0/saved-copy closure before module install; do not apply endpoint391/source/pin PREPs. Native repair_design/timing capability does not imply GPL admission.
