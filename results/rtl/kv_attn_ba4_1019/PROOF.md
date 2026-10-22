# Source and simulation proof

Opt-in source selection is new ba4 module/kit only; ba3 and all closed source modules remain byte-identical. RTL TX payload captures unconditionally on the same edge. All control, validity, fault and STATUS equations remain unchanged.

Real downstream contract: rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv wsel/wobs selects compiled fire slots; split_20261014/ot_qwen_static_slot_link.sv captures observed-valid into cmd_ov and aborts on cmd_wv&&!cmd_ov before v3 PHY transmit. crc_bad/slot_bad inspect only expected present frames. No idle payload semantic dependence.

Verilator5.050 codec positive8800 checks,1602 accepted/598 rejected PASS. Fault-delay mutant4 fails598 comparisons; wrong-data mutant7 fails390; wrong-valid mutant8 fails160. Full programme/root/face production-shape pair comparison PASS133220 checks over64 cases:16 legal/fault modes for four distinct epochs/tokens/512-word data vectors. Each legal operation requests32Q and transmits32RESULT+STATUS; existing exact output edges remain +1 relative legacy launch. This is component context coverage, not a full multi-user token simulation or attention arithmetic throughput qualification.

Remote immutable source archive was staged under /srv/opentallas-scratch/claude/codex-attn-ba4 before builds. Codecunit76513 on epyc6 and pairunit1672533 on epyc5. Codec matrix outer wrapper initially incorrectly inspected empty stdout on expected simulation aborts; actual sim.log witnesses above contain real intended FAIL. No RTL change or weaker checks was used to repair the wrapper.
