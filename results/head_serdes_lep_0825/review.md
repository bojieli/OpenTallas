# SerDes quarter-count plus kept apply replicas: trial placement

Viewed `/home/ubuntu/OpenTallas/results/head_serdes_codex_1028/dchn_plan.png`
on 2026-10-29 during the Codex takeover. The candidate preserves the reviewed
216 x 194.4 um outline, W input band, N corrected-frame output band, S status
band, and centre clock/reset entries. It contains no SRAM macro walls or
channels. Centre-to-corner reach is 145.3 um, and the widest N pin band retains
0.288 um pitch. The source change adds seven kept apply copies and selects
the previously proved quarter-count datapath, with zero extra cycles.

Verdict: PASS-COND for ONE trial placement after the inherited strict LEC is
EQUIVALENT. Review actual placement, reach, clock distribution, and PG before
any subsequent CTS or route. Detailed route remains held on the HEAD flow
release. This review makes no timing or sign-off claim.

Inherited source kit: intel2
`/srv/opentallas-scratch2/claude/head-kits-7/serdes_qk/kits/ot_s81_kp4_dchn_head`.
The continuation waits on the existing LEC container rather than restarting
it. It copies the terminal kit to its own run directory and reuses its exact
synthesized netlist and gates. The placement wrapper refuses any verdict
other than EQUIVALENT and compares the copied netlist bytes before building.
