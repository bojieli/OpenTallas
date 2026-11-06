# CODEX bank128 — current state 2026-11-06

Owner: /root/bank128. Own branch codex/hbm-bank128-wface-1106, E6 tree
/srv/opentallas-scratch2/claude/wt/codex-hbm-bank128-wface-1106. Latest READY9ad038fd7e.
No bank form is currently qualified for parent adoption. Functional utilization must <=.45 and cells <=150k; TAP/fillers excluded. Added write guard is conditional/default-off.

## Active work

* **A+realPG6 standard postroute ECO:** E6 /srv/opentallas-scratch2/claude/codex-bank128-wface/eco_A_pg6_std1; unit oth-ubuntu-953001-1793967932,32GB/8threads/disk8GB. One normal clock-frozen pass, hold margin0, no repair-scope flags or constraints change. Base kit pg6_factory_A/ot_hbm_hc_bank128_pair_core_7d149b37532c-_shallow_pg6_vA is immutable. Collect final TT/FF/DRV/DRC, actual LEF, functional util; routed LEC only after signoff PASS.
* **M5 registered face:** intel2 /srv/opentallas-scratch2/claude/codex-bank128-wface/kits/ot_hbm_hc_bank128_pair_core_7d149b37532c-_wface_vB_m5; unit oth-ubuntu-1009405-1793956480, Docker hbmcore-ot_hbm_hc_bank128_pair_core_7d149b37532c-_wface_vB_m5_-1010537. Healthy finite GRT NDR relaxation progression, latest extra21/30. Preserve and collect once; no age-only kill.

## Physical results and diagnosis

* **Fresh A+PG6:** DRC0, ant0, pre-route LEC EQUIVALENT; NOT SIGNED TT+8.79/FF-19.53(273), slew121TT/59FF, cap0. Functional util .44338/112636 cells meets budgets. Actual final LEF PG6/OBS1..6 passes core_pg_mode(False)=grid M6/M7. New standard ECO above owns hold/DRV failure. Parent M6 reservation/M7 landing still owed.
* **Old A:** DRC0, TT+34.56 but released FF-11.33, slew95/39, cap1/1; util .44450/112877 cells. Actual LEF M5 PG buried under M6 OBS, definitive parent blocker. Fresh private aq re-sign confirms NOT SIGNED; no routed LEC because gates fail. Preserved.
* **Canonical registered B:** NOT SIGNED TT-54.07/FF-16.83, slew343/116, cap0, DRC0, pre-route LEC32890 EQUIVALENT; actual functional util .45844 fails conservative .45. Minimal height+2.70um proposal only, no geometry adoption/run.
* **WeightE registered B:** NOT SIGNED TT-73.23/FF-32.85, slew491/198, cap3/3, DRC0, functional util .45844 fails .45. Compact failure/latest checkpoint retained.
* Earlier canon trunk2, weightE trunk, direct-write ECO failures remain recorded in preserved sources/final views. Their channels/direct-write timing did not close.

## Exactness and source

Default-OFF OT_HC128_WFACE registers525 write bits, +1 write programming edge only; unchanged read/go/arithmetic. Full real pair arithmetic lockstep PASS33000 checks/3000 cycles/2949 known outputs, unchanged arithmetic leaves. READY1049a53f89 includes generator/result; bankq/cutmap/full parent excluded. Original boundary proof and three data/address/enable mutants pass. Compiler projection lane separately measured native guarded scheduling; physical default A+PG6 adds0 cycles.

Default-off real PG6 factory ca3f88082a + review19323f08a0 merged; stripe budget13.33%, real M6 rails/vias before GRT, actual metal reviewed. A actual review a6ee5583d0; original RTL/pins/outline unchanged. No active-kit edits.

## h9b routed-proof repair

Physical h9b_vB SIGNED, original routed proof177 differences then173 after built-in no-widen retry; original artifacts preserved. Isolated E5 /srv/opentallas-scratch2/claude/codex-bank128-h9b-diag owns diagnosis, no active experiment now.

READY9ad038fd7e adds generic late anchored-word discovery plus existing-checker untrusted validity hints. Exact captured source/reset64 retained. Automatic anchored siblings/structural closure173→37; all32 own-entry loaded age-diagonal guards prove and full captured miter25567/25567 PROVED. Age stays free outside own wq_pv OR ent_q. Adjacent-entry mutant rejects32/32 and restores37diff; tiny generic wrong output/alias controls rejected. Official released certification remains owed; diagnostic is not final EQUIVALENT. No RTL, reset, warmup, constraints changes. Root owns tool review/release.

## Cleanup receipts (completed; do not double-count)

Stopped only exact obsolete root-backed weightE ECO i2 unit oth-ubuntu-649757-1793945275.scope / Docker prd-wE_vA-i2-2705304, oscillating DRC12..25 at iteration44 and superseded. Preserved qualified views/source/failure/final+useful GRT checkpoints.
E2 exact reclaimed7,380,586,496 allocated bytes, manifest /srv/opentallas-scratch2/claude/codex-bank128-prune/bank_inactive_20261106_113132.json. E6 inactive generation/unused preview reclaimed194,117,632 bytes, coordinator tmp/codex-bank128-pg/E6_inactive_prune_manifest.json. Shared Git/source trees not counted or removed. Fleet/root already received receipts. Cleanup hold lifted; ordinary actual FS/memory admission applies.
