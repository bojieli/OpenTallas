# S81-LP-1 (2026-10-29): LP partition split estimate + count_align_bind fail-closed + clock-src links

## (1) LP partition > 400k cap: split along the coll-lane (u_u_ln0..3) boundary  — ESTIMATE (12.14b), no build

s_0S_LP (dsdv_slice_lepw_mus_LP__t2, 1442.88 x 1226.88 um) flat census = 556,766 std / 265 SRAM (Codex, CHECKED).
Own probes on the exact same census closure (intel1:/srv/opentallas-scratch2/claude/s81-lp-1-1029/{hier,hiermap,flat_lanebb}):

| cut | parent std | headroom to 400k | verdict |
|---|---|---|---|
| A: 4x lnland u_u_lnl* (Codex) | 398,106 | 1,894 | FAIL (clock leaves alone > margin) |
| **B: 4x coll lane u_u_ln* (DEFAULT)** | **322,070 CHECKED** (flat, lanes = exact-port blackbox) | 77,930 | PASS; +5..10 % P&R growth -> 338-354k (UNCHECKED) |
| C: lanes + lnland | ~163,410 (UNCHECKED arithmetic) | — | fallback only if B's placed parent > ~360k |

Lane child dsfd_coll_lane_w_safe8_ntf CORE_CRED12: 83,003 std / 19,830 FF / 55 SRAM (hierarchical mapped, CHECKED),
2143 pins, one clock ck (= LP clk), one reset rs. Same RTL as main (ot_s81ph_coll_lane_safe4.sv unchanged since
a19178766, byte-identical to the census snapshot). No RTL logic/cycle change; partition plan pins unchanged.
Old hard tile dscoll_lane_w_s12h (725.76 x 583.2, 17 % fill, 818 ps TT insertion) is NOT reusable: 4 do not fit the
partition (2 x 725.76 > 1442.88) and insertion breaks the 250 TT common core latency. New compact lane kit needed:
area 62,002 SRAM + 11,927 std um2 -> ~165k um2 outline at ~45 % (UNCHECKED; derive from the parent slot).
Details: lp_split_estimate.json. Probe scripts: hstat2.py (recursive per-instance mapped counts), area.py (SRAM area).

## (2) count_align_bind KeyError src_part recurrence
Root cause (CHECKED, = DIE-S81-22 02:48): go16 ran a stale tool snapshot (wt/die-s81-18 @9e0f2cfb03, before RM273
merged 46cae83a4); main already had the src/dst fallback. Hardening commit on this branch: ocv_parts() raises a named
BindError for a row with no partition identity (was bare KeyError) and for corner rows disagreeing on a port's
partition pair (was silent last-row-wins). +1 test; the main tool fails it (mutant check); 87 count_align tests pass.

## (3) global_clock_src links
epyc2 codex-s81-2340/global_clock_src, codex-clock-takeover-1029/{src,src02,src03}, die-s81-21/geomdiag: absolute
links into another lane's dir replaced by RELATIVE links into a per-dir hardlink copy src_9e0f2cfb03/ (same inodes as
die-s81-22/src_9e0f2cfb03; atomic mv -T swaps; json inputs hardlinked). 70/70 plan physical refs resolve, 0 broken
links (CHECKED). Left untouched: die-s81-23/g03route (live job of DIE-S81-23; its links still valid).
