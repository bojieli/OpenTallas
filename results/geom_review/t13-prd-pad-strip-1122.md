# SerDes t13 standalone parasitic count

The exact retained H17 and kept-wire t10 detailed-route databases both contain 1,089 intentionally coincident M5 pin pairs. The pairs are 544 PMA RX signals, 544 PMA TX signals, and TCK. The normal final report already sources the kit's `pad_abut_strip.tcl` before extraction. The standalone ECO count omitted that step and both original corner logs stopped at ODB-0420. A replay on unfilled `5_2_route.odb` reproduced the failure before any fill geometry. The pinned extractor reports containment of the block-pin shape by a connected instance-pin shape on the same layer. [OpenROAD tmg_conn at 6cb3f2b704](https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/6cb3f2b704/src/odb/src/db/tmg_conn.cpp)

The updated count loaded the unchanged filled `5_route.odb` read-only in both corners. In each in-memory copy the existing helper removed the same 1,089 pre-existing two-point stubs, each on its original net and inside an equal M5 terminal rectangle. Every affected BTerm and ITerm was retained, and the rest of the database's wire IDs matched. The two removal tables are byte-identical at SHA-256 `d95ec7cf2dc8555f87c6af6888f24acfa83c4853aa82552004c4f46c45bb9cba`.

| Corner | Original | Updated slew violations | Updated capacitance violations |
| --- | --- | ---: | ---: |
| TT (TC) | ODB-0420 | 19 | 0 |
| FF (BC) | ODB-0420 | 21 | 0 |

The TT run extracted 411,850 nets, 4,387,563 segments and 5,923,494 coupling capacitors, then passed the placement check. FF read the same 1,001,217,804-byte SPEF. The replay completed in E9 unit `oth-ubuntu-434826-1795377537` with exit 0. Logs and tables are in E9 `/srv/opentallas-scratch2/claude/nearmiss-eco-r1/serdes__t13/rcx_checkpoint_codex/dual/`.

The source fix `15743e90b96` passed four canonical test files and landed on main as `0efed5dab8a`. These are extraction and count results. Timing sign-off and routed LEC remain separate gates. No routing or original checkpoint writes occurred, and the inherited full reroute continues.
