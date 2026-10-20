Actual s6c copy-state relation, 2026-10-20 takeover; source 8a3f5328c.
qkd_kvs_grp_s6c: 230 copied-output equalities, 957 sequential primitive instances, SAT PASS.
qkd_kvs_grp_h_s6c (host variant): 239 equalities, 970 sequential primitive instances, SAT PASS.
No initialization attributes or state initialization assumptions: retained FF states start arbitrary and independent.
Reset asserted 12 SAT steps (6 ck, 3 hck cycles), release for 20; equality checked t12..32.
No opt_merge, no ignored unknown cells. Canonical ASR/HQN binary semantics from the existing pinned coupon.
Shared arbitrary SRAM output per instance/time retains correlation of copies reading one port.
Consequently this proves finite copy convergence, not SRAM first-read validity, pointer admission dominance,
full RTL/reference equivalence, indefinite induction, physical closure, or protocol-reset qualification.
Original randomized canonical production benches remain separate b1/b2 evidence.
Actual primitive D-inversion controls: u39392_c1 and u36532_c1 cause SAT proof failure as expected.
Initial v1 opposite-property controls are diagnostic only; their logs remain remote.
Exact primitive/pin correspondence PASS 41694 / 41051 copies, conditional on corresponding states equal.
Initial certificate parser failed because leading timescale hid selected top; fixed stripping timescale
and asserting selected top exists. Original failure log and helper preserved; no semantic comparison relaxed.
Full pre-lowering JSON states and generated formal SV retained on ep7:
/srv/opentallas-scratch/claude/codex-kv-grp6-cold-1020/{out,causal}.
