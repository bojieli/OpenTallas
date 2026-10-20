# N59 svc reach > 405 fix (QW-N59SVC 10-20): offline proof of the reach_reloc hook on the svc3 3_5 ODB
Input: ep9 ref_gate/qfd_n59_svc3-20261020-065454 3_5_place_dp.odb (same RTL/netlist as svc4).
summary.json: reach_reloc.py (reach 390): 300,010 stage edges, 284 > 405 before, 0 after, 279 registers moved.
t2b.otrun.log: reach_reloc.tcl sourced on that ODB + detailed_placement (max displacement 1.9 um) + re-audit:
post_dpl_summary.json 0 > 405 after DPL.  cls.py / pos.py: classification of the 283 Codex spans (0c21c3724).
