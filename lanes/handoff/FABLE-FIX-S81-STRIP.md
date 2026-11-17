# FABLE-FIX-S81-STRIP handoff (S81 strip leaf family, 75 types; started 2026-11-16 20:40 PST)

Owner of strip leaf closure end to end. Executor: S81-TYPES-R-STRIP (Opus). Bind: S81-DIE-R2 (C4). Read first: lanes/FABLE-PD-S81-STRIP.md.

## State
- Cause 2 (GPL) MEASURED: die-scale drift in the last Nesterov phase. t75, TD off, same 3_2 DB, exit overflow 0.25 vs 0.10:
  median movable cell moves 98 um, 61,962 / 125,066 > 100 um, 32,817 > 200 um; landing-ring logic leaves its FIRM flops by 150-300 um.
  Density 0.65 / 0.9, TD off, keep-resize 0 do not stop it (worker pilots 1.30-2.07 x). Exit 0.20 is on the knee (t47 1.26 x, t75 1.06 x).
  Exit 0.25: t75 TD off 1.026 x, DPL average 2.0 um / max 91.6 um; t75 TD on 1.017 x.
  Data: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/{dump/ov25.txt,dump/ov10.txt,cmp.py,gpl/t75_td0ov25}.
- SETTING: sparse kits exit GPL at overflow 0.25 (OT_GPL_SPARSE_OVERFLOW, OT_GPL_GUARD rule 3 in face_flops.tcl; gen_phys emits 0.25 on S81).
  Branch claude/s81-strip-gpl-stable-1116 @39ef73a234f (on r430 588ce81), pushed, 24 tests pass locally. NOT gated, NOT READY-posted:
  waits for the CTS reads below. Clone: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/lane (patch script ../patch_ovf.py).
  Interim form for a kit: `override export GLOBAL_PLACEMENT_ARGS = -overflow 0.25`.
- Proof RUNNING (ot-run, TD on, -overflow 0.25, GPL -> resize -> DPL -> CTS -> x1.45 census):
  t47 intel1, t75 epyc7, dirs fable-fix-s81-strip/gpl/{t47,t75}_ov25, driver fable-fix-s81-strip/pilot2.sh,
  census out fable-fix-s81-strip/sta/<t>_ov25, logs intel2 ~/fable-fix-s81-strip/pilot_<t>_ov25.log.
  Compare with the 0.10 kits: t47 -3,956 ps / 15,893 paths, t75 -1,454 / 10,091 (x1.45 census).
- Form B: r432 approved (claude/s81-strip-vp-xr-1116 @1a183f5a920, XR + 16 dswp copies). C4 bind by S81-DIE-R2 not landed.
  Worker asked (post da748a3f) for the bank-end placement mechanism of the vpw + XR flops; not answered yet.
- COORD 21:40 (closure strategy lever 3): setting, form B and dswp copies must be in the D5 tree before r437 releases 29 leaf items;
  tell S81-TYPES-R2 the setting when the CTS reads land (provisional told, post 56392285). No leaf kit at overflow 0.10.
- Stopped: epyc8 unit oth-ubuntu-1637513-1794831534 (old-plan B6gE t72 kit of this lane name, 17 h in GRT extra iterations).

## Next
1. Read the t47 / t75 CTS censuses. If the ring / station classes are gone (only the 285-endpoint vpw class and VP driver left): run
   `ot-run ... tools/fleet/ot-gate-remote claude/s81-strip-gpl-stable-1116@<sha>` and post READY to COORD; tell S81-TYPES-R2.
   If t47 still shows ring logic > 50 um from its flops: PD review fix 4 (ring logic placed with the band).
2. Review the worker's bank-end mechanism; after the C4 bind regenerate t34 / t62 with form B + the setting, image review, GRT read.
3. t34 GRT read of form B decides the 9 far types (> 500 um: t65 t3 t10 t74 t38 t13 t42 t31 t34): under +42 ps -> VS move ~100 um
   toward the banks as a plan row (S81-DIE-R2), not a second stage on all 75.
4. Sign-off t34 / t62, export signed leaves to AGIdock /archive/opentallas-signed-1114 + rtx-pro, then waves over the other leaf types.

## CODEX takeover 22:18-22:44 PST
- Corrected pilots ov25td30 remain running (intel1 t47, epyc7 t75); noB route/CTS launched,39ef stillHELD. Source corrective patch_ovf2 already applied but uncommitted in E8 fable-fix-s81-strip/lane; waitCTS classification before committing/READY.
- New opt-in placement source claude/s81-strip-vpw-bank-1117@e1b62d6096a (existing wt_xr clone). Gen optin OT_S81_VPW_BANK=1 installs bank-endFF allocator and persists ONE existing standard clock tap group, deriving actual hierarchy (t34u_vp,t62u_lf1_u_vp). Addedcells/cycles0. Earlier51ad88e normalGREEN61/61; e1b normalgate running intel2 ~/fable-fix-s81-strip/gate_bank_e1b.log client694480.
- Geometry/DPL proof ONLY (original nonXR copiedDBs, no signoff claim): intel1 fable-fix-s81-strip/bank_t34_dpl placed317VPWFF FIRM,maxbankdistance11.328um,clk_t33 standard118.2um frombankcentroid,DPL0failures/check_placementPASS,maxneighbor1.2um. epyc7 bank_t62_dpl317FF,max13.488um,clk_t36 standard97.8um,DPL0failures/check_placementPASS,maxneighbor1.1um. LOOKED gap-cluster images PASS-COND. Both prove bank-end mechanism, not fullB timing. B adds907XRFF ->1224cohort,<1500tap budget,stillrequiresfreshbind/fullshape.
- t75 actualreach defect isolated390bits onft0station4->5,max442.8um. Simple43.2umshift FAILED545macro overlaps (E8 cong/t75_ft0_shift43.json). Initial south-onlyrepack superseded due narrowroutecorridor. Finalv2 E8 fable-fix-s81-cong/t75_ft0_repack_v2/{rows,report}.json,review.png; builder../repack_t75_v2.py:ONLYstation4(bit_sitesindex3,regsindex4),1105bitsinclpad,maxadjacent380.7um,0macro/otherFT hits,0FF/0cycles. Fullheight east-of-ve_s band399.6,4.32..418.284,54.0,≥2.16macroclearance; LOOKED PASS-COND. DeliveredDIE geometry,notadopted; generatedfixed/clock/PDN review pending.
- Originalt28/t34/t62/t72 stillGRTextraiterations,no5_1_grt.odb; preserveprogressing jobs. At22:37,t34iteration14/30,t28~6,t62~9,t72~5; rankonlywhenreloadedGRTexists.
