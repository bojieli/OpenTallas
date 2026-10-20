# Genuine raw-qnorm programme model, static dates only

ROOT chose existing VP→VS QB9→VQ(AQ_XMEM2)→actual DL4 up→RSTOP own assembly→XSg0.
The model emits320 target5 CTL payloads containing only the genuine original
1280 FP32 q_norm.scale values, followed by20 actual target0 QB8 commands.
No quantized value drives g_d. Quantized532-bit beats are separate scoreboard
records, generated independently by hc_gate.g_quant/aq_expect and checked
against original hdc_golden_v41.quant_fp8:1280 codes and40 exponents agree.

Scratch608..927 reserves40960 existing VP SRAM bits. It is disjoint from every
head-local projection address in leaf2, odd coefficient rows17..47 and QR
output544..559. Each320 row has an explicit write-commit/read/release interval.
Other existing SW scratch600+ overlaps; no whole-layer or MU free-lifetime
claim is made. That overlap remains a required reuse/context proof.

Dates use XR CTL pin sampling as0 after all resets are ready. The actual XR
input/decode/output adds2 edges; DL4 plus VP pin sample adds5; the SRAM write
adds1. Writes at0..319 therefore commit8..327. QB commands at320+46b reach
VP pins327+46b. The source model includes VS accept/read/return/u registers,
VQ pin/assembly, AQ18-stage valid convention, VQ run/header state, four real
XQ fragments, DL4 up, RSTOP pin/assembly and XS pin/SRAM writes.

The46-edge cadence follows two distinct resource constraints: mode must
remain unchanged through the fourth fragment, and the next second-block AQ
result cannot arrive while the preceding40-cycle VQ run remains live. VS's
19-edge command bound alone is insufficient. In the model, final XS source
commit is1260 relative to the first raw-state CTL. This is a new source cost
and must be composed against the unchanged original deadline; no prefix is
free. It is a static register model to measure and refine, not a native
selected phase or RTL timing receipt. Conditional logical dates are distinct
from currently NULL actual regional-reset/clock dates.

Unpinned model job3706716 on ot-epyc4 exited0 (8GB/one thread admission).
Next admitted component must drive the real XR/glue/VP/VS/VQ/RSTOP/XS source,
compare produced codes/scales and all timestamps with this model, and reject
wrong owner/index, missing/corrupt data, mode overwrite, clock/reset slips and
live memory reuse. No frame/CAP success can be credited before that join.
