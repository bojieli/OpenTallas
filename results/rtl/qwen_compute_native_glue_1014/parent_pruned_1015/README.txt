Actual candidate-only combinational keep cleanup, based on85b373696; measured source commit899bc79954f3af15bc3e5908faf81c474ecc0008. Original85 live/terminal physical snapshot untouched. Isolated worktree q-compute-parent-prune-1015; no shared/CLOSED RTL/view edits.

Four private combinational helper copies retain original equations/widths/prefix carry order and remove two internal keep attributes;25 candidate instantiation lines switch to those copies. Inverse helper renaming recovers original candidate part BYTE EXACT. All sequential always blocks, bank assignments,58 banks,11 reset masters,14 CLOSED children,84 clock roots and compiler ages/latency unchanged.

Actual Yosys proc/flatten/opt/techmap/opt result943 residual FFs versus2278 before; reduction1335=58.604%. Both structural useful-output graphs contain937 FFs. Remaining six deliberate keeps are five rom_ce/rq_ce aliases and one local rst_l copy. Genuine KV storage710 pre-ABC bitmapped FF bits(before) to zero(after), while24 useful cur FFs carrying KV wire aliases remain. Wide generic4952 Q-width sum is not a mapped physical count. Bitmapped JSON gzip/SHA, exact Yosys flow/log, source/mask hashes and before/after graphs included.

Source-exact functional results using actual leaf RTL/full old-parent reference:
M0 PASS3499 complete-word checks,264 tile outputs,438 node outputs,264 nonzero outputs.
M1 expected FAIL complete word at cycle134; M2 cycle134; M3 cycle535.
Boot16 PASS3559 checks,264 tile outputs,445 node outputs.
All banks PASS5959 checks,448 tile outputs,745 node outputs,448 nonzero; real bank reads64/120/96/104/64.
Actual bitmapped native pin dependency audit PASS31504 pairs:10788 direct,20716 combinational,zero unmatched.

Every heavy job used ot-run admission; successful host/unit/exit captured in jobs.json and logs. Inputs SHA checked at job start; deterministic seed198 ROM masks match the old oracle. One initial dependency attempt selected EPYC4 without the AGI-only measured artifact and exited2; preserved separately in attempt_history/initial log. Retry qualified hosts using the actual measure directory and passed31504 pairs. No failed result overwritten.

verify_parent_prune_receipt.py checks current source/mask hashes, fresh numerical builds/coverage/negatives, measured943 FF, matched31504 pairs and successful job exits. Candidate physical spec requires this receipt instead of the old source-hash receipt44. Physical qualification remains OPEN: FF reduction and functional proof do not establish parent CTS, actual RNE/OR/rounding/fanout delay, native boundary timing, route DRC, production20um channels/PG or IR. The original dense-channel physical attempt remains HELD; no automatic adoption, invented residual macro or instruction semantic change.

Same pinned native libraries/config/image synthesis-only comparison (unit oth-ubuntu-2033563-1792063048, EPYC4, rc0): original Yosys mapped-stat2308 DFF/35919 cells/196822.943160 area; candidate972 DFF/10057 cells/194264.634300 area. Crucially, BOTH actual1_synth.odb handoffs have954 DFF (75 reset+879 plain). Handoff instance counts11232 original vs9958 candidate. Source1335 FF reduction is pre-ABC only; actual residual clock sink reduction ZERO. No physical58.6% clock/area saving claim. Original85 preGPL954 is consistent, but these matching handoff-stage databases provide the direct comparison. No candidate placement/CTS/route was run. Comparison receipts, exact script, logs, hash-bound ODB paths and both synth_stats in native_synthesis/.
