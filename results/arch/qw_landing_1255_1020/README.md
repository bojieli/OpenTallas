# Actual Qwen g5 receiver-face landing source candidate

The g5 generator intentionally defers slice2-to-slice2 links in
`OT_SPLIT_LAND_LIST_IN_FACE`. The actual regional verdict retains 182 functional
slice links / 50,267 bits, plus three external static strap bits (185 / 50,270
in the raw owed report). These are NOT repaired by G5F2's observation fault tree.
The committed model classifies every raw owed detail row and keeps every row
unbound/unadopted. The separate eight no-root rows remain another prerequisite.

Representative actual bus `n_dv_st_E1_st_u_st`: `dvs_E1/st_wo` (source clock
`n_clk_r96`, reset `n_rst_field__t7222`) -> `dvs_E2/st_ei` (receiver clock
`n_clk_r122`, reset `n_rst_field__t7656`). New `qfd_dv_slice2_e_stland` intercepts
this complete 1088-bit input INSIDE the receiver-parent RTL. It instantiates
`qfd_slice_st_face_land`: six existing D8 SRAM ring slices, five 192-bit and one
128-bit. No ready/credits/backpressure. Unreset data lives in 17 real 32x64 dual
clock SRAM macros (34,816 allocated bits, 8,704 live ring payload bits); valid,
epoch, pointers and output masking retain the existing ring protocol.

Exact TT arrival differences at the actual named ck pins: 8718.722656 -
8788.809570 = -70.086914 ps; FF early: 7037.440918 - 6981.118164 = +56.322754 ps.
The model reserves 100 ps margin plus 80 ps for EACH endpoint region (160 total).
The existing D8 SRAM aperture is [1.25 T,4.125 T], T=833.333 ps. L=5 makes macro
age `(L-3)T+phi`, safely inside that aperture throughout the reserved interval.
Price is +5 receiver edges / +4166.665 ps per traversal against the direct wire,
136 bytes/cycle sustained. Every dependent status/scalar/calendar age still
needs recompilation before bind. K=(L+G-R0-2) mod16 and is captured in a new
4-bit boot register only while receiver reset is asserted (>=2 receiver edges).
The six slices consume the same stored offset. Released configuration changes
must not alter the calendar. Exact G/R0 reset-release receipts are still owed.

The forwarded-lane drift maxima 1536.3/2568.9 ps describe a DIFFERENT scope;
they are recorded by the model and are never substituted for this pair's signed
clock phase. Whole-die phase bounds cannot qualify a per-pair D8 ring blindly.

Macro LEF area: 17 *31.992*17.304 um². Control/boot/register area, face placement,
reach, full native mapped census, standard LEC, actual SRAM hold/setup and
parent functional/calendar integration are NOT measured. No gate/route launched,
no existing view replaced, no broad die rerun or qualification claimed.

The minimal full-width mechanism bench uses actual TT/FF phases scaled to its
10 ns behavioural clock, four reset scenarios and offsets 3/6/11/14; all 1088
bits change. It flips the external K input after reset release to prove the boot
latch is effective. Read-selector mutation is the causal negative. It runs only
on the fleet with Verilator5.050. Logs and exact source hashes follow terminal
results. Early harness failures are retained remotely and are not design fails.

Final exact-source fleet unit39814-1792526330 TERMINAL0. Positive PASS1618/0 errors;
wrong read selector FAIL2935/1618 checks, as required. This validates the new
full-width shim and boot-offset hold under four minimal cases, not the full
receiver parent/calendar or die. Final SHA receipt matches committed default
shim and bench script. Early harness failures remain remote under positive,
positive2, positive3 and their build logs; no evidence overwritten.

## Coherent ten-bus receiver cohort successor

`qfd_dv_slice2_e_eiland` now intercepts every actual input from dvs_E1 to dvs_E2,
not only st_ei: cmd_ei116, hr_ei453, st_ei1088, sc_ei48, rv_ei1, re_ei1,
rr_ei3, rl_ei1, rd_ei512, dr_ei520 = 2743 bits. This matters because lpc captures
the status, scalar, command, HR and return tuple on the same receiver edge.
The st-only candidate above remains a scoped mechanism witness, unsuitable for
cohort adoption by itself.

The complete cohort source uses `qfd_slice_ei_face_land`: fifteen SRAM D8
slices (14x192 +55), 43 physical32x64 macros, 88064 allocated bits/21944 payload
ring bits. Each bit from this source root receives the same +5-edge price and
same epoch. Fifteen kept boot-offset copies avoid a shared offset flop driving
all pointer cones. Actual mapped kept-copy census is still required. Other
source-root inputs are unchanged and remain distinct scheduling obligations.
The model lists each of the ten buses and its +5 receiver-edge price. Data rate
is 2743 bits/cycle; area is 43*31.992*17.304 um² macros plus unmeasured control.
No claimed whole-parent latency/rate or replacement of released clock pins.

The successor bench checks full2743bit words (all chunks change), both exact
signed corner phases modulo a period, four reset/restart cases, boot-offset
freeze under an externally changed K, and wrong-read selector mutation.
Default candidate source is unbound; first receiver geometry, native census,
standard equivalence and dependent calendar integration remain required.

Complete2743b cohort exact unit42030-1792526497 TERMINAL0: positive1618checks
0errors PASS; wrongread causal2935errors FAIL as required. All seven source and
dependency SHA checks match this worktree. Logs retained in fleet/cohort_*.
The receiver-parent integration remains a source candidate, not covered by the
isolated ring mechanism witness; no mapped or physical result is inferred.
