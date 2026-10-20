# AHUB6 measured redesign admission, 2026-10-20

The original g4 gates remain active and are not approved. Their source revision is
6feabc28437514b815f6954cbf2351335a50ad77. No gate result is fabricated here.

Read-only clock replay completed on ot-epyc9, unit oth-ubuntu-655021-1792476664,
from g4a 4_1_cts.odb. The copied per-flop TT census proves the late tail:

| Core-clock component | Flops | TT arrival ps |
| --- | ---: | ---: |
| u_rx | 33 | 607.96–800.17 |
| u_ry | 68 | 631.56–841.58 |
| u_core | 2535 | 562.93–594.85 |
| u_io | 386 | 563.03–600.70 |

All 101 late relay flops are missing from the core fence prefix table. The
LP region record explicitly assigns u_rx and u_ry to c. The reciprocal child
flop reference adds 238.7 ps to its 298.47 ps raw pin arrival, giving 537.17 ps.
The remaining core soft mass spans 37.77 ps; fixing fence membership alone
would address the observed clock tail, but does not satisfy native admission.

Native replay on the exact mapped 1_2_yosys.v completed on ot-epyc9 unit
oth-ubuntu-3896271-1792481779 using the original snapshot textbook_lint parser,
collapsing BUF/INV trees and excluding clocks/constants. native_over32.json
contains ALL 265 driver violations, not a thresholded top-eight summary.
Worst: u_io.start 549, u_core.start_b 293, u_io.em_w 292,
u_core.u_rr.rst_n[1] 168, rst_n[4] 128. Most remaining violations are
landing-writer rq roots (CHUNK_BITS=8), with 56 loads per writer chunk.

## Structural successor requirements

1. Include u_rx/u_ry and every LP-record-owned soft child in its regional fence;
   compare fence ownership against measured mapped sequential instances.
2. Split landing chunks from eight to two data bits, regenerate ALL reset-leaf
   counts/slices and valid-vector dimensions; preserve D4/K2 and all edges.
   A writer contains data and epoch/reset consumers, so CHUNK4 is insufficient.
3. Replicate command-start and export enables as kept, uniquely parameterized
   same-edge copies, distributing consumers in groups at most 16 bits to allow
   mapped enable logic. Do not add an unpriced start stage.
4. Replace the five broad core reset roots with same-depth local leaves;
   reset_n[1]/[4] are actual violations, never README waivers.
5. Partition zseen clears and decode consumers, then remeasure ALL mapped
   combinational roots, not only flop drivers. Anonymous roots currently reach67.
6. Run native census BEFORE a layout gate, and prove behavioral PASS plus mutant
   witnesses using Verilator5.050. No successor is admitted until all violations
   are resolved. No new kit gate or route was launched by this evidence packet.

SAFE checklist: pins/reach/depth/storage/schedule inherit g3 only as hypotheses;
fanout FAIL measured265, clock FAIL measured304.4 ps child-inclusive spread,
floorplan ownership FAIL measured101 missing soft flops. Reset fanout FAIL.
A full kit review and current measured evidence remain mandatory.

## Partial source implementation (not admitted)

`tools/qwen_kv_die/ahub6/mk_source.py` generates the opt-in
`qkd_ahub_static_dw_g6_lp` parent. Its thirty landing writer/reader chunks
are two bits. ALL associated valid-vector widths, reset-leaf counts and slices
change together; D4/K2 and the data/command/reset schedule remain unchanged.

The first synthesis-only probe rejected the enlarged aggregate reset-root fanout
at elaboration. The corrected source uses seven uniquely parameterized kept
same-edge root copies, one per region. `rst_n` drives seven D pins. Each root
then drives only that region's forest branch count (core <=32). No depth was
added and no shared helper was relaxed. This correction is an implemented source
change, but command/export enables, core internal resets and combinational roots
still require work. Do not submit this partial candidate or cite it as qualified.

Fleet synth-only probe v2 uses the original source snapshot mounted read-only,
with ONLY the generated parent file overlaid under its old module name for
compatibility with the baseline synthesis config. The top rename is recorded
in the scratch overlay. No live Claude file was modified. Output is ep9
`/srv/opentallas-scratch/codex/kv-ahub6/chunk2_work_v2`. Collect the new mapped
netlist, count every driver, and complete the remaining source fixes before any
gate. Exactness benches and mutant witnesses remain owed on the changed source.

## Control/state structural successor, staged v3 through v9

Private qkd_ahub6_controls.sv is generated from the unchanged g3 safe source.
All new register copies capture on the existing edge. It distributes command,
identity, calendar, export enables, core clears, and same-depth reset leaves.
Z seen/write storage is split into sixteen-bit local components. LM and RZ
capture words are split into eight-bit kept components. Decoder arithmetic is
partitioned into nine semantic groups, with eight same-edge age copies.
No added data/control cycle or timing-constraint relaxation is implemented.

Source inspection found that ot_rst_pipe has two asynchronous-assert/release
synchronizer stages PLUS two plain regional stages. The initial private v4-v6
reset implementation had only the plain stages and is NOT eligible for adoption,
even though its late-command miter passed. v7 restores all four stages. The
stronger test drives commands during reset release and covers T=1/128/513/1024/
4096/8192. It passes 11991 comparisons and rejects both a bad command copy and
a mutant removing the synchronizer stages. This reset correction precedes any
layout gate. The final v9 source additionally passes the ordinary core miter;
full die-calendar exactness is running separately.

Mandatory census tool source94de8573f reads the seven exact std/child Liberty
files extracted from actual Yosys Executing Liberty frontend lines. It uses
Liberty functional BUF/INV transparency and checks every dynamic driver/reset/
macro data contact, without exceptions. v7 remains FAIL42/max133. All broad
reset violations are gone; remaining mapped fanout is in control/arithmetic and
wide capture cones. The133 root was traced to RZ128 capture and67 roots to LM32
capture. v8/v9 partition these actual endpoint groups, rather than relabeling
buffers. Native summaries preserve ALL violations, exact source/Liberty hashes,
and full remote receipt hashes; driver_counts is omitted only to avoid a22MB
inline file. The admission hook itself consumes full receipts.

Measured cost: baseline mapped20527 flops/82607 cells; partial v5 mapped44389
flops/168423 cells. Much of the increase is independent epoch/reset state for
narrow landing chunks. These are intermediate measured counts, not final area
or a closed view. Macro count, payload widths, D4/K2, seven clock regions and all
compiler latency deltas remain inherited. Model cycle delta is0 at this stage.

No source in this packet is approved for a layout gate until native count0,
complete exactness witnesses, reset binding, and a new physical checklist.
