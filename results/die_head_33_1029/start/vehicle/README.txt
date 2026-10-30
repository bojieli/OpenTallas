DIE-HEAD-33 (i) START virtual vehicle on src25m, UNMERGED diagnostic with codex/head-kits-0251@735403ad0 tools, Thu Oct 29 06:38:59 PM PDT 2026. PARTIAL.
Data intel2 /srv/opentallas-scratch2/claude/die-head-33/start (leaf/, map/, codextools/ = main tools/s81_head + the 6 codex 735403ad0 files).
DONE (CHECKED):
 1 local wavefront reset provider (leaf_reset.sh = Codex hk5_leaf2.sh steps 6-9): first pass FAILS closed exactly like Codex hk5:
   r91_3 raw reset hop 410.73 um > 405.  reset_fit25.py = Codex reset_fit.py move of START body r91_3 (+8.631,+0.013 um, same rect,
   overlap-checked; no clock/source/RTL/cycle change) -> leaf_reset_fit.sh: max reset hop 402.112, 0 over 405, 164 type aliases,
   settle 74 (raw span 68 + 4 guard; +10 boot cycles, 0 steady). provider: 1226 stages, 4786 FF, 357 die outputs, 1158 reset ports.
 2 Yosys map-before-flatten (map.sh = codex map_inventory.sh, orfs image yosys, docker 16 GB): 13264 cells, 4786 FF = 4786 planned,
   0 unmapped (summary.json).
BLOCKED: 3 head_start_pack.py stops 'cell y=7740.44 is not on native 0.27 um row phase' at root stage b0: the stages are emitted
   at the ot_clk die-tree node sites (b0 at (8760.96,7740.44); src25m kit_s25 ctree.tcl = codex-head-ca-0840 fresh tree), which are
   not on the 0.27 row phase (core origin 0,0).  HEAD-START-2's vehicle used Codex's separately legalized 'legal1' clock tree
   (final5/clock, b0 at y 7742.52), produced by an unscripted Codex step not in 735403ad0.  Remaining chain after a legal tree:
   pack -> head_start_edge_drivers (BUF8 data chains) -> head_start_local_clock -> head_start_route_overlay on a src25m combo kit
   -> GRT50 TT/FF + START STA (head_start_2 grt recipe) -> dd parse (head_start_3 dd_parse.py) -> data-aware re-plan + CA.
