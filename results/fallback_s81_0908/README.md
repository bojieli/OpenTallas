# S81 G=2 fallback plan prepared 2026-10-27

Prepared for owner fallback-plan deadline before10-29. This is a concrete plan artifact, NOT frozen, NOT routed and NOT timing-qualified. No synth/P&R was started for this packet.

`die_plan.json.gz` is PD7f composed topology refreshed with the approved fi seam correction and the adopted3.36mm2 PHY lot metadata. `landed_sidecar.json.gz` is its G=2/class landing/collector topology. Extract with gzip; use PREPARED.json hashes to identify the exact uncompressed inputs.

Planning counts (script extracted, not independent sign-off):397partitions,245types,169regions,1211landed ports559181bits on570lanes. Each crossing adds3cycles. The288fi lanes are144direct2cycle +144landed5cycle after correcting prior double-counted in-band stations. Clock remains833ps; policy stays TTsetup/FFhold60/25ps.

| Residual | Current evidence | Required next step / owner |
|---|---|---|
| Landing storage | One remaining placement failure, svc_13.attn_i0 needs21.60um macro-free band (old22-failure history retained) | Reserve legal band in ONE S81plan event; PATH-S81 |
| PHY physical source | u_phy metadata is a reservation, no hardened whole-PHY macro. Actual native parent uses u_core/ot_pdie_serdes_col with6real digital tiles +2analog PMA children | FLOW/sta_pg implements actual split and views. Canonical/PD7d decoder closure correction is codex/s81-phy-manifest-0905@1d5d9adef |
| Clock/root timing | Historical PHY/root timing fails; current169region landing source has no fresh real-view TT/FF gate | PATH-S81 continues actual mesh-fed peripheral tap rebuild. No pseudo mesh common-point credit |
| ROWX | Actual macro source proof progressing, source graph/replica mapping unresolved. Neither full475.2x604.8XM lot nor one SRAM fits current svc5/11 at4.32um halo | tokens/ds + coverage source/graph, PATH-S81 plan lot. rowx_lot_report.json is exact current-layout counterexample |
| QXPQ integration | Current PD7f256declarations use legacy qxpq master; production gb737pin/+1go-capture recipe is not yet bound | S81-CORE-LAT + PATH-S81 one event; compiler prices added cycle |
| Token | Ancestor PD7f strict bind0 does not mean raw canonical b178 port-bind0 or current-die G5 | Token compiler binds refreshed source + real slots, not historical LP calendars |

Reset/START budgets from existing source table: root reset release max103cycles, collector die hop377.984um, root ready587cycles. These are planning budgets; physical_clock_phase_qualified=false. Original failed verdicts remain unchanged.

Related pictures are in results/geom_review/codex_s81_0908. Fallback region image is BLOCKED for route, not a GEOM PASS. Owner questions are tracked in coordination logs; this package chooses no new owner policy.
