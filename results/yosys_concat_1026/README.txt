YOSYS-CONCAT 10-26 (QC-LEC-4).  Flow yosys = /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 0.68+post (openroad/orfs:asap7lock).
Reference frontend = read_slang in the same binary.
probes/frontend_probe_verdicts.txt   520 trigger-form probes (read_verilog -sv vs read_slang): defines YC1/YC2
probes/lint_flags_on_probes.txt      rtl_lint scanner on the probes: 0 DIFF missed, conservative flags on EQ forms
rtl_all_hits_before_fix.tsv          scanner over all rtl/ before fix (294: 275 YC1, 19 YC2)
release_hits_before_fix.tsv          hits inside the S81 / QC / KV / HBM die closures (20 hits, 15 files)
rtl_all_hits.tsv / release_hits.tsv  after fix: 274 left in non-release/test RTL, 0 in release closures (895 files)
probes/expr_sites/                   per rewrite site: orig expr (slang) vs fixed expr (flow read_verilog -sv) and orig expr (flow)
lockstep/results.txt                 iverilog 12 lockstep, posted static (LOCAL_CTL 0/1) + native: RTL, mutant, flow-netlist fix/orig
module_equiv/                        A = orig(slang) vs fix(flow read_verilog -sv); B = orig(slang) vs fix(slang); equiv_simple/induct -seq 2
   A residue equals orig(slang)-vs-orig(flow) residue (no new diff), but A did not flag the known posted bug -> weak; B is the rewrite proof.
