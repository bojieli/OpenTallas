# S81 chained-frame landing calendar: root cause of the fc30 u_f_3L03 fault and the fc31 correction

S81-P9-FC, 2026-10-23.

## Fault

The fault is on fc30 (cap30-framecal, die 3b4b975d) in the idle cut_3S_ctl MON3S run:

- frame u_f_3L03 sets ret[69] at cycle 141;
- u_s_3S captures a lane status fault at cycle 154;
- block_fault[4] is sticky from cycle 155.

## Root cause

The calendar-v2 tool (`tools/s81_dv/frame_chain_reset_v2.py` @c1b0a11d1/babd78b21) and TOKc's `frame_chain_calendar.py` both used the same rule, R0(chained) >= G_up. They started each chained frame lane at the upstream frame's hop-0 gate G_up.

That is not the clock the chained frame actually sees. A chained frame lane (xx03 / xx13) is clocked by the upstream frame's `xok[k]`, which is `u_xo<k>` ck_o, which is the upstream frame's landed xk[k]. That clock arrives only after:

1. the upstream lane's last-hop flight. Every upstream xx02 / xx12 frame lands at K 5, so F = 4 periods.
2. the chained hop's own parity and flight (F 1).

The model therefore dropped about 4 to 5 periods. In every one of the 9 retimed frames, the first forwarded edge reaches the K-2 ring 6.0 to 6.5 T after the ring's release. Ring epochs fault when dt >= K + 1.

The calendar-v2 probe (`probe2`) passed for two reasons: it had no flights, and it tied every landing to K 2.

The fault was not specific to 3L03:

- **The other retimed frames fail in the same way.** 4R03, 0L03, 7R03 and 0R13 fail just as 3L03 does. Their status is simply not among the fault outputs of the idle cuts, which is why they looked clean.
- **u_f_1L13 also fails.** Calendar-v2 never retimed it. Its dt is 3.0 to 3.5 with K 2.

Earlier explanations were checked and are not the cause:

- The FRH10 / FRRST landings of the rf3r variant are already in the +4 release (pad 2 + rsync 2).
- The u_xo relay reset (`rst_n__xk`) is data-only.

## Model

The model is `frame_chain_reset_v2.inspect` (v2 calendar), exact to the half cycle on common-phase roots:

- **Hop-0 gate start:** G = enable depth + 1.
- **Lane start at the landing:** A = G + 0.5 x (number of inverting dsfd_dvrlyh stations mod 2) + F.
  - F comes from the GEN land plan at each corner, using dv_slice_cut's rule: clamp(ceil(-S1/T), K-D+1, K-1), or K-1 for a lane with no S1 row.
- **Chained gate:** clocked by the upstream frame's arrival A_up. The first xok rise after its enable passes the gate.
- **Ring release:** Rrel = rst_n depth + 4.
- **Window:**
  - late, at tt and ff: dt = A - Rrel < K + 1;
  - early: dt > 0 at tt;
  - EARLY_WARN (reported, not a verdict): G < Rrel, or a coincident first edge at ff.
- **Delay:** the smallest whole delay that meets the late bound. The tool refuses if that delay would put the release after G (LANDING-CONTRACT L3).

Validation: the model matches the edge-exact real-cell probe on all 24 chained frames in the four fc30 cuts. It reproduces dt for the faulting frames and for the clean ones.

## Correction (fc31)

The tool was run on the original cap30 bind (64d4be888, the same input as fc30). Delays in reset stations:

| frame | fc31 total | over fc30 |
|---|---|---|
| 0L03 | +7 | +4 |
| 0R13 | +5 | +4 |
| 1L13 | +1 | +1 (new) |
| 2L13 | +7 | +4 |
| 2R03 | +7 | +4 |
| 3L03 | +7 | +4 |
| 4R03 | +7 | +4 |
| 5R13 | +5 | +4 |
| 6R13 | +6 | +4 |
| 7R03 | +7 | +4 |

- **Stations:** 59 one-bit reset stations in total (fc30 had 22). They use the same placement and LEF-rectangle rules. The longest new load hop is 115.9 um.
- **Die:** 35ba1ef7023140d0… The full die and the overlay metadata are at ot-gold2:/srv/opentallas-scratch/claude/s81-p9-fc-1023/fc31.
- **Unchanged:** ICGs, return lanes, data ports and frame RTL are byte-identical. The restoration assertion holds.
- **Read epochs:** each changed frame's read epoch moves by its delay. There is no new datapath stage.
- **Calendar after the fix:** dt at tt is 2.0 to 2.5 and at ff 1.0 to 2.5 (K 2). G - Rrel is 0.5 to 1.0.

## Evidence (this directory)

- **Calendar checks:** `calendar_{cap30_original,fc30,fc31,fc30_cut_3S_ctl,fc31_cut_3S_ctl}.{txt,json}`.
  - Before the fix (cap30 original and fc30): 10 window failures out of 72 frames.
  - fc31: 0 failures. fc31_cut_3S_ctl: 0 failures.
- **`frame_chain_reset_v2.json`:** the tool receipt. It holds per-lane dt, F and gate slack before and after the fix, the station placement, and the land-plan SHA.
- **`probe/`:** real-cell edge-exact vehicle from `frame_chain_reset_probe.py`, covering the 10 changed frames, their 10 upstream frames and 80 lanes with flights:
  - PASS at tt and at ff;
  - mutants `+MUT=k` (the reset k stations short; k = 4 is exactly fc30 on the 9 calendar-v2 frames, k = delay is the uncorrected die): k = 1, 2, 3, 4, 5, 7 are all CAUGHT as a real landing epoch fault at tt and ff.
- **`cut_3S_ctl/patch_cut.py`:** carries the die delta (station lines copied byte-exact from the fc31 die) into the fc30 cut_3S_ctl. It produces slice_top a240fb53. The MON3S idle rerun result is recorded below.

## fc31 cut_3S_ctl idle rerun (recorded by S81-P10, 2026-10-24)

Binary: S81-P9-FC `out_monfc31/obj` (verilated from K_monfc31: slice_top a240fb53 + the fc30 cut tb with MON3S/MONFC
monitor lines only added, tb sha 359ee4b7), recovered to intel2:~/ot-scratch/s81/recovered/s81-p9-fc-1023.

| run | cycles | fault_cycles | first_fault | u_s_3S fault3S / f_* events |
|---|---|---|---|---|
| fc30 cut_3S_ctl idle (STW-S81d-TOK, die 3b4b975d) | 2000 | 1844 | 155 | block_fault[4] sticky from 155 |
| fc31 idle 400 (S81-P9-FC 10-24 00:24, out_monfc31/idle) | 400 | 0 | -1 | none |
| fc31 idle 600 + trace (S81-P10, intel2:/srv/opentallas-scratch2/claude/s81/entry_fc31/idle) | 600 | 0 | -1 | none |

The u_f_3L03 lane status fault is gone on fc31 (the bench's own "FAIL zero checks" is the idle-run convention: nothing
is compared). Native entry replay on this binary (S81-P10, held-payload f_ks model a1f22086cc, KS 2297 probe-confirmed):
jobs 15/16/17/20/21/22 PASS (fault_cycles 0, line W/E bit-exact, check PASS), mutant corrupt:hf_7N_l0:33 CAUGHT,
PASS_CUT_COMPONENT -- intel2:/srv/opentallas-scratch2/claude/s81/entry_fc31/out (+ out_probe; legacy-pulse control
pulse15 reproduces the fc30 eks_7N TORN miss with fault_cycles 0). Same verdict on the plain fc31 build: main 0e75647078.

## Not fixed: EARLY_WARN (report only)

14 GEN-original chained frames have a first forwarded edge only 1.0 T after release at tt and G - Rrel = -0.5. At ff (F 0 lanes) that edge is coincident with the release: 0L13 0R03 1L03 2L03 2R13 3L13 4R13 5L03 5L13 5R03 6R03 7L03 7L13 7R13.

These frames are fine in every tt simulation. Their early side, however, sits outside the margin that the GEN gives every direct frame (G - Rrel in {0, 1}).
