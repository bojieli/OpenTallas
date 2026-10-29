# BF col (ot_v41_bf_col) G2 V1 failure: root cause + estimate, DIE-S81-25 2026-10-29

## Root cause
- Outline: 450.168 x 198.72 um is the plan_s13r2 slot of u_r0.u_e1e/u_e1w (CHECKED, plan_s13r2.json) and the outline
  of the closed bf_compact199 view. Aspect 2.27 is plan-given; the outline is NOT the cause. No plan delta needed.
- CTS TT -110.39 ps / TNS -1247.66: the shared BF16 tag line[102] -> lane acc_r[26] spends ~650 ps in an 11-level
  buffer ladder (arrival 863.13, required 752.74; Codex V1 CTS report, UNCHECKED by me). This is fanout distribution
  of one final tag-stage register to 16 lanes x (32 acc + control) loads spread over ~400 um, not arithmetic.
- GRT-0183 (net15370 boxed in): initial GRT overflow 0 (Codex, UNCHECKED); the failure is in the FF-only GRT
  incremental hold repair. V1 picture (viewed, ce12_bf_v1.png): ROMs stacked at the W side with a 10.872 um channel
  between them; the W strip (x 5..42) and the 10.9 um throat are the densest region. Hold buffers added there have
  no free horizontal track. Exact net location not extracted (UNCHECKED).

## Estimate (analytic, UNCHECKED until built)
| | TAG_GROUPS 4 | TAG_GROUPS 16 |
|---|---|---|
| lanes per final copy | 4 | 1 |
| max source->acc reach (Codex f6d290b7e est.) | 198.4 um | 29.4 um |
| loads per copy | ~130+ | ~35 |
| buffer levels (BUFx4 ~18 ps + wire) | 5-6, ~200-300 ps | 2-3, ~50-80 ps |
| tag path slack estimate | +240..+340 ps | +460 ps (path no longer critical) |
| added FF | +39 (0.07 %) | +195 (0.36 % of 53,852 sinks) |
| cycles | 0 | 0 |
TAG_GROUPS 16 is chosen for both builds (larger margin, cost 0.36 % sinks); the two parallel fixes differ in the
routing hypothesis for GRT-0183:
- t16a: ROMs at the V1 sites (W stack, channel 10.872 um ~ 97 usable horizontal M2+M4 tracks at 74 % derate).
- t16b: ROMs on the S/N faces at the W side (R180 y 6.048, MY y 129.744): the W strip reaches the logic through a
  60.7 um centre band (~540 usable H tracks) at the clock-entry height; both ROM clk/addr pin bands face the band
  (picture bf_variants_plan.png, viewed). Same outline, same pins.
Both carry KEEP_XPOS 1 (LEC fix, zero cycles, +0 FF net).

## Build obstacle found (CHECKED)
The V1 kit's master_core_infra.tcl / core_infra_plan.json lists every clock sink by synthesized name
(OT_CORE_INFRA_SINK_INSTANCE / UNPLANNED_CLOCK_SINK). TAG_GROUPS 16 (+195 kreg FFs, final-stage FFs renamed) and
KEEP_XPOS (x_pos -> g_xpk.u_xpos.q) change the sink census, and t16b moves the ROM clk pins (tap mp_ck_T00301/2).
So a copied kit cannot run past floorplan: the core clock plan must be rebuilt from the new synth census
(tools/die_plan/master_slice.py --trial + core tree) before PLACE. Step 1 (synth of the new RTL) is launched.
