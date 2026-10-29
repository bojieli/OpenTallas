# HEAD strict die port-bind (OWNER 12.17-4 BIND FIRST), DIE-HEAD-24 2026-10-29 05:48 PDT
tools/s81_head/head_die_portbind.py (module check + die_port_bind --manifest-only --logic-free-stub + tie audit + nested leaf pins)
on main 9cddaa527 plans (decompressed beside the original so relative pins_file paths resolve):
- plan_hk3 (results/die_head_21_1028/hk3/plan_hk3.json.gz): 16 masters/326 instances -> hk3/
- hk4 raw RX/TX event (results/die_head_21_1028/hk4/plan_spine_raw_rx_tx.json.gz): 21 masters/351 instances -> hk4_rx_tx/
First hk4 run FAILED only unresolved_children=2: ot_reset_sync (6 dsdv hbc/hostb modules) and ot_s81hd_lep_pair
(ot_s81hd_lep0N_core) missing from the declared manifest. Fix = 2 lines in tools/s81_head/head_portbind_extra.f.
After it BOTH plans PASS: all error classes 0, tie audit 528/0, nested PASS (hk3 3612 inst, hk4 2934 inst);
spare_out_bits = declared open wavefront outs (hk3 1176, hk4 1620). gen/ (generated RTL) not committed (regenerable).
Runs: intel2 ot-run units oth-ubuntu-1391962 (FAIL), oth-ubuntu-1444592 (hk4 PASS), hk3 PASS.
