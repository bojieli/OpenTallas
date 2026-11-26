# KV ESTRIP G3 v2n placed review

Viewed both place layout and density images on the exact G3 private place-only kit, epyc8 KV-A5t9-r6-publish-1125/private/KV-PV-ESTRIP/kv3_pv_v2n_1125214935/gen/kv3_pv_v2n/run/layout_review/place. The stage completed place. The two main macro columns leave a continuous center corridor, with congested islands between the small center macros and a long strip close to the east edge. The placed-checkpoint channel estimate peaks at 0.391 and north M7 pin-track use at 0.464. Neither has a routed measurement.

The placed review flags 17 opposite-face pins, peak local density 1.022 near (1049.3,189.3) and a 1485.5 µm spread on ctl_cmd bit 31 between three receivers. The placed snapshot has 413,839 instances. The largest opposite-face case is the static strap_ca_k_ft4_i[5] from the east face to its west reader.

Verdict. HOLD route while the affected VPORT mission parity hold is active. Retain this placed checkpoint for the ctl_cmd sibling fanout and east-edge density repair. No GRT, CTS or PDN signoff was established by this stage.
