# QC-STB-CAP handoff (Opus 5.5, COORD 11-23 23:0x PST; one job: QC soft types over cell cap; fw = QC-FW-CAP)
## Scope order (COORD + FABLE-RC-QC fe790233): evidence table -> relay-INV share -> hc3 ruling -> splits only if still needed
## Done
- 23:05 EVIDENCE TABLE posted (hub d4376ecc): 85 kits <72h. st_b 5 SIGNED at 405-441k place non-tap; hc0-3 all signed (<=406k); sle_ctl (GRT max, 0 signed, 96.5k BUF at place) and su_c (CTS max) are the count-driven ones.
- Relay-INV synth census (epyc10 /srv/opentallas-scratch2/claude/QC-STB-CAP/census, inv_census.py + class counts): ctl 36% chain INV (fw-like), st_b 11.7%, hc1 9.0%.
- Proposal: die-wide FWCPL instead of per-type splits; hc3 ruling = no change (type_split only if <=350k ever binding).
## Running (done 23:3x)
- epyc10 QC-STB-CAP/probe/{stb,hc1,ctl}: synth-only OT_DLY_CPL measurement on kit copies (cplprobe.sh), logs tmp/cpl_*.log.
## Files: localhost scratchpad stbcap/{collect,extract,fam,table}.py ; kit list = intel2 /tmp/stbcap_collect.json
- 23:3x CPL MEASURED (hub 899bd382): phase-1 synth ctl 296.7->261.4k, st_b_v1 407.8->398.2k, hc1 392.9->394.4k. Rulings: no per-type splits for st_b/hc; die-wide FWCPL (QC-FW-CAP row) lifts st_b_v1 under 400k + ctl/su_c lever; hc3 no change; st_b_v1 type_split = fallback only on request. Probes done, nothing running.
