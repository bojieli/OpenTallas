# HBM-CORES-KITS-10 (2026-10-29): ring_ag qid -> strap_qid + ring V1/V2 builds

COORD 05:35 ASK YES: the ring_ag quarter id `qid` is a declared ID strap (OWNER 10-25 option B): port `strap_qid`, tied at
the parent, `set_false_path -from [get_ports {strap_qid}]`, no pin register. The routed near miss (TT -24.1 ps / 2 ep) was
the timed qid face FF -> lane cap_carry_we path (HBM-CORES-KITS-9, CHECKED).

* Generator (shared, ROOT review): `face_shell.py` passes `strap_*` inputs through (no face register, `face_shell.json`
  `straps`); `gen_core_kit_hbm.py` emits the false_path, `sdc_lint.json` `straps` and `straps.json`. Test
  `test_face_shell_strap.py`. The oneclk ring wrapper renames its port; plan pins + bind strap declaration rename at the
  same DIE-HBM-13 / HBM-BIND-1 event.
* Kit-local (existing Codex kit, epyc2 /srv/opentallas-scratch2/claude/kits10-1029/ring): `kit_strap.py` (RTL shell,
  pins, io.tcl, SDCs, straps), `strap_eco.tcl` (ODB netlist ECO: delete face DFF+INV+hold/input buffers, loads to port,
  BTerm rename; clock cells FIRM), `yosys_strap.py` (same ECO on 1_2_yosys.v for LEC).
* V1 `run_v1.sh`/`v1_eco.tcl`: Codex pad1v2 GRT + strap ECO + repair_design slew 50/cap 20 + FF hold margin 15 -> DRT.
* V2 `run_v2.sh`: retained CTS + strap ECO -> GRT SLEW_MARGIN 50 / CAP_MARGIN 20 / HOLD 10 -> DRT.
* `hnx_margin10.tcl`: REBAL HNX restored35 FF hold margin 10 before DRT (clock frozen + asserted).
