# SIGNED-RECOVER handoff (11-14 ~09:00 PST)
Findings: 59 of 66 LOST rows have explorer signed-store records whose 6_final.odb is present in AGI /archive/opentallas-signed-1106/<host>/... (audit searched by path only). Records: epyc8 explorer-2-work/signed-store/records (932, all SIGNED, carry size+sha256 of each file and embedded signoff.json).
View pack = epyc8 explorer-2-work/store/elements/<node>/*.json + objects/<xx>/<sha>.br (1.14M files, 4.0 GB); pulled to rtx ~/signed-export-1114/_view-packs, then to AGI.
Actions running: AGI server-side copy 1106->1114 for 175 dirs; fleet export of 36 explorer-signed elements with no record (kq_/QC, HBM, KV) from live hosts; rtx<->AGI sync.
Work dir: scratchpad sr/ (master.json, planA.json, fleet_plan.json).
