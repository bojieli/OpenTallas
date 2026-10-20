HBM-SU6/SFUPS12 10-20: spec lockstep benches of the r12 store (RTL ot_hgi_sfu_programme_store_r11.sv at Codex faaef83bb, sha256
d9202dd6...; other sources = the r11 bench tree) on ot-epyc9 Verilator 5.050 (verilator_version.txt). store_lockstep_r7c + fault1-4
POSITIVE PASS; mutants chain/noshift/rowskew/ioskew/flip REJECTED (expected). split_equiv POSITIVE PASS; 6 split mutants (flip11 early chain11 noshift11 rowskew11 ioskew11) fail as required (split_*.log).
