REFILL-1725/KVREG 10-19: KV-die MU bench + mutant regression (MUKVREG2 legs, 102 cases) re-run after the PVFST + HCTL2 merge on
current main 566b12ac1 + today's KV branches kv-pc2 ebc61997d, kv-grp2 a5b15ce36, kv-emb2 d9631325d, kv-health e336c7782
(merge commit fa813c53c on claude/refill1725-kvreg-1019; conflicts resolved: kv_static_die.py RTL_FILE suffixes _rl/_sr/_gs2
combined; p192_mir macro json + EMB ctx files kept from main). RESULT 102/102 as expected, 0 unexpected; 13/13 host MU0
identities identical (out/TABLE.md, `python3 table.py out`). Run dir ot-epyc8 /srv/opentallas-scratch/claude/refill-1725/KVREG
(launch.sh; units oth-ubuntu-18{06566,08413,09577,11540,14023,16378}-17924576xx). Logs only (no build products) under out/.
Not covered: attention vehicles (KV-TOK3/KV-ATTN2), lane-local benches of PC2/GRP2/HEALTH (run by those lanes).
