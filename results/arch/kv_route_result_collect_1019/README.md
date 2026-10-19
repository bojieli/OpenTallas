# KV bounded route/gate pickup

Collected 2026-10-19T14:10:35.155711-07:00. Read-only existing results; no synthesis, native extraction, repair, route, REVIEW or submission. All progressing jobs preserved. SHA256/size ledger is manifest.json. Gate source manifests identify exact content snapshots; source commit alone does not replace the manifest. Source identities: AHUB d1865add311e snapshot with daemon overlays; D2D fa42fd5d3 lane candidate with exact shipped manifest; HOST p8 8a04df728 and S2 180845247 lane tips with exact shipped manifests.

| Existing gate | Actual TT reg→reg setup ps | TT diagnostic hold ps | TT/FF pin spread ps | State |
|---|---:|---:|---|---|
| AHUB sfa | -361.804 | -26.191 | 86.5 / 97.3 | FAIL, trial GRT overflow 0 |
| AHUB sfb | -420.069 | -105.079 | 116.3 / 123.2 | FAIL, trial GRT overflow 0 |
| D2D r7w_sf | -16.074 | 34.862 | 44.9 / 39.7 | WARN, trial GRT 0 |
| D2D r7w_sfb | -23.403 | 36.528 | 51.6 / 47.2 | WARN, trial GRT 0 |
| D2D ovl_sf | -95.508 | 34.450 | 63.7 / 53.1 | WARN, trial GRT 0 |
| D2D ovl_sfb | -100.716 | 34.640 | 51.1 / 48.0 | WARN, trial GRT 0 |
| HOST prompt p8 | 43.000 | 36.058 | 45.8 / 42.0 | CTS finished; GRT live |
| HOST ORDER S2c | -5.875 | 37.598 | 88.0 / 85.5 | CTS finished; GRT live |

These gate timing values use placement-estimated RC. Hold in this table is the TT diagnostic GATE_PC value, **not FF signoff hold**; no fresh FF timing receipt was generated. Negative setup values are actual register-to-register paths, not input/output diagnostics. Final gate verdicts for p8/S2 do not yet exist; inherited p7/order results are not evidence for them. At collection p8 GRT repair had reached iteration 54000; S2 GRT repair iteration1850 (temporary WNS -89.843ps). No terminal detailed-route DRC value for these gates.

AHUB run identities: ot-epyc6:/srv/opentallas-scratch/claude/ref_gate/qkd_ahub_sf{a,b}-20261019-114348. Terminal12:51:34/12:48:50. Boundary has 645 measured pins,3425 clock sinks; TT/FF max insertion934.1/788.1ps (sfa),971.5/825.0ps(sfb). Gate retains child same-layer OBS/pocket warnings (338/338 zh face pins partially covered;68/69 reciprocal child). Existing 13 unsafe source roots, full logical reach/registered boundary and real PG/contact obligations remain. PNG packet: /home/ubuntu/wt/kv-ahub-1019/physical/ref_tile/qkd_ahub_sf{a,b}/gate_layout/{floorplan,density}.png. No approval written.

D2D runs: ot-epyc7:/srv/opentallas-scratch/claude/ref_gate/qkd_d2d_static_{r7w_sf,r7w_sfb,ovl_sf,ovl_sfb}-20261019-121102. Each existing dense64x512 macro still has W793/E792 contacts on77.784um (10.195/10.182perum>6), independently recorded2a0584a66. WARN/GRT0 does not qualify source, macro access, boundary register/reset, PG binding or parent neighbor matching. No known extraction repeated. Actual useful-storage/lifetime/32flag transport model remains the next structural owner. PNGs are in /home/ubuntu/wt/claude-kv-d2d-1019/physical/ref_tile/<kit>/gate_layout/.

HOST runs: ot-epyc6:/srv/opentallas-scratch/claude/ref_gate/qkd_hr_core_prompt-20261019-115518 and qkd_hr_core_order_s2c-20261019-115103. Original local clients977679 and665891 (S2 gate656335) alive. CTS completion6577s and5754s; areas29570um2 and27223um2. Prompt macro clocks have TT/FF max slew143.0/149.5ps; ck.json macro_clk flags the two pins against its configured120ps diagnostic threshold. This is not a newly established Liberty/electrical violation: the selected Liberty max_transition was not independently resolved in this bounded pickup. The owner clock rule remains TT/FF pin spread<=80ps plus matched boundaries; insertion/sink count alone does not reject a tile. Preserve source all-driver/contact/PG/HOSTMU obligations. No source or ODB mutation.

Already recorded daemon receipts reused exactly:
- DCAL bc4 k22a-89fec6b77 CLOSED: TT setup+171.71ps, FF hold+27.79ps, DRC0; SS sensitivity-135.35ps. Record f46052b50, main0eef62f89, batch12:02:13. Do not duplicate the record.
- DCAL bc4w k22w-5a13c6974 terminal FLOORPLAN_MARGIN: actual daemon utilization60.5% (std316/core523um2)>60%; batch11:56:11. Earlier standalone gate PASS does not supersede daemon failure. No geometry tweak/reroute authorized here.
- cdc_pc c3-50430b600 CLOSED12:59:30: TT setup+174.82ps, FF hold+14.18ps, DRC0; SS sensitivity-117.73ps. Record7b4518d85, main22f53efd9. CDC host previously CLOSED03e3a8b12/main58fc3dbc1 TT185.85/FF20.92DRC0. Both retain independently documented PG_HOLD, not repaired by this receipt.

Current frozen GEN8v4 uses DCAL_BC=1 but NO BC4/FLT activation. The new closed bc4 is a different view/source/flag choice; binding requires owner source/native/clock/PG and actual fault-consumer review. No live flags changed. Next pickup: existing p8/S2 final gate/PNGs, actual AHUB structural clock/depth/model redesign, D2D storage/validation model, and DCAL closed-view current-source native/PG/neighbor audit. ROOT remains sole merger and activation owner.
