# PRE-QC-GENCHECK handoff (11-24 02:5x PST) - SCOPE DONE
Pushed main 6490dc4988ae: derived_drop ENTRYFOOT (a tap==footprint, b tap follows moved core, c STALE-EXPORT-TAP >300 um), gen_rtl Landings plan_path, plan_gate_pre GENDRY observer->kit-rtl + OT_REPO_ROOT, gen_phys.view_root(); tests test_derived_drop.py / test_pre_gendry_1123.py.
Proofs: QC 12b66c0e4829 FAIL cl622f65d2 clk_c0/clk_c2 only, cecdcb2a3b4b PASS; KV A5 1463/2601 (= KV-SENDER-SKEW tsv); S81 c8 48/1244 20 types; HEAD r18gw 3/67; QC GENDRY 14 types: 10 kits, cl622 real error, 3 over my cap.
Open for others: owners repoint source_clock_port; QC-ALLFIX 51-type GENDRY needs OT_PRE_GENDRY_TIMEOUT_S 3600.
