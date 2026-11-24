# LEC-VACUITY-SWEEP handoff (COORD split 11-23 22:4x PST)
Job: find every LEC/equivalence pass claimed since 11-22 that used a vacuous method (ABC dsec on a 1-output yosys miter), classify SOUND/VACUOUS, rerun vacuous ones soundly with a seeded negative control, fix shared scripts on main.

## Findings (23:2x)
- dsec vacuity reproduced (intel1 /srv/opentallas-scratch2/claude/LEC-VACUITY-SWEEP/dsectest): gold q<=a vs gate q<=~a, 1-output `miter -equiv`: dsec says "Networks are equivalent"; dprove and bmc3 assert in frame 0; two-file `dsec gold.aig gate.aig` says NOT EQUIVALENT.
- Only vacuous script found fleet-wide (find over all live hosts' scratch, rt/current, main): intel1 QC-TTC-RETIME/tool/lec.sh (lane-private). Users: QC-TTC-RETIME rs1 "LEC pass", QC-TTC-R2 unkeep pass, FABLE-RC-QC accept (withdrawn 22:42). QC-TTC-R2 owns the rerun (lec_seq.sh = dprove + bmc3; reg-corr CEC).
- main/rt: tools/rtl_implementation_campaign.py uses dsec in the TWO-FILE form (sound). kv_leaf_lec.py uses dprove on a 1-output miter + constant-output guard + mutant option (sound). All kit LEC = tools/die_plan/lec.py (key-point CEC, per-point miter outputs, &fraig/&sat/&cec; sound). Yosys equiv_make/simple/induct/status -assert scripts and sat -tempinduct: sound methods.
- => no shared script on main is vacuous; step 4 (fix on main) not needed.
- KVLEAF t2 masters (11): all lec.py. Negative controls (seeded inverted PO bit, same scripts/mounts, my dirs):
  - ikw (epyc9 neg/lec/ikw_neg): NOT EQUIVALENT, differs 1 = po:o_d[137] (the seeded bit), 43124 proved. PASS.
  - kvq (intel1 neg/lec/kvq_neg): NOT EQUIVALENT, differs 1 = po:e_o_e[0], 15509 proved. PASS.
  - ikr (epyc9 neg/lec/ikr_neg, hints + overlays as ikr_p1h4, inputs identical but netlist): NOT EQUIVALENT, differs 1 = po:r_d[0], 30153 proved. PASS.

- Side finding: ikw 6_final.v and logic_final_m5.v have 527 of 544 outputs both cell-driven (net named as the port) and `assign port = \port..NNNN` (output buffer chain) = writer name collision; LEC sees the INV driver and bypasses the output-buffer/hold chain.
## Files
- mutator: epyc9+intel1 /srv/opentallas-scratch2/claude/LEC-VACUITY-SWEEP/mutate_po.py
- neg scripts: .../LEC-VACUITY-SWEEP/neg/{lec_r4_neg.sh,ikw_rc_neg.sh,kvq_neg.sh}

## CODEX notes, 11-24 takeover
- ikw exact OpenDB probe confirmed 527 real, distinct source and terminal nets whose Verilog names collided after the hold hook moved the port. Existing ODB preserves unique pin drivers. Private corrected serialization renamed only source-net labels without saving ODB, then wrote logic_final_namespace.v.
- Scope proof E9 LEC-VACUITY-SWEEP/ikw_writer_codex terminal_cones.log, unit oth-ubuntu-2118653-1795531628: all 527 chains recovered from actual emitted netlist and proved identity with cell Liberty; final bit o_d[137] inversion alone detected. Full core positive/negative units oth-ubuntu-2030929-1795531460 and oth-ubuntu-2031082-1795531461 active. No count change.
- Production OUTHOLD name fix landed OpenTallas main e19fb506fac6. Proc renames only the detached source signal whose name equals the moved port, selects a free deterministic name, preserves OpenDB connections. Canonical tools/ref_tile/tests/test_pin_reg_split.py 2/2 passed. Fixture native PG rules fixed its pre-existing OT_PG_UNKNOWN_DOMAIN. E1 source control oth-ubuntu-3701960-1795531930 uses original producer and fails specifically on o2 shadowed internal name. This does not reclassify an old LEC or SIGNED record.
- Full corrected ikw serialization positive is EQUIVALENT 43,125/43,125 (epyc9 oth-ubuntu-2030929-1795531460; neg/lec/ikw_namespace_pos/lec.json). Full final-terminal mutant remains active; scoped 527-chain mutant already caught. No change to old artifact or count.
