# S81 hi-rs t4 service split, east-west candidate

Viewed s81-svc-hi4-j7-r5-x.png. The retained H8 bind projects 12,674 distinct wires on the earlier y-cut. That is 8.78 per µm before clock/reset and above the 8 per µm face target. Reject that cut for routing. The x-cut at 570.24 µm has 6,896 wires on a 2747.52 µm abutment, 2.51 per µm. Its line falls between the two south HBM windows and crosses no existing window.

The x-cut preserves the original 1442.88 × 2747.52 µm outline and all core shapes. No overlap or out-of-outline box in the layout calculation. The attention side is 73.79% macro area, the remainder 32.69%. The dense attention core rows leave 17.28 µm horizontal channels and the service-side seam channel has room for landings. The 12 new landing SRAMs sit in four groups next to the matching eight engine-stage SRAMs. The attention side still needs actual data/tap reach and the wide seam pin placement seen in the generated kit. In particular, the tall remaining soft-logic area must not pull reset or attention inputs far from their landing.

Verdict PASS-COND for the x-cut geometry draft. The y-cut is FAIL on wiring. Bind, exact pin and clock layout, PDN continuity and the kit image are required before routing. Compute is 0 cycles added by the read-first SRAM form. The separate ATTCUT wrapper contributes +1 ingress and +1 egress, and incremental as-bound cut cycles remain to be priced.

Exact old-bind census and geometry rows: epyc9 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/split-hi4/{hi4-unique-cut-census.json,geometry_x_stage2.json}.
