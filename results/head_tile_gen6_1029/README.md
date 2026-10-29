# HEAD hd_tile canonical gen6 source gates (DIE-HEAD-24, 2026-10-29 05:35 PDT)

Kit = byte copy of Codex gen5 (epyc2 codex-head-tile-source7-1029/gen5, 16 RTL files identical to gen4) with ONE change:
kit face_guard.py = this branch (0cd17ec78), run_kit.sh ODB face guard passes --types-from $N (the hierarchical 1_2_yosys.v).
gen5 failed only FACE_GUARD_ODB 1157/1159 (land_slot x2) because the ODB-written netlist is flat (1 module), so the typed
status-copy / origin_start proofs of 445fb941c had no module types.

ot-run unit oth-ubuntu-3757127-1793277060 on epyc2, exit 0 (run_synth.log): KIT_PREFLIGHT PASS, PORT_BIND 1190/1190,
FACE_GUARD 1159/1159 PASS, REG_FANOUT 28083 PASS, FACE_GUARD_ODB 1159/1159 PASS (types_from recorded), LEC EQUIVALENT
33806/33806 (0 differs, 0 undecided). Synth only: no PLACE/CTS/GRT. Runtime epyc2:/srv/opentallas-scratch2/claude/die-head-24/tile_gen6.
Controls on the actual gen5 ODB netlist: no --types-from -> FAIL 1157; status-copy module renamed -> FAIL 1158; origin module renamed -> FAIL 1158.
