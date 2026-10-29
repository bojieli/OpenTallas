# QC A0 ICG2 native assembly continuation, 2026-10-29

Source base: approved7946a8448d0. Native synthesis (Yosys0.68 slang in ORFSasap7lock) exposed a declaration-scope error before placement. The ck_rp/tx/lsl/fa/region wire block followed the generated ICG2 instances. Slang connected those earlier generated instances to local implicit nets, leaving the later parent clock wires undriven; opt_clean removed33/35 unconnected gates and10 ROM children. Move the unchanged declaration block before the generate. Verilator functional elaboration is unchanged; its old full ICG2 miter could not expose the slang binding mismatch.

Actual mapped1_synth.v census:

|form|ICGs|enableFF|ROM|rawfault|NODE|
|---|---:|---:|---:|---:|---:|
|oldNL|1|0|0|8|0|
|fixedNL|34|66|10|8|0|
|oldNK|1|0|0|8|1|
|fixedNK|36|64|10|8|1|

Both old and fixed emit2660 warnings for historical unused rom_rd wires. That warning count is not the fix criterion. Native child/clock connectivity is the measured fix criterion. Original failed native assemblies remain in intel2 codex-qc-a0-0830/kits without r1; fixedr1 siblings preserve separate source+logs. Corrected NL synth spill epyc2unit2587038 complete0; NK intel2unit2231802 complete0.

Approved ONE placement each continues with ICG2; no CTS/GRT/DRT/signoff claim. NK uses GEOM56V1L legal homes; NL retains reset6 targets. Review results/geom_review/codex_qc_a0_icg2_0830.md and personally viewed macro picture. Runtime proof owner /root/qc_proof is closing actualREGROOT3 mappedleaf operational proof and controls before signoff. Wire declaration reordering adds no state, latency or pins. ExistingNKlocalreset+1bootedge remains as priced in its inherited candidate.

Candidate ICG2 physical costs relative to ICG1: NL+33ICG/+66enableFF per tile; NK+35ICG/+64enableFF. With48NL/720NK this is+26784ICGs/+49248FF; no data-path or steady-state-cycle change. Adoption and actual power/PG remain with QCdieowner.
