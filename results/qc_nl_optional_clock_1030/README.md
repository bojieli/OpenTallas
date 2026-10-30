# NL optional clock declaration correction (PREP)

Fresh current CBX native synthesis capsules stopped in normal RTL lint: selected `qfd_tile_nl_rp2_45` references undeclared `ck_rqr2`/`ck_rqr3` when connecting child `ck_rqre`. Both base and selected2000 copies have this incomplete optional ABI.

The existing non-RR ROM-leaf caller already names these ports and forwards actual `ck_rse`/`ck_rne`; the missing declarations are restored. No clock aliases, RTL expressions, registers, parameters, cycles, or macro views change. The active A0 wrapper selects default `GLUE_HARD=0`, where the child does not consume `ck_rqre`; its existing two RQR roots and hardened public ABI remain intact. Any `GLUE_HARD=1` adoption still requires real parent clock bindings, physical pin/model support, and its ordinary proof/physical gates.

Both changed source files parse under Icarus SystemVerilog with implicit-net warnings enabled, with only the preexisting net-assignment attribute warnings. This is a parser/source-correction receipt, not native lockstep, synthesis, timing, or physical qualification. Current native fullwrapper rerun and source peer review are pending.
