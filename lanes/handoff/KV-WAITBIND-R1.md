# KV-WAITBIND-R1 handoff (Sonnet), 2026-11-21 20:00 PST
Base: KV-PLAN-R6 D27d3 plan 48b92c30c8f6 sealed 19:42 on epyc8 (apply ~21:30); D28 (stable type keys) follows. Holds in kit_wave.json hold_items are NOT dead: pc x4/pv_v6n/hub_Wi lift at D27d3 apply (KV-PLAN-R6 does it), hg/hgi/pv wait for D28 (FABLE-PD-KV-2000 / COORD: no new hg/hgi/pv builds on D26/D27d3).
Routed: 6 hgi + 4 pc + pc_v3 + hroot rows in autopilot/COORD-ROUTED-OWNERS.tsv (commit d99dfea8df1). pv/hub rows already have live owners (PV-R6, HUB-R5).
hroot: FAM-KV-HROOT-R1 chain epyc8 /srv/opentallas-scratch2/claude/fam-kv-hroot-r1 (bindgate running, unit oth-ubuntu-3836537-1795316483). Next: private-spec kit per FAM-KV-HROOT-R1.md Next 1.
CBC-FALLBACK (hub_Wi, pc_v3): cbc_pass on D27d3 -> epyc8 kv-waitbind-r1/cbc_out; rows go to KV-PLAN-R6 for D28.
COORD 20:0x: HGI-R6, IOPC-R4, FAM-KV-HROOT-R1 stood down. I own hgi x6 + pc_v3 until D28 adopts, and the hroot chain (unit oth-ubuntu-3836537-1795316483 adopted). When D28 lands: rebind hgi + pc_v3 at once, start private kits. Freeze until then.
COORD correction: FAM-KV-HROOT-R1 is live and owns kv3_hroot + unit oth-ubuntu-3836537-1795316483; I dropped hroot and killed my waiter. I keep hgi x6 + pc_v3 until D28.
COORD correction: OPUS-FIX-KV-HGI-R6 is live; hgi x6 rows back to it, I do not rebind them. I keep kv3_pc_v3 + CBC rows until D28.
Poll armed 20:3x: local bash bg task (/tmp/kwb_poll.sh, 5-min loop) ends on KV-PLAN-R6 APPLIED/APPLY post or kit_wave event D27d3/D28. Then: pc x4 + hub_Wi private-spec on applied plan; pc_v3 on D28; current main (650916ebb262 fix); avoid epyc7.
