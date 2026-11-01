# Current native595-bit leaf NORMR component

Current canonical ece032 t48+PG bind wrapper `s81p_ot_s81sl_leaf__t2`, part s_0S_L0, executed with actual emitted flattened VP, native VN/VQ and actual functional SRAM models; no VP functional substitute. Clock833ps, all real leaf and landing clock pins use the common source component clock. All packet fields traced from actual C wrapper/XRT wiring. source/stage.json contains exact native file/closure identities (common top glue text hash7dcc944c is unchanged between these binds).

Unit oth-ubuntu-2801747-1793566137 on epyc2, `codex-ds-norm-1101/native_leaf_ece_v4`, PASS three modes: q-only,index0; BF-only HEAD flag,index128; both,index0. Actual NORMR command→VN partial116edges,data3fc9a62e; public668-bit leaf partial117edges. One n_go/metadata/partial/public per command. VP,VNa,VNb,VS,VQ and clocklanding faults all0, landingready1 for each case. Input-bit mutant changes numeric partial to3fc92d15 and also sets VNa fault; RC1 caught.

Fixture49leaf row writes,HLOAD,GAIN,NORMR are actual native operations with checkpoint-derived entry operands; they do not establish final POST residency or final HEAD values. Only the selected native leaf profile is directly executed. Physical phases, all80native cones and absolute HOST/START/global token authority remain outside this component. This result replaces guessed dissolved-VP producer timing for this selected component, not a whole-token PASS.

V2 closure failed MODMISSING for conditional VE qadd/qmul/kand helpers and ot_meso_ring. V3 added exact current ot_s81sl_ve_fp.sv and ot_meso_fifo.sv and passed numeric/flags. V4 additionally checks all actual fault outputs. No DUT RTL change. The original missing-module run is retained remotely; closure_retry.json identifies the correction. The checked-in final tb_current_native_leaf.sv is the exact V4 bench. Historical stage scripts show source assembly; use the final bench when reproducing rather than their earlier two-mode generated bench.

Follow-on V5 drives real public packet rb_v67/rb_d66:35 to measure current RSTD→VQ publication timing; separate live result, not credited here.
