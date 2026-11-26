# KV ESTRIP G3 v6 and v5ne placed review

Viewed both layout and density images for each exact G3 private place-only kit on epyc8. Both completed placement.

- v6, kit kv3_pv_v6_1125214958. The middle corridor stays open around the staggered small blocks. The south pin bundle and east edge are dense. Channel estimate peaks at 0.561. South M5 pin track use is 0.588, local placement density 1.027, and the core START net spans 1507.0 µm across 60 endpoints. The review flags 62 opposite-face pins.
- v5ne, kit kv3_pv_v5ne_1125215046. The narrow south half of the center corridor is visibly concentrated around the CLAND rings. The placed estimate is 550.7 nets across 531.1 tracks (1.037) between u_pvg1_p0 and u_cland_i_pvw__u_TNQN_N_rN_b_d1, an 8.268 µm gap. South M7 pin track use is 0.538 and local placement density 1.067. The reset START net spans 2563.8 µm across 17 endpoints and 14 opposite-face pins are flagged.

Verdict. HOLD route for both. The VPORT mission parity hold remains active. Carry the exact v5ne corridor and START geometry into the structural repair. GRT, CTS and PDN signoff remain pending on these placed checkpoints.
