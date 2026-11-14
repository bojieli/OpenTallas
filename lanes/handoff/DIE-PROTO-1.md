# DIE-PROTO-1 handoff (11-14 04:3x PST, Opus) -- DONE, no jobs running
## Scope
Die GRT + die STA prototypes, all 4 dies, current plans, plan-shape abstracts (OWNER 11-14 00:4x). ADVISORY, DO_NOT_COUNT. RESULT lines posted (HEAD 01:4x, S81/KV/QC 04:3x).
## Where
epyc10 /srv/opentallas-scratch2/claude/die-proto-1b/<die>/cur1114: CHAIN.log (proto_die.sh: kit, GRT TT/FF/off, stock-tree STA), c2/ or ../c2_cur1114 (dieclock_regeq model + --routed), dsta/ (die_sta flat data STA; HEAD only finished).
Scripts in that dir: run_die.sh <kv|s81|head|qc> [tag] (W/P per die; QCP env override), proto_die.sh, chain2.sh/chain2b.sh/chain2r.sh (balanced clock leg; chain2r = routed only, reuse model), dsta.sh, typepairs.py (per type-pair clock damage; works on proto proofs, not routed proofs), qcscan.py (drops orphan core taps -> qc_s29_dp1b.json).
Launch from intel2: ot-run --crit --hosts epyc10 --mem 64 --threads 24 --dir $B --priority die -- bash $B/run_die.sh <d>.
## Gotchas
- dieclock_regeq --routed uses fixed docker names (rf2regeq-it0-grt-FF): never run two dies' routed legs at once (KV collided with HEAD).
- proto_die.sh rm -rf's the run dir: start chain2 legs only after it (or use chain2b, outside D).
- die_sta flat data STA: ft nets of the GRT SPEF are not named as in die_top.v (ft wire RC not annotated); S81/KV runs did not finish in 3 h.
- S81 and QC need their regional clock forms (regions-from / qcreg3); the die-wide tree is refused (structural).
## Next
S81: re-run die STA on B2u per region once S81-B3-CLK posts the region map. KV: re-run chain on kv102sem. QC: after DIE-QC-103 fixes the cbn_q00 taps + sle_su_c pins, run qcreg3.
