# HBM kit classes takeover 2026-11-08 02:22 PST

CODEX took over: KCLS, KITPARAM and REACH collection; candidate fixes on codex/hbm-kcls-0222. No merge, tag or plan-of-record change.

## CODEX notes
- PHY SPLIT PARENT NOT BOUND AS SPLIT remains FAIL: NE_io/NW_io/q_spb0 (+physical_v1)/vsN0 passed provisional views and failed kit_preflight macro_instances. Plan subcores use u_lk_*.u_fcore.u_core.*; current bound parent is monolithic r18h5 ot_pdie_serdes at u_bound.u_u_lk_*. Candidate must supply real split glue and sub_core_leaf mapping, then strict bind + preflight. No blind relaunch.
- KCLS respread form (l): existing targeted tests completed, base and tip file-by-file receipts collected at epyc4 /srv/opentallas-scratch3/claude/die-hbm-91-kcls/t3_{tip,base}.txt. Exact comparison in progress. Hub gen processes remain active on epyc4 dry3 (q_hub_ne PID2613041, q_hub_nw PID2777180); pg_hub provisional overlay processes running. No duplicate launched. Hop estimates 1075.68/898.56/717.12 um remain a named physical risk; no physical release until actual geometry review.
- KITPARAM v2 a2eb941596 approved 02:21, unmerged at takeover. Newly collected q_su11__physical_v1 full dry PASS KITRTL/PROV/TOPO/GEN/GEN_LINT rc0 in epyc4 .../die-hbm-91/dry_tip3/rc.txt. q_b110/pv1 still healthy Yosys lint CPU-active; no new error.
- REACH strict bind new/control both rc0. Candidate dry hits new receipt schema failure: invalid native station placement receipt: stations. Focused child reach_collect traces writer/reader. Existing TIP-ONLY0 summary is from prior run; current test sweep still active. Logs on intel2 /srv/opentallas-scratch/claude/die-hbm-91-reach/dry/new/<type>/kit_rtl.log.

## Next
Fix split parent candidate asbuilt and rooted physical macro mapping, pilot full dry through kit_preflight --contract. Repair REACH receipt schema on isolated branch. Collect running dry/test jobs; publish READY only for concrete passing class fixes.

## Progress update 1
- Own branch codex/hbm-phy-0222@8c1f6e5b2f on hub: exact sub_core_leaf-driven rooting of declared physical paths (remaining subpath/master untouched so preflight still fails closed); 13 focused tests PASS. Private candidate manifest generated from kw27g+asbuilt_t12 with the four plan split parents N0/N2/S0/S1 mapped to existing p37glue; S3 stays unchanged because it has no p37 split rows in this plan.
- Strict cached-elaboration bind launched via ot-run --hosts epyc4 --mem24 --threads2. Source /srv/opentallas-scratch2/claude/codex-hbm-phy-0222/src, output ../bind, log ../bind.log and bind.rc. Controller log intel2 /tmp/codex-hbm-phy-0222/bind.otrun.log. No P&R or STA launched; candidate only, POR untouched.
- REACH fix a4143b6aa7 is on hub; fixed pilot cleared mixed receipt failure, then exposed missing own sparse rtl/lib/ot_reset_sync.sv prerequisite (being supplied). Original dry failures and old failed pilot preserved.

## Progress update 2
- E4 own PHY bind was memory queued and had not begun. Cancelled exact own controller3620525, staged identical isolated inputs on intel1 (inputs checked present, scratch379GB), launched controller3627766 via ot-run --hosts intel1. Latest log /tmp/codex-hbm-phy-0222/bind_intel1.otrun.log. Keep E4 staging until retention review; no deletion.
- KCLS class(l) source preserved on hub codex/hbm-ista-respread-0222@1ee657291e. 26 focused tests PASS; sorted predecessor per-file test receipts each242 lines identical (TIP-ONLY0). Plain gen processes still CPU-active; provisional overlay FAIL newly collected: NW xload_cl2_bdring bsel25 missing directions; NE same + q2n2_vm_core writer_kq4...8645 missing directions. These remain FAIL; no physical release.
- XLOAD provisional direction cause isolated by child: packed dimension contains parentheses, prov_view declaration regex rejects before width stripping. Fix in progress; q2n2 exact-name source alias diagnosis in progress.

## Progress update 3
- Projection branch hub tip86ada8b95d. Producer manifest absent => original explicit paths stay unmapped for preflight; unrelated kits gain no producer-file requirement. 13 focused tests still PASS.
- Intel1 bind admission request16GB (existing reach strict bind measured7.4GB), controller3630221; prior own24GB waiter3627766 cancelled before work. No guard changes and no other lanes stopped.
- New shared provisional-direction class fix READY: hub codex/hbm-prov-dir-0222@8a7de434e0, base289149dea5. Packed dimension stripping fixes xload bsel25; exact recipe files_at commit:path lookup resolves q2n2 header40 ports including writer_kq4. 12 focused tests PASS incl wrong-top negative. Actual both-hub provisional dry starting under child; no P&R or POR change.

## Progress update 4
- PHY bind first admitted on intel1 and stopped before binding because own sparse tree lacked tools/die_port_bind.py. Original bind.log/rc1 retained. Exact tracked file supplied; no design/constraint change.
- Fresh bind2 ADMITTED immediately on E6 unit oth-ubuntu-3257944-1794134408, controller3642132, --mem16 --threads2. Guard admits307GB, source staging331MB, scratch73GB; no floor/guard override. Path E6 /srv/opentallas-scratch2/claude/codex-hbm-phy-0222/{bind2,bind2.log,bind2.rc}. Own source includes projection86ada8b95d and prov-dir8a7de434e0 for dry only. No P&R launched.
- Full next dry script staged dry_p37.sh: kit-rtl -> prepare-stations -> provisional -> gen phys -> kit_preflight --contract, first NE_io only. Launch after strict bind rc0. No auto route and no batch release.

## Progress update 5
- E6 bind2 stopped before emit on one remaining own sparse-source prerequisite: results/hbm_bind_2_1029/dead_qlate_proof.json. Original bind2.log/rc1 retained. Supplied exact proof and its only declared source dependency ot_hdc_delay.sv from unchanged asbuilt base, with byte-equality guard on any existing file; no proof/constraint relaxation.
- Fresh bind3 admitted E6oth-ubuntu-3293676-1794134491 immediately; controller3646099, Python3293749 CPU97%, RSS3.5GB at35s. New output bind3/log/rc; full next dry script now targets bind3. Actual binder work is progressing.
- Existing hub-gen is also progressing: NE wrote fresh ft_bit_sites.tcl2.06MB and ft_track_use.json at02:39; not a hung job. No old process stopped.

## Progress update 6
- PHY bind3 CPU94%, RSS5.2GB at136s, no error. After-bind controller3650344 remains attached and launches exactly one NE_io dry if rc0.
- Hub provisional dry remains CPU-active. Measured runtime cause is 40+ repeated whole-tree git grep --untracked scans across child masters; process-local one-scan module index assigned as bounded runtime fix on another own branch, without changing current live dry/source.

## Progress update 7
PHY private p37 strict bind3 PASS rc0:90 partitions/81 types/420 crossings, errors0/unbound0/tied0/undriven0/multiply_bound0. E6 /srv/opentallas-scratch2/claude/codex-hbm-phy-0222/{bind3.rc,bind3.log,bind3/bind_report.json}. No physical credit/POR change. Attached after-bind collector3650344 proceeds to ONE NE_io full dry through kit_preflight --contract (no P&R).

Timestamp correction: intermediate progress headings used estimated local times and have been relabeled by sequence. Artifact/unit timestamps are authoritative; no result or failure verdict changed.

## 2026-11-08 02:49 PST
- PHY source staging branch6bd1276e21: exact existing three split source files and required gf/syndrome headers staged together. New immutable asbuilt_p37_inc.json selects them. Old dry2 missing-include FAIL retained. dry3 KITRTL PASS0 (19files, unbound0) then topology FAIL KIT_TOPOLOGY_BIND_STALE because manifest source paths changed from strictbind3; guard preserved, not bypassed.
- New strict bind4/controller3667445 on E6 uses exact staged manifest and chains one NE_io dry4 through preflight on rc0. bind3 PASS evidence remains intact. No P&R.
- Shared provisional class semantic fix has actual full q_hub_ne PASS rc0, all30 contractchildren resolved; E4 codex-hbm-reach-receipt-0222/provdir/q_hub_ne.log. NW sequential provisional dry healthy.
- Shared tool branch hubbd4edf5333 includes exact semantic fixes plus one process-local module index: actual16,427modules indexed13.318s, cached lookup4us,13tests PASS. No live source changed.

## Handoff to Claude 2026-11-08 04:25 PST — HBM KCLS/native/receipt child scope
Stopped all new launches/probes on parent's explicit reset. Child cascade complete; healthy jobs retained; no manual deletions/merges/tags/POR changes.

Sources:
- Own branch codex/hbm-phy-0222: last verified canonical intel2 ref388b275e1a. Latest parked LOCAL commit377c90030b; canonical push already in progress in toolsession67016 at stop, deliberately not polled. Local tree /home/ubuntu/codex-hbm-phy-0222. Latest composition (rootPMA7a11 patch+nativeaec+recursive include staging) is parked code, NOT a tested full runtime release.
- Verified canonical tool branches: codex/hbm-native-receipt-tool-0222 dc73be6fd9 (independent of unadopted reach plan); codex/hbm-prov-dir-0222 bd4edf5333; codex/hbm-ista-respread-0222 1ee657291e; codex/hbm-ne-input-delay-0222 aec3976daf (local-clock grouping, SOURCE-only). Real gearbox proof commit25fb70f119 is ancestor on native branch.

Actual results:
- E6 /srv/opentallas-scratch2/claude/codex-hbm-phy-0222: strict bind3/bind4 PASS0,90parts/81types/420crossings, all connectivity errors0. NE_io KITRTL/TOPO/PROV/GEN7/preflight7+8 PASS0; original six split-PHY hierarchy errors removed. Preflight8 correctly finds old Wchannel4.32<10.8. This is class/source preparation, no physical or sign-off credit.
- Shared provisional-direction full dry PASS0 NE29/NW32 contract children, E4 codex-hbm-reach-receipt-0222/provdir. Receipt source pilot q_su11 PASS0, native4stations, unbound0. Source tests focused13 projection/14native plus7co-root; no broad reruns.
- Actual EP gearbox transactions on I2 codex-hbm-ne-gbx-0222/attempt_1 PASS:199/1650 decoded comparisons at+4cycles,25/2IDLE beats; MARK/IDLE-only mutant caught42, IDLE-only caught1027, separateST2 cohort clean. No FEC/PMA/SRAM/physical phase claim.

Private NE form, all on I2 /srv/opentallas-scratch2/claude/codex-hbm-phy-0222:
- candidate_ne_vC/die_plan.json is private, source plan unchanged elsewhere. Widens slot648->677.376, private die east+29.376; spreads macros >=25.92um and mirrors EP MY (contractLEF permitsXY) to uncross512-bitTX/RX. Real port directions replace erroneous/duplicate core rows. TX/RX/ST+2cycles each,2052FFbits, TX+RX+3332ps@833. Typearea+0.12690432mm2; globaloutline what-if~+0.54467mm2. Images/review in ownbranch results/geom_review/codex_hbm_phy_0222.
- asbuilt_ne_vC.json, candidate_bind_C/ strict PASS0 using cached JSON and read-only canonical sourcebase. Last native_kits/vC/rc.txt KITRTL_RC2: canonical selected ot_s81_kp4_enc_la.sv lacks neighbor headers. Latest LOCAL parked helper stages selected LA encoder plus recursive exact headers; not yet staged/run. Original failed files/logs kept.
- Current I2 runtime src is older composition (no PMAoutput patch/common-rootfollowup); do not call it latest377. No NE live job, no NE P&R launched. Source-only fresh prep next with local parked composition + explicit io_outputs10names (root7a11); normal strict native context must match new manifest. Then root PMA clock/eye/pad contract before GEN/P&R. Also finish complete legacy bus-station overlay: some old bus sites are inside EP and were not qualified by the native3-link image.

Other live/remaining:
- q_mca child handback /home/ubuntu/coord/lanes/CODEX-HBM-REACH-HANDBACK-0415.md is authoritative. Live intel1 /srv/opentallas-scratch2/claude/codex-hbm-qmca-reset-0222/kit32 unit3039147-1794140502: PLACE-only, KEEP RUNNING; HOLD_CTS/HOLD_ROUTE/DO_NOT_COUNT. Prep duplicate driver definition failure unit3015071 diagnosed/fixed via filelist reference only, original retained. Candidate32latches+247keptdriver,17edge reset proof112400actualrelay comparisons and +/-160phase witnesses PASS/mutant caught. Last confirmed canonicalq_mca36a9c04bf9; child's final commit/push toolsession46145 already running atstop, unpolled.
- q_mca has no START port; prior STARTpattern wording meant reset release/reassert pulse pattern only. Approved bindingMETHODOLOGY6.1 uses TTsetup0/FFhold25/833 (oldROLE60text stale); no private relaxation.
- q_spb1 bounded lookup found original flat160 only, no measured die per-port table in checked receipts. HOLD_CTS until actual DIEproof/tap_arrivals_TT+FF or explicit OWNER fork. Root already logged OWNER?; no within-kitCTS substitute.
- Inherited KITPARAM q_b110/pv1 original lints healthyCPU99.9 at last04:15collection, no endrc; q_su11pv1 full dry PASS. Keep running.
- Inherited broad REACH base test hit original90min timeout rc124; tip still active at lastcollection. Oldcomparison is stale, validation INCOMPLETE notPASS. New receipt regression12rows fixeddc73; remaining dry failures mapped KITPARAM/rootrecursion/provisional classes. Old hub gen jobs remain CPU-active with fresh output, not killed/restarted.

OWNER?/holds: root owns PMA clock/eye budget+forwarded tck post-clock-taps and data pad proposal (7a11 source tool ready, physicaldraft HOLD); root owns per-port-first predicate fork for q_spb1/q_mca. No new owner dialog and no budget invented.
