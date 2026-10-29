HEAD hk5 tile continuation, 2026-10-29 Codex takeover.
Source: branch codex/head-0830 from claude/die-head-27-1029 a068003085.
Input copied from inherited die-head-27/tile_src8; five-core tile geometry and SOURCE7 private reset/status copies unchanged except adopted hk5 i/o pin move.
Failures retained: predecessor gen8 missing sparse SRAM bb; own gen1 missing v2 SRAM bb; gen2 stale fclk_out_au source clk_t33; gen3 confirmed clk_t33 is absent from the selected physical plan. Existing head_regional_one_entry rule restores old clk_t/clk_c output source contracts to clk; only those metadata entries repaired, without deleting density/tap metadata. Tile itself had source clk already.
Gen4 successful: source7_tile_receipt.json. Actual mapped LEC EQUIVALENT33806/33806, no differs/undecided,191.7s; raw+ODB FACE1159/1159,portbind1190bits0/0,28083regs0fanout>64.
ONE reviewed trial PLACE live intel2:/srv/opentallas-scratch2/claude/codex-head-0830/gen4,ot-heavy oth-ubuntu-2374806-1793288350,client2373627. Check gen4/hd_tile/run_place.log and parent tile_place1.otrun.log. Fresh DPL geometry/full data reach+clock assignment required before CTS.
Physical non-tile forwarded-clock binding remains a separate actual-view check; repairing logical export metadata is not proof of physical phase correctness.
