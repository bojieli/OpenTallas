# LEAF-ROUTE-CBC handoff (11-23 ~02:40 PST)
OWNER 6079af4: J9 is the ONLY S81 event (cut 18:00). R5 wave A intake 10:30, hard stop 12:30.
Work dir E9=epyc9 /srv/opentallas-scratch3/claude/leaf-route-cbc/row ; fork j9tree ; scripts there.
## Delivered row 3d (R5 manifest aa6ce7d GATED-PRE)
J9-LEAF-LANECH+EDGESTRIP+FTCORR+LANESHAPE+KV: ops row/j9F_type_ops.json 57c87ed2a8f0 (grown frame on VIS-DIE v3 c9a4768659a1, replayed AFTER die_grow); ref row/j9F_final2.json 934aee47869d; PRE PASS.
Build: row/j9full.sh (grow v3 -> reshape 20 types -> lanech_row --ftcorr leaf -> lanech_row --ftcorr kv t1/t3/t4/t5 -> hopfix -> tapfix -> reprice) then row/j9Ffix.sh (nullfix, PRE, mkops excl kv t5).
Lane core kit SIGNED (corekit/ot_dsrom_su_hcpost_lane_pr_ls: TT +78.94 @833, LEC 0, 277/277). LANESHAPE files' shas were sent to R5.
## Running
- strict bind+LAT+G0 on j9F_final2: row/j9F_bind.sh F, --mem 380, logs row/gateF.otrun.log + j9gateF/.
- in-plan probes (intel2 .../leaf-route-cbc/probe/probesF.sh): t44F t58F t61F t4F t9F kv1F (+ t44A2 on old A plan).
## TODO
- On VIS-DIE v4 (COL Y shift): re-run j9full.sh + j9Ffix.sh on the new base, then send the ops sha to R5 (by 10:30).
- Renders: read t44 max tap load (rc7), t58/t61 corridor (rc4/5), t4/t9 window edge (COORD ruling 2), kv t1 (rc12). Set PROBE-PASS only when every class is covered.
- hg-S81-REACH pad->crr: needs an RTL stage (ot_s81sl_crr PRE). Proposed to R10 a1b4f3afb5616ae9d; awaiting reply on who writes it.
- Send R5 the gate result.
