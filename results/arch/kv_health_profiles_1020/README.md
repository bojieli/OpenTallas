# KV health native parameter profiles

Exact selected-view/native routed-netlist audits, base GEN9 813ef84a8.
Three positive audits prove every port and paired state bit (2/2 each); the qkd_hp_or2 MUT=1 control fails both equivalence points. Liberty function models and closure identity are checked by the existing audit tool. Immutable closed archives are qkd_hp_or2-o1-a11f46db5, qkd_rlys_1-v1-6da52734e, and qkd_astk_fault_join-r1-849bb441e.

Frozen receipts in receipts/ name exact RTL/view artifact hashes. Add entries from receipts/profiles.json to the die profile manifest without changing existing entries or receipt paths. Nonparameterized relay/sticky modules carry empty parameter dictionaries. Health OR defaults to MUT=0.

This proves leaf logic and parameter identity only. The complete die health reset flush, physical path/phase, retirement, PG and strict bind remain separate obligations. No source or shared helper changes.

All synthesis/equivalence ran through ot-run on ep5, unit oth-ubuntu-166804-1792493956. Exact equiv logs and commands retained; their SHA values match the audit JSON.
