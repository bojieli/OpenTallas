# CODEX TOK-HBM / HBM-MU / assigned HEAD reach handoff — 2026-10-29 02:04 PDT

EXPLICIT RESET received from ROOT. PARKED. No new project work/jobs after reset. Current source worktree clean at codex/tokens-hbm-1028@6be5c0287, pushed to origin; own WT /srv/opentallas-scratch/claude/wt/codex-tokens-hbm-ready-1028. Bank child bank_absence was told to park (its work already terminal/merged). No owner questions pending.

## One live owned job: preserve it

Existing fulltree component regression, NOT current die/token qualification:
- Host epyc2, ot-run unit oth-ubuntu-201658-1793260539, requested40GiB/4threads. Started via intel2 ot-run. Client functions exec session85588 can remain pending; use remote files/processes below rather than launching a duplicate.
- Runtime /srv/opentallas-scratch2/claude/codex-hbm-token-1028/fulltree
- Remote source WT /srv/opentallas-scratch2/claude/wt/codex-hbm-token-fulltree-1029, branchcodex/hbm-token-fulltree-1029@3260121c4. Original run script results/tok_hbm_codex_1028/fulltree/run.sh there.
- Last observed: Verilator frontend finished, fast C++ objects0/1 complete; class2 compilerPID517864 live (~9minutes at02:03), makePID270610 invokes-j1. Unit parent201658, script201688. Total4large fast objects and4slow objects. No functional logs yet. Do NOT stop/restart now; ROOT explicitly says let it continue untouched.
- Diagnosed build inefficiency: Verilator5.050 -j4 did not set C++ build jobs; actual make-j1. Future-only script fix6be5c0287 adds --build-jobs4 (local help confirmed). It does not alter this live run or its source.
- Earlier attempts: unit158770-1793260176 exit127 before functional run, remote hub lacked pushed branch; fixed own local bundle/checkout. Unit194526-1793260480 terminal MEMCG-OOM at16GiB, exit143; retry above40GiB is the only live job. No other lane process touched.

Exact read-only checks:
```bash
ssh -o ControlPath=none epyc2 'tail -n 20 /srv/opentallas-scratch2/claude/codex-hbm-token-1028/fulltree/build.log'
ssh -o ControlPath=none epyc2 'ps -p 201658,201688,270610,517864 -o pid,ppid,etime,pcpu,rss,args'
ssh -o ControlPath=none epyc2 'ls /srv/opentallas-scratch2/claude/codex-hbm-token-1028/fulltree/pre_n1/run.log'
```
After completion collect pre_n1/run.log, pre_n6/run.log, post_n1/run.log, post_n6/run.log and pre_n1/mutant_job_a.log under the runtime. Bench always$finish/exit0: classify HNX_FUSED PASS/FAIL, mism/fault/done/bankerr/read/write counters, not process exit. Mutant qualification requires passing nominal vehicle first. Script runs all four cases and same-binary A-address control. Sources: archived32leaf fulltreebench from hbm_n4_native source_snapshot, current pinned native tree/hub_n4ext/eng,833ps clock,40warmedges/negedge drive. OLD f4c_t9p3 station table deliberately retained: component regression only, not current C25c vehicle. It revisits inherited fulltree numerical failures after source pad fixes; exact root cause remains open until result collection.

## Completed HBM source/compiler components

Main publication confirmed by merge owner: initial rgap/finite absence work through27cfdfe04 + no-SU bankee0ef7ce0 on maina7168d188c; optional P3 sources/native ALAT/top ALAT published8777d00cb7; HEAD reach receipt publishedbaf7411b45. Later tiny notes/guards may still be in merge queue; all are on pushed source branch.

- 3b0e55245/fbb6ffeb5: opt-in --schedule-rgap calendar and --calendar-rgap native217 emitter, strict native field/source/price guard. Actual161jobs:81PRE rgap24, +9720serviceedges. Disabled/corrupted controls refuse. No default change.
- b6c504469/27cfdfe04: finite explicitSU/MTP/MU no-local-SU SW/SE calendar guard, actual8NorthSU source census; native one-lane RD267/rgap24 real RTL120chunks/120writes/6returns fin1011 fault0; same binaryrgap23 stickyfault477 caught (even laterfinish/exit0). Logs committed.
- Child ee0ef7ce0 distinct hfd_vms_bank_native_q0_faces_nosu master:1840checks256reads64writes/373cycles lockstep + forbiddenread/write and swapped-response controls caught. No production source selection or actual production finite absence proof.
- be7a18ee0: WCOPY aliases into actual pinned bank, explicit eight-instance m5a3w1/m5a4w1 source transform tools/hbm_b2/su_build_profile.py. Exact command: python3 tools/hbm_b2/su_build_profile.py CURRENT_NATIVE_TOP.sv --profile m5a4w1 --out OWN_NATIVE_M5A4W1.sv --receipt OWN_PROFILE.json. No default/profile adoption. Actual old8parent graph4/4/0; default graph equivalent, WCOPY1 propagation proven with forced0 actual mutant caught. Rebal/bind have command; actual next source/manifest event belongs to bind/plan/root.
- 9d7d18b64/6b1678cc3/efcf94d9e: prod_compile --alat and NativeTiming/layer_images --native-alat, default bytes unchanged. MLAT5/WCOPY1 ALAT3->4 actual ds_rs135->139 (+4), ds_spsqrt4 375->448 (+73), same payload/address. Raw core edges only; old cycles_stream_833ps retired4/3 conversion NOT used. m5a3w1 linear32 vsold29; m5a4w1 linear33, bank+1; SIDEII5/4 candidate22/1/55/24. SIDE hardware3/3 intentionally held; no blind global ALAT propagation.
- 81f22f1b3 recovered new MTP_N6 candidatea1228bb5771a604f53aad9de3366f460fd9d7c0c59b9a04fa2856405b5726933:3916records,I1-I7PASS,161FUSED/9600VMcopy/414720HBMload. Lost oldf0 bytes unavailable on current hosts; wholehash differs, historical byte recoveryFAIL. All161FUSED fields/offsets/formats exactly match old saved receipt,0reject; no whole-image numerical equivalence claim. Source/evidence results/tok_hbm_codex_1028/image_recovery.json +candidate_mtp_N6_a122.hgi1r.

## P3 opt-in source packet and remaining integration contracts

results/tok_hbm_codex_1028/idx_multirow/ABI.md has exact ports/types/timing, logs and reproduction stager.

- c8a35d877/f99155a4b: all old769 packed IDX bits are occupied (684keep_bitmap plus TOPKk last10). Distinct IDX818 collar appends49 bits from previously reserved hostoperand424..472; same six host rows0x800..805,0runtime edges. n_rows5/pitch12/weightStride16/queryStride16. No default source master replacement. Real RTL833ps2280matchingedges/1026writes/4launches/10cases PASS; same binary dropping49fields caught; reserved473 guard retained. Optional serializer now404b7a3b7 refuses native weight/query strides not8/4-sector aligned (valid6/96/8/512 accepted).
- 51c3f0806: new ot_hnx_idxq_rootctl_static_am grafts donor CW2 calendar onto actual selected root05f5acd8bbc7953a0ce8ba02dd3d697489d5c327bee7bb09bd8def049f2a4c1e. Actual TOPK/share tail byte-identical; preserve VM_RT75/CR_RT36/SEL_LAT40/RSTL1/FAN32. Ports16/8/32 selector control, lin_clear/lin_row5/lout_row5, selected_v16/ingest_v4/sf4; argmax_m264 retained. Real service-only1201-edge lockstepPASS, RT74 mutant caught84. No active INDEX calendar in that service check. New calendar has no physical fanout/timing qualification.
- Same51c: donor qctl DELIVERED_RESET0 default retained, optional1 direct delivered reset. N1/N6 control-only1603matchingedges/14KEY/4live/10PRE/2frame/7rowstarts fault0; same-binary DROP_PRE caught906. Source calendar imported unchanged from859b27b6b.
- 10313fc40: distinct n12-compatible multirow reader exposes VM_RT_EXTRA default4; donor shell hardcoded2 was wrong for actual selected171(SW/SE/NE) and173(NW). Real request-derived-return model, N1 thenN6 weight stride8/query512:4642edges/profile,14blocks/70requests, fault0, exact request/data/headweights; wrongRT2 caught13. SIDs must remain SW0/SE1/NW2/NE3 (donor client hardcodes four SID0s). Native strides are VM256-bit sectors; HGI B descriptor is FP32[32], native head reader packedBF16[32], so correct real packing/staging and alignment remain needed.
- 6abf91d57 documents combined row hazard, still OPEN: next row_start/seen clear must follow all prior-row reader blocks PLUS query quantizer qv/tag tail. Actual query rejects duplicate seen bits and faults frame_start with block_v/emit_v/qv. No row identity in reader tags. G2MIN23 is only scorer query reuse, not this drain window. Donor2->actual171/173 delta169/171 must be priced separately; already-current171/173 baseline adds0. Do NOT reuse donor pitch or add169/171 twice.
- Four real selectors needed (+3 current12SRAM masters =+36SRAM), with bind's corrected sparse quarter expansion, not donor compressed lower-half packing. Row-slot link, all real keybuf clear/live/pre/replay wires, reader strides, actual reset and combined programme/source/plan event remain. Component proofs are not full INDEX scores/token.
- Actual candidate census:8 active INDEX recordsN6, global nkeys524288/1048576 (firstrecord295,offset38000,layer2), plus80KVUNION/40TOPK/40UNION. No nkeys0/South-key inactivity claim. Native local shard lowering required, not truncation of global nkeys. Missing SouthSVG key_lines need actual producers; North services are id_stack2, direct aliases would change contract.
- Actual retained8NorthSU QID2/3 source has no KIND2 FULL/SIDE, despite physical slots. Root/rebal/bind own explicit capability source fix and actual two-role/compiler mapping; no production absence/capability claim. Candidate direction separates FULL_SIDE capability from VM QID, defaults unchanged, but is not adopted by this lane.

## Current C25c / clock / source closure

HBM owner source/trial candidate1a planabe1936f353f83ffc73175ee0d3652712a50f1e3 SHAe3f35afffb6e3ad8001571a569d0c5e8ee88d5e37372e3da9318738344cf5f57, typed side53ed20461. New boundary-only draft0e34777f1 SHA57ad209f (264scorer+16NP4,80keybufSRAM) keeps intended station latency; no duplicate161job diagnostic required.

ba735b060 source diagnostic: actual stationNW53/44 NE53/45, return267,81PRErgap24+9720serviceedges=8.09676us, WSC146/PK5=1/PB5=0. Host packet transport30, provider LOADcapture31, then UNKNOWN regional CAKextra K. Qualified bound.MISSING deliberately omits host leg; normal calendar refuses. RAW_SOURCE_ONLY diagnostic removes provider START/preload/commit timings and START authority and uses diagnostic schema, so emitter required fields absent. No programme/boot/whole-die vehicle. HBM owner helper6d3b080eb +typed clock_extra_required=true/null side closes generic int31+prose acceptance;11testsPASS reported by owner. No guessedK.

Old strict463 verdict retained; old diagnosis corrected in TOK-HBM-5. Current unmapped32810 originally includes8realSUsubtrees29198 +2SFU200 +4scorer3412, notallscorers. SM gin/qin8608zero seed bits intentional. Selector padding intentional but packed quarters wrong (bind corrected). RF_LOCAL shared integer vb multidriver discovered by bind; bind owns narrow vb_valid rename/regenerate, no active SU edits from me. No R7 waiver. SPB optional source e64c6bba8/FLOWd3d7fc341 actualTX4/RXstatus4; old plan-only4/2 means delta0/+2 only if actually consumed, not blind token surcharge.

## Failure dispositions / MU audit

Historical pg-coreconn-3 NSM2 SMH activity run:145errors/150words over14records, nofault/xstoreerror, exit0 misleading.5dump windows end before retire. Actual helper correctly FULL BENCHNOTPASS. Exact numerical cause unresolved (control/data age/fixture drift is inference); not currenthnx_rp3 release. FLOW owns current replacement, old activity remains unqualified; no expensive rerun by me.

Three old Oct26 mu_r13/mu32_r13 proxy jobs listed in HBM-MU-AUDIT are on epyc1, explicitly RETIRED-1027 in SSHconfig; hostname no longer resolves. Did not contact retired IP or rerun obsolete proxy. Unavailable historical archives are not implied live jobs/production evidence. Current native source/plan gates supersede them; audit lane updated.

## Assigned HEAD actual G1 reach — completed and published

ea1cb3c0a, published mainbaf7411b45. results/head_serdes_reach_codex_1029/{review.json,review.py,README.md,resize_liberty.json,placed.png}.
- Exact existing kit5 geom from intel2 /srv/opentallas-scratch2/claude/codex-head-serdes/kits5/ot_s81_kp4_dchn_head/geom/geom.tsv (3_place.odb); no extraction/synth/P&R rerun. Current viewed image supplied by HEAD owner.
- Typed master ot_s81_kp4_dchn / actual u_phy.u_link.u_dec.u_chn / hd_serdes / INTERNAL_CORE R2_INTERNAL_TIMED_IN_PARTITION.943ports=320input/623output,4369nonempty direction-typed cone relations,6440registerD/Q records map to actual placed instances.132physically resizedx1->x2FFs (264records) checked against actual image TT Liberty identical sequential state/CLK/!D and D/QN clock arc interface, not name-only exception.
- Strong full-pin-shape distance to EVERY C-record placed-cell box:373.230um <405. Actual semantic first/lastFF bound237.030um. All945physical signal ports accounted by943data+declaredclock/reset; all3227actual sequential cells covered by stronger bound.0missing/empty/mistyped/unclassified endpoints.
- Image VIEWED:216x194.4compact,50.39%fill, regularWinput/Noutput bands, no macro wall, existingGRT0. Original AUTO pin_unreg320FAIL retained; no generic rule edit/waiver. This is geometry-only; TT833/60,FF25,pairCPPR/skew,LEC,DRT,partition signoff still required. HEAD owner authorized diagnosticCTS/GRT with LEC pending; no physical job launched by me.
