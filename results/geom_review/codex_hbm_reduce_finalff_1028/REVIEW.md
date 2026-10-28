# HBM collector reduce final-FF core trial

Verdict: PASS-COND for the core-only current-source trial. Images personally viewed 2026-10-28.
No whole-parent geometry or sign-off qualification is claimed.

The current C20j selected core is 233.28 x233.28um with the same d5760c6fb862 pin table. W/E wide buses
occupy aligned, evenly spaced faces; maximum10um-window density2.4pins/um is below6 and M4 track use0.115.
Control pins have ample N/S space. No memory macros or macro walls occur inside this core.
The centered8.64um clock island is retained from its explicit master slice. Core M5 VDD/VSS straps and
post-GRT native pg_connect remain staged; the actual runtime PG check is still required.
The previous same-slot placement used31.6%area and reported clean DPL, leaving space for a sparse residual data repair.

The final-FF option adds no RTL/clock cycle, changes no pin, outline, clock latency,833ps period or60/25 uncertainty.
It preserves the bound202.5ps FF SDC; this kit has no authority for an automatic measured-mean rebind.
Old actual TT setup is+27.43ps; oldFFhold−0.34ps after GRT. The optional corrective pass must retain TT>=0 and
recheck FF>=0 after legalization/routing, with existing clock freeze and strict geometry comparison.

The parent context image's40 long control-bit arrows are abstract core-to-core references. The HBM die owner
mapped all five buses to explicit planned equal-age serial_k2 chains: q0 has3stations each(maxhop289.4um),q1
has4each(maxhop101.3um). Their actual RTL/calendar qualification remains OPEN in the parent lane.
The parent hub's other source/clock/street defects remain separate; this review authorizes no parent route.
