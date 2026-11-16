# FABLE-FIX-S81-SERDES handoff (owner of S81 serdes__t1 x2, t13, t14, t15 x2)

Gates: DRC 0, TT setup >= -42 ps, FF non-port hold >= 0, bind + LATCHECK. Lane S81-SERDES-DPL (Opus) follows this lane; it had no live builds at 06:40 PST 11-16.

## Facts (06:40-07:20 PST 11-16)
- Hub log: only serdes__t13 and serdes__t15__cla2127225 fail DPL-0033 (01:23, plan G3b 3fa87b84b18, v1 tree). t1__clb45, t15__cla3d, t16, t12, t2, t3 pass DPL on G3b. t14 and t1__clfe stopped at sdc_lint (B6gE) before place.
- t13 failed DPL log (epyc8 kw43 wave attempt_5, logs kept): 233 movable cells never legalise (repair buffers in u_cland_ft3/4/5_i, u_ft_ft3/4/5_o_0, reader_start flops), 116 off-site, 146 overlaps, 151 edge-spacing. 39,612 ring cells FIRM. Failed DB was cleaned.
- v2 tree kit_preflight refuses the old ring form (ring_ff: ring >= 256 bits without ring_place=ff), so on v2 these kits stop before place until the plan has ring ff.
- F2s family (F2sv, F2s2) serdes blocks vs G3b: only landing bands change: ring_place ff and rect x 17.28..92.88 -> 17.28..56.16 (E side 2792.88 -> 2829.6).

## Builds (epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes, v2 tree src_s81_pin_eb1e73448bd0, v2 bind kw45/s81bind_pin_eb1e73448bd0/out)
- gen.sh / gen2.sh FORM TYPE: wave recipe (die_gen_env + item_env of kit_wave.json 11-16).
- A/ = G3b plan as is, ring_ff preflight line disabled in the private kit (old form, to get the failed DB): serdes__t13, serdes__t15__cla2127225, place running.
- B/ = planB.json + sideB.json = G3b with the 11 serdes type blocks + sidecar collector types of F2sv (ring ff, narrow bands); kit-rtl + prepare-stations on G3b (bind matches), gen phys on planB: all six items, place running.
- Client logs: localhost scratchpad placeA_*.log, placeB_*.log; kit logs <form>/<type>/run_place.out.

## Next
1. Read A t13 3_5_place_dp-failed.odb: where the 233 cells sit (rows/sites, FIRM neighbours, blockages). Name the cause.
2. Read B place: DPL pass or not. If pass: the fix is the F2s ring-ff rows (already in the die plan) and the serdes items go to route on B; if fail: flow fix on branch claude/fable-fix-s81-serdes-1116.
3. Route the passing kits (run_kit.sh route 80 16), sign-off, export to AGIdock /archive/opentallas-signed-1114 + rtx-pro.
