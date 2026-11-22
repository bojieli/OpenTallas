# FABLE-FIX-CONE-SCATTER handoff (Opus 5.5 for Fable; COORD launch 11-22 09:4x). Owns class LOCAL-CONE-SCATTER + its tool.
Lane dirs: intel2 /srv/opentallas-scratch2/claude/fable-fix-cone-scatter (clone/ = ot-lane-clone of main 7564be45ae; tmp/), epyc2 same path q/ (cone_dump.tcl, run_cd.sh).

## Findings so far (10:xx)
- The plan ALREADY HAS placement-group fields (COORD note "no field" is stale):
  * partition_types.<t>.place_regions [{name, inst_re, util, centre_um | near_re}] -> gen_phys install_place_regions -> place_regions.tcl
    (PRE_GLOBAL_PLACE, dbRegion+PHYSICAL_CLUSTER group; cone auto-extend when members < 0.5 of cone; DROP when cone > 8x members).
    S81-DIE-R5 kit-patch made it GPL-only (released before DPL) on serdes (DPL-0033) -- check whether that is on main.
  * partition_types.<t>.placement_guides [{inst, bbox_um, kind soft_region}] -> region_guide.py from-plan (kit_wave) -> soft GPL guide.
- Census source: ~/coord/autopilot/jobs/*/a*.log stop lines with path_um/span_um (format since ~11-21). Script: scratchpad census.py.
  48h: 42 distinct stop paths, 6 match signature (span<=200, path>=1000, wns<=-150):
  leaf t45 -663 (hi_sw->wdo_q), leaf t31 -503 (hi_sw->wdo_q), leaf t1 -348 (sw_a_q->wmw_q), dsdv nh_mus_C t1 -679 (xf driver flt_q self loop, 26 st),
  dsdv lepw_mus_LP t2 -347 (count_r[1]->count_r[5], 19 st), KV kv3_pc_v3 -1045 (idpc bin q -> u_kvpc1 core pin, span 10, 30 st). QC/HEAD: none.
- t1 kit (epyc2 kw43 .../18a2688b741/items/ot_s81sl_leaf__t1/gen/...) already has s81_vpw_bank.tcl (XR flops at banks, FIRM).
  End wmw_q is the b_dec (priority write decode) output reg; cone dump running (epyc2 q/t1_ctl.tsv).

## 10:2x update
- COORD scope change 10:0x: NO leaf t1 proof (LEAF-R10 owns XR decode fix, main d4aeaa3c6b58). Proof type from census outside leaf XR:
  chosen dsdv_slice_lepw_mus_LP__t2 (counter count_r; family owner FAM-S81-DSDV-R1, ASK posted 10:1x, launch if no OBJECT in 30 min).
- Tool commit 1 ddf3601771 (clone): place_regions kind fence|soft (place_regions_release.tcl before DPL), box_um, radius_um; precheck long row; schema+json. ot-push-main running (bg).
- Tool commit 2 (uncommitted at 10:2x): type_overlay.py accepts top key "place_regions" (kit-only, no rebind) -> private-spec --overlay route for the proof. Tests pass (test_type_overlay 29, test_place_regions 25).
- lepw t2 J7 place ODB copied to epyc8 q/lepw/3_place.odb; cone dump queued via ot-run (end re g_safe_write.g_address[N].count_r) -> q/lepw/cone.tsv.

## 09:5x update (hub clock PST)
- PUSHED main 4040b479bc (place_regions kind/box/radius + release hook) and 51fdaae779 (type_overlay place_regions key). rt/51fdaae7793b exists.
- Proof specs (rt 51fdaae7793b, overlay, default J7 tree/bind, goal route):
  A fence: ~/coord/autopilot/private_specs/FABLE-FIX-CONE-SCATTER/s81_dsdv_slice_lepw_mus_LP__t2_1122094657 (ov intel2 L/ov_lepw_A.json)
  B soft : .../s81_dsdv_slice_lepw_mus_LP__t2_1122094715 (ov_lepw_B.json)
  Launch = kit_wave.py run-item <spec> (bg, on intel2) after 10:10 if no OBJECT from DSDV-R1. Waiter: ot-wait --kit --durable.
- Rows: 20 place_regions, lcs_tx<t>_b<k>: inst_re g_tx[t].g_safe_write.g_address[(4k..4k+3)]. near_re tx t bank k SRAM macro, radius 30, util .5.
- Census+tool post 09:5x (hub 66f5021280). COORD report sent after this.
- epyc8 cone dump of lepw J7 ODB (q/lepw/cone.tsv) still queued (bg).

## 10:3x update
- Launched 10:10; first try FAILED kit_snap: KIT-STORE MISSING type_overlay (overlay file must exist on ALL die hosts). Copied ov_lepw_A/B.json to /srv/opentallas-scratch2/claude/fable-fix-cone-scatter/ on epyc8 intel1 epyc9 epyc10 epyc2 epyc7; relaunched 10:24 (units runitem-dsdv_slice_lepw_mus_LP__t2-71876 A, -71881 B; logs intel2 L/runitem_<spec>.log, try1 logs kept).
- Durable waiters (intel2 nohup) L/waiter.sh A-fence / B-soft: poll kit dir, then ot-wait --kit place/route --durable, post PROOF lines. (A junk 10:13 PROOF post was corrected.)
- Next: read place result (wns vs -347 baseline, OT_PLACE_REGION lines, DPL), hand row file to S81-J6-ASSEMBLY-R5 (J9) + DSDV-R1.

## 11:10 PST takeover update
- Latest private actual runs: A spec suffix 1122104037, unit runitem-dsdv_slice_lepw_mus_LP__t2-72895, work suffix 1122103955; B spec 1122104125, unit -72903, work suffix 1122104047. Both epyc8. Both now progressing in kit_rtl, actual ot-run scopes 4134244-1795374324 and 4124466-1795374312. They are legacy group utilization A=.50 / B=.30 with the same 20 anchors, distinct from earlier failed fence/soft overlay specs.
- The 10:56 rc78 came from ODB cone-dump client 695718 under E8 q/, with no result after its declared 3600-s wait and no stage evidence. Actual inherited A/B had explicit E8 load admission waits. The older 10:13/10:14 waiter posts had simply preceded kit-directory creation and had already been corrected.
- E8 q/lepw/cone_takeover.tsv and cone_takeover.live.log, unit oth-ubuntu-4149090-1795374343 rc0, recovered exact baseline: 720 counter flops in 20 groups and 6,472 visited cone gates. The sampled tx0/address1 counters cluster at x115.668–119.772, y721.845–725.355, ~9–13 µm below their SRAM, yet measured path is 1679.4 µm / 19 stages / −347.11 ps. Counter seats are already local; inspect whether the exact candidate group captured the intervening gates.
- Reviewed exact 20 bank anchors, macro shelves, channels and clock taps, picture E8 q/review_1122/cone_scatter_plan_ab.png, coord 05990647db6f. A/B Tcl in-memory read-only replay against the retained ODB is queued E8/I1, E8 q/review_1122/replay.live.log. This checks group coverage and computed regions while the actual builds continue. Review actual placed layout before any new Codex route. No inherited process was stopped.
- KV pc_v3 is the same scatter signature but its id/lpc result drives status and macro pin 490 µm apart. A single generic fence has competing loads. IOPC's existing macro-local register / separate combinational copy proposal is the needed architecture path. No duplicate KV run.

## 11:34 PST structural evidence and LEPe N2
- Read-only E8 legacy region replay unit oth-ubuntu-415170-1795374911 rc0 drops 20/20 groups in each utilization case. In the exact native synth cut, 11/12 carry gates are within x114–119, y724. The lone _081637_ is at x954.180/y724.815 with no external output sinks. Its other input is pp_g[0] from the kept shared tx-push primitive near x955 (also feeds tx1). This observed input tug explains the counter's out-and-back excursion.
- E8 q/review_1122/one_gate_guide.png is a reviewed geometry illustration of the one instance. The JSON is a coordinate receipt. Existing region_guide.tcl deliberately skips fewer than 20 members, so the manifest alone cannot implement that trial and should not be queued. The generic undirected legacy place_regions cone policy stays in place.
- Existing resolution is FAM-S81-LEPE-4 J8 N2, 5a208e94fe, OT_S81SL_LEP_TXQ3. It makes separate kept qualifiers for memory/state/pointer with identical logic and no cycle. Exact E7 composed F2/R1/N1/N2 tree fam-lepe4/trees/s81_n1 contains that define on dsdv_slice_lepw_mus_LP__t2. Its bind out is s81_n1_bind_n1. E7 fam-lepe4/n1bind/launch.out confirmed elab/strict bind rc0, LATCHECK 873/873, PRE PASS, and the nine G0 errors are byte-identical to F2. No exact N2 physical kit found in the owner or DSDV controller specs. The outstanding N2 step is exact place-only, actual geometry and TT, then determine routing against the bound row. Prior A/B still separate running admission.

## 11:40 PST exact TXQ3 place-only trial

Reviewed N2 planned image and extraction E7 `fam-lepe4/n1bind/n2_geom_plan.{png,json}` (coord 9263b6a4b02). The TXQ3 plan preserves all 53 placed baseline macro rectangles including hard-core track offsets, 109 taps, seven station sites and 15 edge windows. Scoped to goal `place` after coordinating FAM-S81-LEPE-4 and FAM-S81-DSDV-R1 (post f5f94b58969). Intel2 durable unit `codex-lepw-t2-txq3-place-1122` and spec `~/coord/autopilot/private_specs/FABLE-FIX-CONE-SCATTER/s81_dsdv_slice_lepw_mus_LP__t2_TXQ3_1122/spec.json`, E7 work suffix `1122113735`. Sealed on the existing fork, `dfcb8055f488` matches all existing bind generator hashes. Past source seal, kit work moved to kit_rtl. For any next route, review actual image, TT and exact separation of memory/state/pointer before routing. Legacy A now in active GEN; B still under regular E8 admission. No inherited units stopped.

## 12:38 PST N2 source-selection correction

The first place-only controller was stopped after generation and before placement because its kit selected the old portfix178 LEP source. Config.mk passed `OT_S81SL_LEP_TXQ3`, but the actual selected `physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv`, SHA `df47fa726b866508c403122739672041315478da4b89259ca8fc586667533820`, had no TXQS branch. The initial N1/N2 tree patched only the default RTL, which that type's native bind source manifest does not select. The first seal and bind are preserved for diagnosis. There is no TXQ3 physical verdict from that attempt.

The exact portfix178 overlay-only patch and minimal witness are on E7 `fam-lepe4/n1bind`. Patched overlay SHA `e21c69e15d1b060f38e0c47db5de5a0efb17dbb169e865a21ce49b1980db663f`. The witness simulates the literal selected selector and qualifier RTL for 64 input tuples with selector on and off. Both pass. Inverting the push input to the state copy fails on the first vector while the memory copy remains correct. Full Icarus parse hit a preexisting multi-net declaration syntax limitation in unrelated payload logic, so the witness extracts only the exact relevant branch and module. Native closure is separately checked by a fresh strict bind.

Official E7 independent copy `codex-lepw-n2-corrected-fork-1122` is forking to `/srv/opentallas-scratch2/claude/fable-fix-cone-scatter/trees/s81_n2_portfix178_1122`. Leave the owner tree unchanged. Apply only `txq3-portfix178.patch` after the copy and run the staged `fable-fix-cone-scatter/bind_n2_corrected.sh` under normal ot-run bind admission. The bind must name this exact portfix178 file in the selected ledger and bind.f and match the patched SHA before a fresh sealed place-only spec. Plan SHA remains `cd78ff7dfd19683ff8488839cf05f10a129ca7078c31f609dc9b020dfc37554d` and its image was reviewed. No new route and no main mirror this turn without the exact proof. Inherited legacy A/B remain intact.

The corrected E7 fork finished (54.21 GB / 328,518 independent inodes / zero outside links). Applied just the selected portfix178 patch; the new overlay is e21c69e15d1b and the owner original is still df47fa726b86. The fresh strict bind is now a durable E7 unit `codex-lepw-n2-corrected-bind-1122`. Log `/srv/opentallas-scratch2/claude/fable-fix-cone-scatter/txq3-portfix178-bind.live.log` and stage logs under `txq3-corrected-bind/`. It will attest exact path+SHA in both native selected ledgers before any new place-only submission. The previous setup analysis is physical evidence only for baseline J7. No main mirror or new routing was started.
