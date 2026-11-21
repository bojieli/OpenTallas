# FABLE-FIX-S81-COLROM-R4 handoff (started 11-21 10:3x PST; successor of FABLE-FIX-S81-COLROM-R3)
Dirs: R4 = epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r4 (scripts, pkg/, gen_j7c/, logs); tree + gate on epyc10
/srv/opentallas-scratch3/claude/fable-fix-s81-colrom-r4 (candJ7cG, gate_j7g). Hub log intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r4/chain_j7g_otrun.log.

## Inherited chain DIED (R3 oth-ubuntu-1549570-1795283695, rc 3, 10:36 PST)
src_manifest build of main 2ddb19c (scope tools rtl physical results) refused "tree and tracked list differ": 7 tracked symlinks that point at
directories (physical/hbm_attn_tile_r/bank_v7/ot_attn_bank_ew136, ..., results/qc_die33_1029/bind/cores). walk_tree() uses os.walk, which lists
a symlink-to-dir under dirnames, so it is never "walked" -> any full-scope git-archive build fails. Tool bug (flow lanes); not on my path.
Old-view gate2 replaced by the J7c gate below (new view inside the real J7 tree).

## Running: J7 gate of the NEW view (unit on epyc10, ot-run --priority plan --plan-job bind)
chain_j7g.sh = mk_j7g.sh (REAL copy of S81-J6-ASSEMBLY-R4 candJ7c [composed + j7_post] -> candJ7cG; + guard RTL + view rdxg_1121 + HCP entry
from main 93ad08b4406; + signed_view_sha_s81.json ot_s81_cfg7_seq _tt.lib e93af8bb...; + gen_colrom_rows.py (RDX_LIB rdxg) rows/repoint/sidecars
on the candJ7c plan -> R4/gen_j7c; + dead-input re-proof reprove41_cfg7_rdxg_j7_r4 under guard RTL; landing sidecar check)
-> gate_j7g.sh (fresh external ELAB, strict bind, LATCHECK, G0 vs gates/candJ7c, PRE).
Package for assembly = R4/gen_j7c/{colrom_delta.json,plan.json,sidecars/} + R4/pkg/src (view, RTL, registry) + R4/mk_j7g.sh steps 4-5 (= j7_post with VIEW=rdxg).

## Deleted (ot-delete): epyc7 R3/rdxkit, R3/ov1; epyc8 R3/rdxkit, R3/rdxkit2, R3/view/*.part.
## Next: gate result -> hand to S81-J6-ASSEMBLY-R4 (or by 19:00 tell them to keep a10c16b8 out of J7d). Step 5 rep kit from candJ7c sidecar.


## OPEN-RELAYS from FABLE-FIX-S81-COLROM-R3 (stand-down 2026-11-21 10:28 PST)
Unanswered failure classes; post RESULT or ACK naming the class id (fail_route accepts the whole owner chain).
- FAIL-CLASS 958ddd525b s81/waiter RESULT FAIL: open 210 min, 3 item(s): OPUS-FIX-S81-SVC-R5@04:59, OPUS-FIX-S81-SVC-R5@05:10, OPUS-FIX-S81-SVC-R5@05:14; owner chain FABLE-FIX-S81-LEAF-R5 > FABLE-FIX-S81-LEAF-R6 > FABLE-FIX-S81-COLROM-R3
