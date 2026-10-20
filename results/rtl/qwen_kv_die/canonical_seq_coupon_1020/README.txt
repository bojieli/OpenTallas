ONLY DFFHQNx1_ASAP7_75t_R and DFFASRHQNx1_ASAP7_75t_R are qualified by this packet.
No other cell or physical closure is invalidated or qualified by this result.

Normalized ASR vs exact PDK altos_dff_sr_0: PASS544 checks.
All binary D/reset combinations from initial q0/q1, all16 reset-pair transitions at stable clock0/1, both-low -> release either reset, data hold and falling clock. Inputs settle before a positive clock edge.
Normalized plain HQN vs exact PDK altos_dff: PASS128 checks from initial q0/q1, all binary D/clock transitions with setup, falling-clock and data hold.
Both output QN <= !D on a positive clock edge. ASR RESETN0 presets QN1; SETN0 clears QN0; both0 clears. The priority-masked set event handles release SETN while RESETN remains asserted.
The scope is fault-free binary functional behavior. Notifier events, X input timing violations and transistor-level metastability are not modeled. Independent arbitrary binary register initialization is addressed separately in block cold-boot proofs.

ACTUAL imported ASR from this image/model FAILS this same UDP coupon: normal RESETN=SETN=1,D=1 gives canonical0/imported1. Original body asr_imported.v and asr_imported.log are preserved, not inferred from a name. ACTUAL imported HQN PASSES128 (dff_imported.*). This finding is specific to the pinned image/Yosys/import recipe; other owners must test their exact imported model with --imported-model.

Import recipe that produced the failing model:
Yosys0.67 git2d1509d1b, exact immutable Docker image in image_id.txt.
read_liberty -ignore_miss_func AO.lib; read_liberty -ignore_miss_func INVBUF.lib; read_liberty -ignore_miss_func OA.lib; read_liberty -ignore_miss_func SEQ.lib; read_liberty -ignore_miss_func SIMPLE.lib; proc; write_verilog library_model.v
The five original source Liberty hashes are library_hashes.json; full imported model hash is canonical_model_identity.json.

Reusable source-pinned command (fleet, Icarus required):
python3 tools/qwen_kv_die/canonical_seq_coupon.py --pdk-seq CANONICAL_SEQ.v --pdk-sha256 6e63ff4b5587097a76bf395c6f2383035368d5c8d95dbf551ba324d3a9537fde --out NEW_DIR [--imported-model ACTUAL_cells.v]
This checks canonical normalized models first and records an independent coupon PASS/FAIL for each present actual imported type. Imported failures are recorded without preventing normalized coupon generation. library_model_pdk.v replaces only these two named cell models; all other imported cells are unchanged and unqualified by this coupon.
For Yosys formal prep: read_liberty ...; read_verilog -overwrite canonical_ASR_normalized.v; read_verilog -overwrite canonical_DFF_normalized.v; ...
Do not use broad opt/opt_merge in an independent-copy-initial-state proof. Inventory distinct copied FF output state bits, prohibit unexplained unknown cells, and record all init attributes.
