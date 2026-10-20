KV-TOK 10-19: MUKVREG2 legs (102 cases) re-run on the newest KV source claude/kv-gen8-1019 @06a659135 (+ bench-only overlay
97cd2e0dd). RESULT 102/102 as expected, 0 unexpected; 13/13 host MU0 identities identical (out/TABLE.md, `python3 table.py out`).
Run dir ot-epyc8 /srv/opentallas-scratch/claude/kv-tok/MUKVREG3 (launch.sh). First attempt omitted physical/asap7_memory_macros
from the staged source (hroot/peer cp errors, host MU0 DIFFERS as a consequence): deleted, this is the record.
