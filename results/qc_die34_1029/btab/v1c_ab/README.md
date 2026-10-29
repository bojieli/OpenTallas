# DIE-QC-36 KITS BTAB QC-014: (A) east pin-column re-place and (B) E-strip M5 keep-off + M3 corridor reserve, both from V1c

COORD rulings [DIE-QC-35 KITS update] 13:14 (2) + DIE-QC-36 relay: build (A) and (B) IN PARALLEL (12.17(3)), both from V1c
(best DB: DRC 6, slew TT 11 / FF 2, FF hold +6.59, pair 38.1/35.7), each with a planned repeater fix for the long TT slew
nets; win = DRC 0 + routed LEC EQUIVALENT + FF hold >= 0 + insertion in band (+ rest of signoff.json).

## Reference V1d (DIE-QC-35, collected 13:42 PDT by DIE-QC-36 KITS) [CHECKED intel1 KIT/signoff/signoff.json]
NOT SIGNED: TT setup +280.86 | FF hold +4.66 (sdc -20.33 IO overlay) | pair TT/FF 42.2/38.3 | TT pin-flop insertion
246.51-273.86 (mean 261.15), FF 195.22-221.66 | DRC 16 | slew TT 12 / FF 2 | antenna 0, PG 0 open, sdc_lint/face_guard PASS.
Routed LEC: NOT RUN - the chained intel2 ~/dqc35k2/btab_lec_chain.sh (pid 2552901, DIE-QC-35) is stuck in its
"! pgrep -f signoff.py run --run-dir ..." wait (the pgrep pattern matches the waiting ssh/bash command line itself);
not killed (not mine). V1d does not beat V1c -> no LEC needed for the verdict.

## Measured facts used by the estimates (probes on V1c 6_final.odb / route.guide, CHECKED)
- g_btb[1]/[3] E face x 254.664; kit strip keep-offs: M4+V4 obstruction 252.964-254.592 (inside the macro), placement
  blockage 254.664-261.738 (E pin-column strip). M5 over the macro is free except the PG stripe 252.564-252.876.
- DRC nets are S-band tw-data starts (ptw_data[924]/[931] QN at x 227-229, y 6.8 -> INVx1 at y 71-73 in the mid
  channel): they cross g_btb[1] N-S; GRT gave them M3 guides in the E corridor; DRT ran them on M5 over the macro inside
  the E strip and dropped V45 + M4 east across the macro M4 OBS to reach the corridor (= the 6/16 markers).
- dbWirePathItr probe: in V1c the ONLY nets with M5/V4 shapes inside the E strips are the 2 DRC nets (_1154_,
  g_btb[0].m_wa[8]); 0 of the 410 frozen clock nets.
- E corridor demand: 1,498 nets have a guide in x 254.664-261.738 over the macro y-spans, 809 of them on M3 (V1d 838).
- Long-net slew: V1c routed TT slew >= 240 ps (75 % of 320) on 140 pins (V1c sign-off session + set_max_transition 240),
  + 6 extra V1d TT violators = planned_rep_pins.txt -> 117 nets; dry run on V1c: 116 get a BUFx6f, 1 skipped (no free
  point), planned_rep_dry_v1c.txt.

## Estimates before build
**(B)** removes the DRC by construction: the dive needs an M5 wire inside the E strip (V4 and M4 there are already
obstructed and the macro M4 OBS covers the body); with an M5 obstruction over the same strip no layer M4/V4/M5 is open
inside it, so DRT has no way in. The capacity cost is the 2 DRC nets only (0 clock, 0 other nets used that M5), so no
new congestion; the M3 region adjustment 0.30 over the 7.07-um corridor (~49 M3 tracks) keeps ~15 tracks free of GRT
demand for DRT to re-route those detours legally (GRT may spill ~0.3 x 809 guide-nets east of 261.74, where M3 is open
over the std-cell area; V1d GRT had 0 overflow). Risk: GRT overflow in the S-corner gcells (the V1b class) - judged at
GRT. Clock unchanged (V1c wires FIXED) -> insertion/pairs = V1c within coupling noise (V1d moved max 269.73 -> 273.86
with the same tree, so insertion in band is NOT guaranteed by B). Hold: same FF-only routed-RC ECO margin 10 as V1d (V1d
+4.66). Slew: 116 BUFx6f (6x the x1 drive) split each listed net at its first free L-path point, cutting both driver R and
the driven length; no new hold (data-only, setup +280 headroom).
**(A)** frees corridor capacity instead of blocking: GPL sees a hard blockage over x 261.738-264.330 (48 sites, ~18 M3
tracks) on both macro y-spans, so the E column cells (V1c: 716 DFF + 712 BUFx2 + ~330 AO22/AO221 + 1,161 INV in x 261.7-268)
spread east; the blockage is removed before DPL so DPL / plan CTS / FIRM tree cells are untouched. M1/M2 pin access next
to the corridor drops, M3 supply for the N-S detours rises ~1.4x; the dive then has a legal corridor path. Clock tree is
re-built by the same plan CTS on a slightly shifted E column -> insertion re-measured (risk +-few ps). Slew: same planned
list, inserted before GRT (synth-named nets survive the re-place; re-named placeNNNN/wireNNNN pins are reported MISS).
Hold: kit two-mode GRT hold repair (V1c +6.59).

## Builds (intel1, kits /srv/opentallas-scratch2/claude/die-qc-36-kits/kits/)
| variant | kit | restart | unit | client log (intel2) |
|---|---|---|---|---|
| (B) | qfd_dv_s8x_btab_f3bv1c_b | V1c 5_2_route.odb as 4_cts.odb (sha 8302ccff), V1d run form | oth-ubuntu-294551-1793306489 | ~/dqc36k/btab_b.otrun.log |
| (A) | qfd_dv_s8x_btab_f3bv1c_a | V1c kit cut back to 3_2_place_iop (GPL re-run) | oth-ubuntu-294553-1793306489 | ~/dqc36k/btab_a.otrun.log |
Launched 13:41 PDT. Files: a/, b/, planned_rep.tcl (shared by both), planned_rep_pins.txt.
