# S81 E1 measured core views, 2026-10-29

`dsfd_qbank_N` is SIGNED: TT setup +287.41 ps, FF hold +3.53 ps, related-pair skew 11.1/9.5 ps, DRC/antenna 0, post-route LEC EQUIVALENT 384/384. Its new TT/FF native libraries, LEF, pins and receipts are in `physical/die_plan/s81/cores/views/e1_dsfd_qbank_N_1029`. The attachment helper checks SIGNED, 833/60/25 policy, routed equivalence, outline and every pin before setting the library on the plan's 104 exact matching declarations. The actual event `1dfae74037a` passed; wrong-pin and wrong-outline controls were caught. No canonical plan was edited.

`dsfd_qbank_S` and `ot_s81_sstn_base566` are LOCAL_PASS_NEEDS_PARENT, and remain explicitly provisional. Their payload directories retain that verdict and the real-parent receipt requirement. Their measured models may be used to obtain the missing parent qualification; these rows are not SIGNED.

| Core | TT setup ps | FF hold ps | TT/FF pair skew ps | DRC/antenna | Post-route LEC |
| --- | ---: | ---: | --- | --- | --- |
| qbank_N | 287.41 | 3.53 | 11.1 / 9.5 | 0 / 0 | 384/384 EQ |
| qbank_S | 338.97 | 9.55 | 16.5 / 14.4 | 0 / 0 | 1813/1813 EQ |
| sstn_base566 | 413.06 | 0.57 | 15.9 / 13.9 | 0 / 0 | 1707/1707 EQ |

All three used the reviewed E1 physical contracts from `1dfae74037a`. The approved `1bbddb2cb37` GRT buffer cap fix raised a tool stop limit without changing constraints. qbank_S also uses a 20 ps FF repair guard instead of 10 ps, after the baseline routed local hold failed by 0.62 ps. Baseline failures remain in sibling run directories. No RTL or cycle change.

The independent GEOM-71 22:19 review allowed these three E1 cores; the images were viewed again before route. qbank_S and sstn retain the zero-DRC/pin-access condition on their M3 faces; final DRC and pin audits passed.

Runs: `intel1:/srv/opentallas-scratch2/claude/codex-s81phys-2250/kits/dsfd_qbank_N_e1_cap100`, and `epyc2:/srv/opentallas-scratch2/claude/codex-s81phys-2250/kits/{dsfd_qbank_S_e1_h20,ot_s81_sstn_base566_e1_cap100}`.
