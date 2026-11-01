STA-0171 numeric-parameter physical serialization class (DIE-QC-59S, 2026-11-01T08:44:50-08:00).

Problem: OpenSTA/OpenROAD read_verilog rejects every instance parameter override, numeric too. A signed QC child kept
as a black box by its eager *_bb.v metadata header (codex 50faadff5, OT_NATIVE_BB_METADATA) keeps the parent override
(qfd_dv_s8_vm8q_rp1: .MIF(MIF) -> MIF=0) in yosys, and 1_2_yosys.v carries
  qfd_dv_s8x_vmr #(.MIF(32'sb0..0), .MUT(32'sb0..0)) u_va (...)  ->  [ERROR STA-0171] 1_2_yosys.v line 90, syntax error

Class fix (tools/die_plan/native_bb.py --physical-synth, already applied by every gen_phys kit run_kit.sh):
after the existing 1_2_yosys_native_metadata.json write and ROM label unset, OT_SIGNED_PARAM_SERIALIZE reads every
override on a master declared by an eager *_bb.v header (numeric-default params only; ROM string labels keep their
own rule), removes it ONLY when it equals that header default (two's complement at the cell width), and stops synth
on any other value (1_2_yosys_signed_params.json lists the errors; no .ys is written). Kits without *_bb.v headers
skip the block in Tcl. Golden RTL, the metadata JSON (keeps MIF0/MUT0) and the LEC RTL side are untouched.

Repro (pinned openroad/orfs:asap7lock sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29, ot-run intel2, minimal ORFS make synth = yosys + synth_odb
OpenROAD read_verilog/link_design). Inputs = actual signed headers, native RTL and TC Liberty of codex 50faadff5 (lib
and module SHA = its manifest.json) + the LEFs of /srv/opentallas-scratch2/claude/codex-qc-param-preload-1101/input
(inputs.sha256). Top = vmr #(.MUT(0),.MIF(P)) + crh #(.MIF(0)) + crh unparameterised.
  main (origin/main native_bb.py): rc 2, [ERROR STA-0171] 1_2_yosys.v line 90 (main/make_synth.log)
  fix  (this branch):              rc 0, 3 default overrides removed on 2 masters, no '#(' left in 1_2_yosys.v,
                                   1_synth.odb written, link_design top clean (fix/)
  neg  (fix, vmr .MIF(1)):         rc 2, OT_SIGNED_PARAM_SERIALIZE ERROR ... .MIF(..01) != signed header default 0
Unit test: python3 -I tools/die_plan/test_native_bb_params.py (unittest.log, 7 tests OK).
Replay: bash mk_repro.sh R WORKTREE MAIN_NATIVE_BB; ot-run --mem 5 -- bash run_repro.sh R
Claim boundary: frontend/serialization only; no child functional proof, FT wiring or route claim.
