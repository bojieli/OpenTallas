# CORE-ELEMAB-1115 handoff (2026-11-15 11:xx PST) - DONE
ot_s81hd_elemA_cv SIGNED+ARCHIVED: A1p epyc10 runs2/A1p/eco_cn1/i1 (TT +220.06, FF +8.99, DRC 0, LEC EQUIVALENT 58348/58348).
ot_s81hd_elemB_cv SIGNED+ARCHIVED: B2p intel1 runs2/B2p/eco_ce1115/i1 (TT +191.26, FF +4.81, DRC 0, LEC EQUIVALENT 52963/52963). B1p (epyc7) and A2p (epyc2) also signed, not archived.
Archive: AGIdock /archive/opentallas-signed-1114/s81_head/<core>/ + rtx-pro ~/signed-export-1114 (odb sha256 equal, INDEX.tsv rows appended, 2nd rows carry the view-pack column). View packs s81_head.c.<core> verified IDENTICAL, in _view-packs on both copies.
LEC fix: s81_head 64-edge reset contract (lec64 runs on epyc10 A1x/B1x kits). Durable change: branch claude/hdcore-reset-contract-1115 @5f20b81b701 (READY; train must run test_kit_reset_contract.py under pytest).
INDEX note: the 08:2x NO-DB rows remain (append-only); the last two rows per core are current.
Nothing live for this lane.
