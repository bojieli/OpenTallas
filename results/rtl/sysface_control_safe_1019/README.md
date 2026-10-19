# SYSFACE parent control repair: review packet

The generated `qfd_sys_face_control_safe` parent retains all public pins and event edges while replacing the merged reset/control distribution. It is an explicit diagnostic component candidate. The original parameterized FACE is retained; neither a release clock phase nor an absolute production epoch is selected here.

- RTL: `rtl/qwen_split/generated/qfd_sys_face_control_safe_cold_1019.sv`.
- Deterministic generator and independent proof tools: `tools/qwen_split/sysface_control_safe/`.
- Model and actual native-buffer Liberty cell evidence: `results/arch/sysface_control_safe_1019/`.
- Exact cold parameters: MU/OVL/SRAM_CAL/CTX_ACCEPTED/COLD_PREFIX = 1, OVL_AW = 12, COLD_START_OFS = 2000, OVL_FIRST_OFS = 20000. The latter two are diagnostic fixture constants. Only the three ROM image parameters remain configurable on this generated master; unsupported scheduling parameters are absent. The generator independently whitelists both diagnostic profiles and rejects changed source hashes.
- Original-to-emitted macro instance names are in `cold/receipt.json` under `macro_bindings`; retain these actual generated names in the nine-macro placement. The graph still contains exactly three ROMs and six native 64x16 SRAMs.

The exact cold graph starts with 3,653 FF bits. The repair copies 34 registered sources on the same edge and replaces three old reset FFs with a 98-FF forest: 3,782 FF bits, a net addition of 129. The original three-edge reset release and asynchronous assertion are preserved. Originally synchronous resets remain synchronous, unreset payloads remain unreset, and reset/enable priority is unchanged. The candidate adds 190 real BUFx2_ASAP7_75t_R cells, with 13.851 um2 Liberty cell area. Total mapped area remains a physical sizing obligation.

Proof has three independent parts. `check_graph.py` establishes sequential correspondence for every original equation, all copied D/clock/reset/enable connections, and the three-level reset forest. `check_emitted.py` exhausts each of 9,295 emitted Boolean equations, then checks the re-read and synthesized source's 3,782 actual FF kinds and D/C/R/E/Q bindings, nine complete macro bindings, 190 real native-buffer bindings, and 2,788 public pin bits. `audit_mapped.py` recursively expands all kept paramods in the actual Yosys snapshot: maximum 24 non-clock pin loads, no undriven or multiply-driven signals, and no over-32 net. This snapshot is pre-ABC generic mapping; native standard-cell timing and slew are not established by it.

Verilator 5.050 real-parent evidence:

| Vehicle | Result |
| --- | --- |
| Full legacy MU/SRAM parent | 1,512 exact events; 1,024 PW + 8 DW; four head contexts; row 64 + scale; all 62 public outputs equal over 250,839 samples |
| Enabled AW12 cold parent | Two AUTH/program/witness/context/INIT/row rounds separated by abort and re-admission; all 62 outputs equal over 4,807 samples |
| Reset phase sweep | 128 asynchronous assertions at varied phases; exact three-edge release; 4,149 public-output samples |
| Structural proof guards | Ten corrupt graph/profile cases rejected |
| Emitted-source proof guards | Wrong Boolean operator, copied D pin, reset/enable kind, and macro master rejected |
| Mechanism mutants | Corrupt copied D, shortened reset release, and inverted native-buffer input all fail with committed witnesses |

The first copied-D mutant was invisible to the public-only cold trace. That insensitive run is preserved as `cold/copy_d_public_only_insensitive.log`. The final miter additionally checks every actual copied FF against its original cohort on each sample; the mutant then fails at the copied FF while the corrected parent passes. This is a copy-mechanism witness, not a claim that the cold fixture exercises every downstream use of that control.

Compressed JSON files are immutable full graphs, not summaries. Run `python3 tools/qwen_split/sysface_control_safe/verify_packet.py` from a fleet source copy to verify source hashes, emitted RTL, and all graph evidence. Reproduce the complete build/test matrix with `bash tools/qwen_split/sysface_control_safe/run_all.sh` through unpinned `ot-run` in an isolated fleet copy. The standalone waveform tests remain component fixtures, not SU/MU token qualification.

Safe-design checklist before any gate:

1. Pins/reset: control transformation preserves every existing pin edge; the parent still owes actual boundary pin-register/reset-landing audit and compiler accounting for the inherited internal reset release of three edges plus any external landing stages.
2. Reach: HOLD for the actual nine-macro floorplan and all <=405 um paths.
3. Fanout: PASS in the emitted graph and re-synthesized generic snapshot, maximum 24 actual non-clock pin loads; native post-map/post-route proof remains required.
4. Depth: unchanged original logic with real buffer-tree stages added; HOLD for native depth/setup/hold and slew/load proof.
5. Storage: PASS for this repair: existing three ROMs/six SRAMs retained, no new indexed arrays or delay chains.
6. Floorplan: HOLD for measured native standard-cell area, legal macro lattice/channels/pin access, full-width 40–60% cell band, and ROOT visual review.
7. Clock: existing root retained, 3,791 clock pins including nine macros; HOLD for TT/FF <=80 ps spread, actual parent compensation and hold budget.
8. Schedule: zero added data/event edges; inherited reset release remains three. Final compiler reset/admission and absolute production phase are OPEN.

No REVIEW.json, gate, submission, native timing PASS, or release adoption is produced by this packet. No shared flow/tool files were edited. The native buffer's actual source Liberty path and hash are recorded; final physical PG, signal slew/load, native timing and routed clock/reset census remain mandatory before admission.
