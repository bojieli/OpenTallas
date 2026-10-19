# Gated180 synthesis candidate — not a release view

This candidate exists to measure synthesis area, preserved regions, and fanout. The current root-only clock constraints are not a timing certificate for its period4 bank clocks. Do not run CTS/signoff or bind this view until all generated-clock scenarios and the native family census are supplied.

Safe-design checklist before synthesis/floorplan:

1. Pins PASS: bankwrite captures input; root output mux register captures output. Receiver reset has rs0/rs1. Static K straps only. Enable/source epoch registered.
2. Reach PASS:39.096um square below405um single-cycle limit.
3. Fanout MODEL: kept payload regions<=16bits, replicated4select/reset controls. Inspect synthesized sinks, shared status and ICG load before CTS.
4. Depth MODEL: bankwrite->shadow is inverted capture; shadow->registered root mux. One extra receivercapture priced explicitly.
5. Storage PASS:1748bits total incl9ICG latches at180b/cycle;600b requires4children/padding120b. No waiver.
6. Floorplan MODEL:39.096um square; synthesis616.224um2 yields~51%core utilization. Full-face payload pins<6/um, no macros/power islands.
7. Clock OPEN:8realICGs period4T/pulseT/2. Need each compiled bank phase/K/root relationship, descendant-root census, native TT/FF insertion/spread<=80ps, ICG enable checks,150/100 crossroot reserves, and all data/metadata/select/reset paths directly timed. No falsepaths/MCPs.
8. Schedule PASS behavior only: extra outputcapture1; writeboot+1/readreset+2; fixed4write readiness prologue. AllK/phase/3integeragebands/reset grid has199008 actualedge checks, age.25..3.125T and overwrite>=.875T across two boots. Legacy ages unchanged; totalE and sampled bankK are distinct.

Committed evidence: results/arch/qwen_split_compute_1014/safe_qw_land_1019/gated_phase_joined_r2_384.json and bench_gated. Physical TT setup/FF hold remains unqualified.

ResetR2:rawrs drives only the two face landing flops; localreset clear and fixed-fill readiness release derive from landedrs1. No steady data age change; boot releases tested separately.
