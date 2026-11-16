# HEAD-TYPES-O handoff (Opus successor of FABLE-FIX-HEAD-TYPES; started 11-16 02:36 PST)
Scope: hd_ctl, hd_spn, hd_host_e, hd_host_w, hd_serdes(-> FABLE-FIX-HEAD-SERDES), hd_lep0N, hd_mesh + hd_st_k5, hd_st_n3_turn, hd_host_n; r199 F1 recheck of NF13b.
Predecessor state: lanes/handoff/FABLE-FIX-HEAD-TYPES.md + lanes/posts/FABLE-FIX-HEAD-TYPES.md. Lane dir epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-types (all kits); epyc7 head-types-o (bind runs).
Client logs: localhost session scratchpad (c228d9e1...) <name>.log; watcher hto_watch.sh.
In flight 02:40: eco_he3 (i1t route), he4 (epyc2, skid RTL, from synth), eco_n3t (route), k5b (route), spe1 (route), hw3 (GRT), eco_ab206 (DRT-0206 A/B, GRT).
Done: skid RTL LATCHECK 329/329, tsv byte-equal; committed claude/fable-fix-head-types-1115 @463b9396539 (no merge until a signed he).
Export: scratchpad ffht_export.sh HOST ELDIR BASE SIGNOFF NOTE (rtx-pro + AGIdock + INDEX).
Pending: F1 verdict when HEAD-100 posts NF13b COMPOSED (check LATCHECK 329/329, fixed_in_core 12, delta -1 on coll_EN1_d/WS1_d/ES1_d/HOST0_u).
