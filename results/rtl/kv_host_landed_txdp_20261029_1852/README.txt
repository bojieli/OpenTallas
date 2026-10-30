TOK-KV native HOST producer-delay reproduction, 2026-10-29 18:52 PDT.
Base: fee96ecff02059a8cf28e980fd72a9e1bfb58b56 (TOK-KV-4 source fixes).
Executed: intel1 /srv/opentallas-scratch2/claude/codex-kvtok-1847
oth-ubuntu-3190992-1793325119, ot-run mem2 threads1, terminal exit0.
Actual RTL: ot_qwen_d2d_static_end_sfm + native slot controller + CRC + p192 SRAM models.
A real single-event TX calendar emits port1/kind13. Provider boundary is modeled
as 157 registered edges (86 outward + 2 HOST + 67 return + 2 boundary pin flops).
FEG disabled: first-epoch authorization is outside this producer-capture mechanism.
Fixed TXDP1=157: one TX, all 548 payload bits exact, no abort/end_fault/fault_cause.
Negative stale TXDP1=4: actual epoch_abort=1 fault_cause=0x80, same delayed observation.
Negative missing producer observation with TXDP1=157: same abort/0x80, not masked.
No RTL edit or added cycle. No native whole-die, 36-layer token, throughput or physical
PASS claim. Inherited full v3 probe still running; component does not replace it.
The run used main's identical mechanism files; committed source hashes bind the rerun.
