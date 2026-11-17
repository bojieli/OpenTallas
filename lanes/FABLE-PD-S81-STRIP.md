# FABLE-PD-S81-STRIP: strip leaf CTS setup failures (t28 t34 t47 t62 t75), 2026-11-16 20:15 PST

Read-only PD review. Kits: `fable-fix-s81-cong/countable_F2s4tapfix1_eight/gen/ot_s81sl_leaf__<t>` (intel1: t28 t34 t47; epyc7: t62 t75 t72).
Inputs: worker census `an_place/sta/<t>_cts/setup_paths.tsv` (4_1_cts.odb, placement RC, cap x1.45, before the kit TT repair),
kit logs (3_3 GPL, 3_4 resize, tt_setup_measure), plan `s81-b3-clk/ev/B6gF2s4tapfix1.json`, the vpw RTL, and two small STA reads
of mine through ot-run (4_cts.odb, kit RC x1.00, path geometry): intel1 + epyc7 `/srv/opentallas-scratch2/claude/fable-pd-s81-strip/{t47,t75}/run.log`.

## Verdict

Two independent root causes. Form B fixes only the first.

1. **VPW write arbiter (all 75 leaf types).** `ot_s81sl_vpw` is a five-writer priority arbiter: every one of the 256 `wdo_q`,
   18 `wa_q`, 8 `wmw_q` flops sees raw `x_wv / x_wa[0] / x_wm` from the VS core as a kill term. That is 285 endpoints per leaf,
   and the count is exactly 285 on t34, t47 and t75. VS clk->x_wa costs 383 ps inside the core, so 636 ps are left for the wire
   plus 5 logic levels. **Form B is the right structure for this: GO**, with the placement conditions in fix 2.
2. **Global placement diverged on t47, t75 and t8fix.** These kits entered detail placement with about twice the wirelength GPL
   had already reached. Combinational cells sit 250-700 um from their FIRM flops. This, not the VP unit, produces the 15,893 and
   10,091 path counts. Form B does not touch it, and a form B kit placed this way will fail the same way.

## Numbers

### Q3 first: what the x1.45 CTS model hides

| Leaf | Worker read (4_1_cts, x1.45) | Kit TT measure (4_cts after repair, kit RC) | GPL min HPWL | HPWL into detail place | Ratio | Buffers added at 3_4 |
|---|---|---|---|---|---|---|
| t28 | -577 | -312 | 19.44e6 | 19.61e6 | 1.01 | n/r |
| t34 | -758 | -478 | 7.28e6 | 7.64e6 | 1.05 | 19,662 |
| t62 | -548 | -216 | 13.72e6 | 14.11e6 | 1.03 | 40,147 |
| t72 | n/r | -725 | 19.49e6 | 20.24e6 | 1.04 | n/r |
| t47 | -3,956 | -2,642 | 10.98e6 | 25.88e6 | 2.36 | 147,329 |
| t75 | -1,454 | -1,047 | 13.90e6 | 26.59e6 | 1.91 | 127,632 |
| t8fix | n/r | n/r | 19.99e6 | 36.09e6 | 1.81 | n/r |

The model overstates by 265 to 1,314 ps, but no leaf comes near -42. No GRT DB existed at 20:00 (t34 was in GRT extra iterations),
so there is no GRT read of these kits. My own read reproduces the kit numbers (t47 -2,641.5, t75 -1,046.6).

### Q1: top 200 paths by slack, by class (x1.45 census)

| Leaf | Into vpw (VS / driver / leafdn) | hig -> lane pins | VP driver internal | Reset relay hop | Other |
|---|---|---|---|---|---|
| t28 | 104 (37 / 67 / 0) | 85 | 0 | 10 | 1 |
| t34 | 200 (200 / 0 / 0) | 0 | 0 | 0 | 0 |
| t47 | 156 (106 / 0 / 50) | 25 | 0 | 0 | 13 station->port, 4 ring, 2 |
| t62 | 19 (19 / 0 / 0) | 0 | 99 | 47 | 18 VP reset, 17 |
| t75 | 198 (198 / 0 / 0) | 0 | 0 | 0 | 2 VP reset |

vpw decode dominates the worst 200 on four leaves (52-100 %), not on t62 (10 %; `driver_dswp_q` -> `hw_d/lo_d` leads at -548).
Over all failing paths it is a minority: t28 285/926, t34 285/939, t62 259/1,067, t47 285/15,893, t75 285/10,091.
All paths by class: t47 clock-landing ring 10,308, VP driver 2,076, VP other 1,063, hig 641, station->port 459, vpw out 405.
t75 ring 4,947, VP driver 1,901, station->port 1,161, hig 1,082, vpw out 204.

### Q2: is one stage at the vpw input enough?

t34 worst path (x1.45): VS clk at 137 ps, x_wa[0] at 520 ps, capture flop clock at 334 ps (useful skew +197), required 1,156,
arrival 1,914. The 1,394 ps after the pin are 5 gates (about 214 ps) plus 1,541 um of path for 751 um of Manhattan distance,
in three 240 um unbuffered legs of about 130 ps wire each.

- One stage **at the vpw (bank) end**: VS -> XR flop has 636 ps and no logic. At the measured 0.77 ps/um, 751 um costs about 578 ps:
  about +58 ps at x1.45, about +150 at kit RC. The second cycle (XR flop -> 5 gates -> wdo_q, local) has more than 500 ps spare.
- One stage **at the VS output**: the 751 um then sits behind clk->q and in front of the 5 gates, in 548 ps: about -30 to -130. Wrong end for far types.
- These are estimates from one path and need a GRT proof on t34.

Plan census, VS edge to the nearest u_b0/u_b1 edge, 75 leaf types: median 376 um, max 588 (t65). 66 types over 150, 57 over 250,
27 over 405, 9 over 500 (t65 t3 t10 t74 t38 t42 t13 t31 t34). t28 64, t47 156, t62 177, t75 281, t72 294, t43 423, t34 501.
One stage is enough on paper for all 75 only if the XR flops sit at the banks on a late standard tap and the route is straight.
For the 9 types over 500 um the margin is about +60 ps at x1.45: expect t65 near zero.

### Q4: t47

Not the regex alone. In order of weight:

1. GPL divergence (table above). HPWL ran 1.16e7 -> 1.52e7 -> 2.23e7 -> 2.50e7 over iterations 370-400 and GPL stopped at overflow 0.0991
   with 2.58e7. The PLACE-NOCONVERGE gate passed because it only looks for GPL-1010. Movable utilisation is 0.71 %.
2. Clock-landing rings, 10,308 paths. `ring_place=ff` fixes the ring flops and leaves 53,710 ring logic cells to GPL.
   Example at kit RC: `u_cland_ft2_i` sd_c[36] at (166,1260) -> AO22 at (62,593) -> y[36] at (166,1254): 7 um apart, 1,537 um of path,
   13 buffers, -598.6 ps against a 416.5 ps max_delay. Input port ft1_i[218] (19,1278) -> AO21 at (25,568) -> flop (24,1252): -530.5.
   The same rings cause 2 failing paths on t62.
3. vpw in the same state: wdo_q flops spread over x 118..915, y 38..1239 (t34: x 627..671, y 341..351). x_wa[0] -> wdo_q[1][110] is 403 um
   apart with 4,107 um of path, -2,048.8.
4. Station -> port, 459 paths. The -3,956 path is a displaced inverter and output buffer driving 258 fF, not a missing station:
   `u_ft_ft6_o_7` (602,1012) -> port (558,1278) is 310 um, the path runs 2,524 um through (65,448). The plan's max station hop is 365.3 um,
   0 over 405. The ft_polarity_local regex fix (cd9e0a184f, not ce1ca0f7e6 alone) is needed for this class and for nothing else.

### Q5: t75

Same class as t47: GPL divergence (1.39e7 -> 2.65e7 in the last 30 iterations) plus vpw. Ring sd_c[21] (1320,1256) -> AO22 (1207,980) ->
y[21] (1320,1251): -382.3 at kit RC. Worst path: `cst_vsp` flop (684,347) -> wdo_q (508,557), 386 um apart, 2,152 um of path, 27 cells, -1,039.
Milder than t47: port -> sd_c passes at kit RC (+54, +64), where the x1.45 census counted 2,676 failures.

### Q6: who shares the structure

- vpw arbiter: all 75 ordinary leaf types (75 parts, every VP has WRP=1). 27 of them have VS more than 405 um from the banks.
- GPL divergence: 3 of the 7 leaves placed so far (t47, t75, t8fix). Every leaf kit runs the same GPL options at under 1 % utilisation,
  so all 75 are exposed. Not checked on the other S81 type families.

## Ranked fixes

1. **GPL exit gate and stable placement, before any form B kit.** Owner: S81-TYPES-R-STRIP (tool change through the normal merge path).
   Fail the kit at PRE_RESIZE when HPWL at GPL exit exceeds 1.2 x the minimum HPWL of the same run, the way gp_noconverge_gate does for GPL-1010.
   Then find the stable form on a t47 place-only pilot (about 45 min): first candidate `GPL_KEEP_OVERFLOW` off, so that the 63,286 buffers
   of the non-virtual timing-driven pass are not inserted at overflow 0.25. I did not run this pilot; the mechanism is inferred from the
   HPWL trace, and t28/t62/t72 show the same spike in their last printed row yet enter detail placement at 1.01-1.04.
2. **Form B, with placement fixed by script.** Owner: S81-TYPES-R-STRIP for RTL and kit, S81-DIE-R2 for the C4 bind and LATCHECK.
   XR flops for the x_w* and VS-side inputs go at the bank end (a region at u_b0/u_b1 holding vpw and its XR flops), on a standard tap,
   never at the VS output. Do not raise LF_CS_HI_D as well. Pilot t34 (501 um) and t62 to a reloaded-GRT read before volume.
3. **VP driver fan-out, not in form B.** Owner: S81-TYPES-R-STRIP. `driver_dswp_q` is one flop driving the hw_d/lo_d/wl_d registers 300-500 um away:
   t62 601 paths, worst -548 at x1.45 (t62 kit WNS is -216; its class at kit RC was not read). Replicate it per slice with kept copies, as vpw does with xl_q/xh_q (0 cycles).
4. **Ring logic with its flops.** Owner: S81-TYPES-R-STRIP. After fix 1, read the ring paths again. If any ring gate is still more than about
   50 um from its flops, place ring logic with the band instead of `ring_place=ff`. The paths have 416.5 ps, so they tolerate about 150 um in total.
5. **t34-class far types.** Owner: S81-DIE-R2. If the t34 GRT read of form B is under +42 ps, move VS toward the banks on the 9 types over 500 um
   (form A as a plan row), or add a second stage on those types only. Do not add a second stage on all 75.
6. **Advisory: reset relay half-cycle leg.** `u_rrl_N/q` (negative-edge flop) -> `u_rrl/state`: 72-151 paths per leaf, 344-361 um, -230 to -306 at x1.45.
   The 405 um reach check passes these hops as full-cycle. Read at GRT before acting; not measured at kit RC.

## Stop list

- Do not build form B kits for t47, t75 or t8 until fix 1 is in: the result cannot be told apart from the placement fault.
- Do not continue the t47, t75 and t8fix routes to sign-off. Their placement is the defect; route time is wasted.
- Do not add stations or cycles to t47 ft6_o/ft2_o for the "2,538 um" path. The station is 310 um from its port.
- Do not approve ce1ca0f7e6 alone (Codex: successor cd9e0a184f handles the u_bound prefix).
- Do not judge any leaf on the x1.45 pre-repair census alone. Use `tt_setup_measure.log` or a reloaded-GRT read.
- Do not swap the VP source into a bound kit to test form B (VP HI and reset are flattened there): fresh elab and bind only.

## Not done

- No GRT read (none existed). No pilot of the GPL change. The Q2 margins come from one t34 path.
- Class shares for t28, t34 and t62 are from the x1.45 census; only t47 and t75 were re-read at kit RC.
- `ot_s81sl_vpw` is not in `origin/main:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv` (f0d0ca4677 holds only vp, cst1, cst there);
  I read it from the kit's bound copy `rtl/ot_s81sl_vp.sv` (tree B6gF2s4tapfix1). Where main keeps it was not found.
