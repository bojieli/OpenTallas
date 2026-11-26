# HEAD R21 HE EPC pin access review

The review covers the in_data[127] access geometry at the current R21 u_epc location of (423.36, 60.48) µm in R0. The target-only LEF is d6d46723991c, from R21 base cd40317c8860 and exact signed core GDS 712154fb538f. The eight signed stack shapes and three continuous same-net conductor rectangles affect only the target pin. The change replaces the affected M5 and M7 local obstruction windows with exact signed geometry. The native target pin passes EOL. The inherited whole-view EOL counts are 44 on M5, 571 on M6, and 1 on M7.

I viewed the local overlay on epyc10 at /srv/opentallas-scratch2/claude/abstract-exact/gdsdrc/r21_epc_exact_needle_1126/r21_epc_exact_needle_overlay.png, SHA d9751efef935. It shows the clear M5 aperture, the M6 pin on its horizontal track, and the continuous M7 vertical pin. The surrounding solid and dotted shapes retain the neighboring obstruction and signed metal context. The exact parent ODB independently passed both power rails and found zero VDD/VSS wire or via bounding boxes in the target envelope plus 144 nm. See E8 units oth-ubuntu-2944529-1795681320 and oth-ubuntu-3512247-1795681973.

The route remains held pending HEAD's parent geometry disposition and normal admission.
