# Joined RESTJ redesign — Codex 2026-11-08 02:22 takeover

## CODEX notes

Collected actual completed JOINED3D89 (found by Q2NF lead): intel1 `/srv/opentallas-scratch2/claude/die-hbm-89/restj/build_JOINED3/kits/ot_hgi_sfu_split3_ctl_rest_1c_f057777f78e4-JOINED3D89`. It is NOT SIGNED: TT -58.99 ps / 83 setup endpoints, FF -179.07 / 5947 (5790 ports, 157 internal; internal worst -14.44), DRV0, DRC0, antenna0, synth LEC EQUIVALENT. No ECO: setup exceeds near-miss limit.

GEOMETRY viewed actual PLACE density (`run/layout_review/place/density.png`, local `/tmp/restj_density_0222.png`), plus Q2NF lead's route heatmap: no macros, sparse interior, long E pin-edge clump at roughly60–70% local density, W-to-centre logic tree. CLASS: long single-driver control fanout into VM wide write data mux. TT worst `_0886_[16]` (lane0 registered drain sector bit16) -> `_0896_[252]` (lane1 VM write data), large repeated buffer fanout chain. Reset-recovery `_0919_ -> _0922_` is +29.99 and is NOT the failing setup path; no reset-only rebuild.

REDESIGN in progress, cycle neutral: lower extracted rest leaf into one-bit generic FF/mux cells, duplicate the four measured drain-sector selector FFs so each copy serves at most8 bit-cell consumers. Clone same entire FF function/clock/reset, keep each clone to prevent remerge; no logic, interface or cycle changes. Targeted estimate about280 extraFF, far below150k cells. Broader conservative companion can cover all high-fanout FFs if measured generic census supports it. Preserve existing joined scalar_data128/load4/address96 +1 cycle; no old data-only receipt inherited.

Own source branch `/home/ubuntu/codex-restj-0222-src`, `codex/hbm-restj-local-0222`, base main289149dea5. Transform `results/codex_hbm_restj_0222/clone_selectors.py`. Own lower-only run intel1 `/srv/opentallas-scratch2/claude/codex-restj-0222/{input/core.sv,lower.sh,clone_selectors.py}`; local ot-run client3630967, log `coord/tmp/codex-restj-lower-0222.log`,16GB2T. Last observed memory wait. This is generic elaboration/structural census, no P&R or STA. Next: collect exact clone count; full source equivalence + clone mutant; commit source/factory; one PLACE pilot and view before CTS.

OWNER? none newly raised.

## CODEX notes — proper joined-mode follow-up

Own branch pushed `codex/hbm-restj-local-0222@18ea1cb765` (predecessor193d1efccd). It carries the exact existing JOINED3D89 source deltas with the canonical wrapper name restored before hardening, selector-copy factory, full leaf equiv recipe, and a fail-fast requirement for the joined `__p56_ctl` export. No adoption or POR change.

First export failed before P&R on my clone cell/net names sharing one Yosys namespace; v2 uses distinct `_ff` cell names and exports cleanly. Exact census: four selectors /16 added FF /maximum8 immediate consumers per copy. The earlier280-FF estimate was too high because combinational decode nodes are shared. Broader wire/control reach still requires actual PLACE review.

Mechanism gate PASS: four-step SAT after the first edge, arbitrary selector and bank data. Wrong-D clone mutant is caught (`proof did fail`). Existing proof logs E6 `codex-restj-0222/mechanism_{clean,mutant}.log`.

Correction before any P&R: the first baseline generic lowering omitted `OT_REST1C_SCALAR_OPIPE_JOINED`, so its generated leaf lacks `__p56_ctl`. Its full proof is a baseline-mode diagnostic only, never current joined qualification. Stopped only my now-obsolete exact container `codex-restj-full-equiv-0222` (healthy jobs from other lanes untouched); failed/baseline files retained. New helper refuses a graph without that port.

Proper joined-mode lower/export/full-equiv now running on E6 `/srv/opentallas-scratch2/claude/codex-restj-0222/joined/`, own local client3685666, log `coord/tmp/codex-restj-joined-0222.log`,16GB2T. It reads the exact old source with the joined define, folds constant logic before one-bit lowering, then adds same-cycle selector copies. No P&R/STA yet. Existing tiny mechanism proof is reused (same clone operation and mutant); the full joined leaf proof is new and required.

Resource move: cancelled ONLY my unadmitted intel1 export client3645374, explicit NOT RUN receipt in `codex-restj-export-v2-0222.log`; staged current source to E6, where memory was available. E6 scratch2 was63GB, so any physical pilot should go to roomier intel1/E4 after the proof is read. Source-only base kit has been collected separately, with no old run/LEC/signoff artifacts copied into a new physical context.

## CODEX notes — selector proof and first physical pilot

Correct joined-mode graph has71714 original generic cells. It exposes3996 direct bit-cell consumers per selector:1996 added FFs at8 loads/copy,15952 rewired input bits. The earlier16-copy count came from the unoptimized diagnostic and is superseded. PIN CYCLES0 relative to existing joined source. Cell count rises roughly2% of the prior111k-cell form; clock sink count rises roughly8%, so clock locality is part of the PLACE read.

Actual graph certificate `joined/clone_certificate_strict.json` PASS on E6: all original cells/ports/nets/module metadata stay, original source FF connections stay, every added cell is a plain positive-edge FF with identical source clock/D/function, and every changed consumer connects only to its own source copy. Wrong-D graph mutant is caught. Combined with the source-FF SAT miter/mutant and existing64-edge boot contract, this proves this exact replication transformation. It is component proof, not routed-kit LEC. The two long per-internal-wire Yosys diagnostic sweeps were stopped only after this certificate passed, by exact own container names; they are NOT COMPLETED, not source FAILs or EQUIVALENT receipts. No other lane's jobs touched.

Own source branch current `codex/hbm-restj-local-0222@4759fecdcc3`, on GitHub AND canonical intel2:/home/ubuntu/OpenTallas. Published via an own bare relay with central objects as read-only alternates; no git command ran inside the central checkout.

Builder fixes before any physical work: native plan pin records use `name` rather than bus/bit; canonical hash helper had an unstaged import dependency. V3 handles both forms and uses exact GATE-PINS-2 canonicalization (baseline hash matches). Failed prephysical outputs kit_localA/A2 are preserved and marked DO_NOT_COUNT/HOLD_ROUTE; never launched.

New candidate intel1 `/srv/opentallas-scratch2/claude/codex-restj-0222/kit_localA3`: source-only kit, no inherited run/LEC/signoff artifacts.3815 E/W data pins alternate M4/M6. Actual ASAP7 M6 pitch .064/offset .032/height .032;0 off-grid,0 duplicate M6 positions. Peak20um-bin track use E M4 .2568/M6 .336; W .228/.304. M5 PDN and centre clock entry are unchanged. New actual pin PNG viewed; review + image committed at results/geom_review/restj_local_0222{.md,_pins.png}. Verdict conditional one PLACE; no CTS/GRT/route release and no parent-POR adoption.

FIRST PLACE pilot admitted intel1 unit `oth-ubuntu-1256316-1794136686`,16GB8T; local ot-run client3761458, log `coord/tmp/codex-restj-place-0222.log`. Runs run_kit_hbm.sh GOAL=place, OT_LEC_REPLICA_MATCH=1. Actual synth/physical LEC must still be EQUIVALENT for sign-off. HOLD_ROUTE and DO_NOT_COUNT retained. Next: collect synth guard/LEC and actual placed density/clock/dataflow; fix any remaining hotspot before CTS. No signed-off claim.

## Current — E4 A4 pilot (supersedes A3/I1)

Branch `codex/hbm-restj-local-0222@a173b7939bf` on canonical intel2 hub + GitHub. A3/I1 stopped BEFORE CAD: sdc_lint.json was incorrectly omitted as a presumed verdict, but is generator input context. Copied that context unchanged; no RTL/pin/clock change, failed A3 preserved. A4/I1 waiter was cancelled as NOT RUN on CPU-load hold; identical source moved to E4.

LIVE: epyc4 `/srv/opentallas-scratch3/claude/codex-restj-0222/kit_localA4`, unit `oth-ubuntu-1201275-1794137367`, local client3791664, log `coord/tmp/codex-restj-place-e4-0222.log`.8GB8T PLACE-only; measured old PLACE peak2.22GB + new frontend2.03GB justify stage cap (future DRT needs32–48GB; old DRT peak20.82GB). E4 scratch3 is root-backed; latest lane rules expressly permit it,656GB was free above150GB floor. Preserve progressing job.

SYNTH DONE:85932 std cells,13079.4um2,0 macros. Own synth LEC started in a separate admitted/queued8GB unit; no EQUIVALENT claim yet. Current pre-placement WLM repair_timing has no estimated parasitics,10782 endpoints; after21 resizes it repeats WNS-906.374/StTNS-5226.4 without more changes (600+ endpoint iterations). CPU/log advance: not hung; reported shared pre-place WLM no-progress class to root/flow. No live job edited or restarted. Actual PLACE image still pending; HOLD before CTS/GRT/route and DO_NOT_COUNT remain.


READY SOURCE — `codex/hbm-restj-local-0222@a173b7939bf`, exact same tip on canonical intel2 hub and GitHub. Actual A4 kit native LEC EQUIVALENT:41577/41577 proved,0 differs,0 undecided (338.5s), receipt E4 `kit_localA4/lec_async.log` and `lec/lec.json`. The whole-graph replication certificate separately covers71714 original cells,1996 exact source-FF copies and15952 rewired inputs; wrong-D mutant caught. No further ordinary proof rerun needed.

A4 has passed the1000-iteration WLM loop into actual PLACE; last iter1260 overflow.4411, improving. Routability weighted congestion minimum1.0361, overflowed tiles.34%. No final actual render yet. Physical stage remains HELD after PLACE pending density/dataflow/clock views, no route release/no count.

Static compact companion B only:181.44x267.84um, same source/zero added cycles, cell-area/core fill29.2%, face pin track windows<=.4104 after legal M3/M5 N/S and M4/M6 E/W spreading,0 track collisions/overflow. Full Manhattan corner span449.28um, Euclidean323.51um, clock-to-corner161.83um. Clock(90.72,133.824), parent embedding offset(125.28,90.816) preserves previous absolute clock and layer track phases. It has NOT RUN CAD/STA and actual registered-stage reach still needs placement review; parent POR unchanged. Do not launch B before actual A review. All artifacts, including failures and own obsolete copies, now preserved per root no-manual-deletions instruction.

Static B model and viewed pin image published in `55cf4dd1cdfd64bb817defa6c80181ca71990e77` on canonical intel2 hub + GitHub `codex/hbm-restj-local-0222`. This descendant changes only geometry-model/review files; actual native-EQ RTL remains exact a173b7939bf. A4 global place reached3_3_place_gp.odb after iter1670, now routine placement-parasitic report stage; no stage escalation.


## Current — A4 read; shallow/local-chain compact B synthesis

A4 PLACE completed rc0, unit oth-ubuntu-1201275-1794137367. Native LEC EQ41577, but actual estimated PLACE TT WNS-469.32/TNS-613698.44:1281.70ps bin VM drain_data[481] -> lane0 VM write_q[69], through two32-bit rounding additions then selection. Reset recovery+33.59 is still not the failing setup path. CLASS: DEPTH + SPARSE.

GEOMETRY: actually viewed E4 `kit_localA4/run/layout_review/place/{density,layout}.png` (local /tmp/restj_a4_{density,layout}0222.png).9% fill, sparse interior; E pin/mux clump~63%, N edge strip peak68.8%; no macros. N/S M5 sliding windows.502; resetrelay7590sinks spreads790.4um, io_r fanout3 spans up to609.5um. Existing selector copies do not resolve upstream control/reset or arithmetic depth. SMELLS: pinclumps N/S, long upstream fanout, opposite-side control reach, sparse clock sink span. HOLD beforeCTS/GRT/route. All A artifacts preserved.

REDESIGN: exact full32-bit BF16 rounding `x+32767+x[16]` becomes independent carry-prefix reductions;64 exact source substitutions,0 added cycles. Full32-input SAT PASS; tie mutant caught at59ff8000. Four selectors retain copies; upstream io_r452, resetrelay, sync_q1, sync_q0 are copied sink-to-source. Every selected source/copyQ measured<=8loads:4x499 selectorcopies,249io,979resetrelay,122sync1,15sync0.69842 original cells,3361copies,23533 originalconsumer inputrewires; strict wholegraph certificate +wrong-D mutant pass. Asyncreset FF mechanism SAT clean and wrong-D mutant caught. D/R may connect only to equal upstream copies; C/type/function preserved; source FF wiring unchanged. The existing64edge boot and reset establish the inductive relation. No giant proof sweep. Externalio_word/rst_n port load remains an explicit obligation; fanout bounds do not claim physical locality.

READY SOURCE: `codex/hbm-restj-local-0222@0f7e3e80e61598593b1192084e6c8f20daa26e97` on canonical intel2 hub AND GitHub. Factory +proof notes results/codex_hbm_restj_0222/{shallow_round.py,round32_function.svh,round32_miter.sv,clone_selectors.py,check_clones.py,reset_clone_miter.sv,apply_compact_geometry.py,shallow_round_proof.md}. Same existing joined +1cycles preserved, PIN CYCLES0 additional.

LIVE B: E4 `/srv/opentallas-scratch3/claude/codex-restj-0222/ot_hgi_sfu_split3_ctl_rest_1c_vB_0222`, unit `oth-ubuntu-2344205-1794140028`, localclient3918677, logcoord/tmp/codex-restj-vB-synth0222.log.8GB8T GOAL=synth ONLY plus fresh separate nativeLEC; no A EQ inherited.181.44x267.84um compact footprint, N/S M3/M5+E/W M4/M6, staticpin windows<=.4104/no collisions, fullManhattan449.28um. ActualM5clock90.744,133.824 (centre90.72 snapped toM5track), embedding125.28,90.816 preserves oldactual216.024,224.64. ParentPOR unchanged; source-onlykitbase, no inherited CAD/verdicts. HOLD beforePLACE until nativeB EQ and actualnewpinreview; HOLDCTS/GRT/route untilactualBplacedview. Next collect freshsynth/LEC, viewnewpinmodel, then firstBPLACE if legal. No manualdeletions.


## CLAUDE BACK — takeover handback (no further launches/probes)

SOURCE: own `/home/ubuntu/codex-restj-0222-src`, branch `codex/hbm-restj-local-0222@440dc33a99c25df95d444acff770a95e42a1925a` on canonical intel2 hub AND GitHub. Source/factory/proof commit0f7e3e80e61598593b1192084e6c8f20daa26e97; descendant440dc adds viewed exactB pin review only. No uncommitted source edits. No merges/tags/POR changes/deletions.

LIVE, PRESERVE: epyc4 `/srv/opentallas-scratch3/claude/codex-restj-0222/ot_hgi_sfu_split3_ctl_rest_1c_vB_0222`, unit `oth-ubuntu-2344205-1794140028`, localclient3918677, local log`/home/ubuntu/coord/tmp/codex-restj-vB-synth0222.log`. GOAL synth,8GB8T; SYNTH DONE88798 stdcells/13635.3um2/0macros, face_guard/port_bind/selrange PASS. Native B LEC started12:18:42UTC in its separate8GB unit/container `hbmcore-ot_hgi_sfu_split3_ctl_rest_1c_vB_0222_-2344286-lec`; both frontends finished, correspondence/proof active at handback, no failure seen. Receipts `lec_async.log`, `lec_run.log`, `lec/lec.json` when produced. Do not inherit A EQ. No B PLACE launched.

B exactsource:64 full-width BF16 round expressions replaced with equivalent shallow prefix function; all32-bit SAT PASS, tie mutant caught59ff8000.69842 originalgeneric cells plus3361 exactsamecycle FF copies across4selector/io/resetrelay/sync1/sync0 sourceclasses. Every selected source/copyQ has<=8 actualgraphloads, including upstreamDs. Strictgraph certificate and wrong-D mutant PASS; asyncreset clean/wrongDmutant PASS. Artifacts E4 `shallowB1/{core.sv,generic.json,replicated_chain.json,replicated_chain.sv,replication_chain.json,clone_chain_certificate.json}`; component logs E4 ownroot `round32_{clean,mutant}.log`, `reset_clone_{clean,mutant}.log`. Source-onlylower/export jobs finished0. All older diagnostic/failure artifacts preserved.

B geometry:181.44x267.84um, fullManhattan449.28um, actualclock90.744/133.824 with embedding125.28/90.816 preserves old216.024/224.64. E/W M4/M6, N/S M3/M5, measured sliding20um peak.4128. Actually viewed own exactB pin PNG, committed results/geom_review/restj_compact_b_actual0222{.md,_pins.png}. Conditional firstPLACE allowed only after nativeB EQ; reviewactualplaced density/dataflow/reset/clock reach before CTS. Parentio_word/rst_n boundary loads remain explicit; <=8logicalfanout does not establish physical locality.

A4 finished PLACE rc0/nativeLEC EQ41577 but TTestimatedWNS-469.32/TNS-613698.44,1281.70ps serialround data path. Resetrecovery+33.59. Actualdensity/layout viewed:9%fill, E~63%clump,N68.8%strip,M5pinwindows.502, resetrelay7590loads790.4umspan. CLASS DEPTH+SPARSE, held beforeCTS/route; NOT signed. A path E4 `kit_localA4`, unitoth-ubuntu-1201275-1794137367 complete. Original JOINED3 route onintel1 remains TT-58.99/FF-179.07, internalhold157/worst-14.44; no ECO, no signoff claim. Pre-CAD A3 failure missing generatorINPUTsdc_lint.json is diagnosed/corrected; I1 A4 waiter was NOT RUN, moved E4; all preserved.

EXACT NEXT: collect current B nativeLEC; if EQ launch FIRST B PLACE via ot-run8GB8T (not route), then actuallyview/render density+pin/fanout/clock and comparedepth/reach before any CTS. If nativeproof fails diagnose actualJSON, no waivers/retries. No livejob metrics patch applied. Root future-only private prectsmetrics opt-in exists but this candidate was left intact. All physicalholds/DO_NOT_COUNT markers remain. Owner questions: none. No children under RESTJ. Stopped new launches/probes immediately on Claude reset message.
