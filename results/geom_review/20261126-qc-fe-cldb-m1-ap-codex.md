# QC FE cldb4efe33 M1 clock pin access

Reviewed the exact iteration-55 marker class on the original E10 routed job and the retained GRT input. The 77 M1 markers belong to 48 CLK pins and five leaf tap cohorts. All normalize to the same DFF master obstruction where a right-side VIA12 extension leaves 16 nm of spacing against the 18 nm rule. The markers with PG references are tracked independently by QC.

The diagram at epyc10:/srv/opentallas-scratch2/claude/QC-DRT-ECO/cldb_m1_exact_1126.ap_model.png shows the affected notch and the alternative VIA12 enclosure on the left CLK metal. The exact pin and guide census in the same directory records two alternatives per pin. Forty-three cells have a legal point in both original M1 and M2 guides. The remaining five are within 33 nm of their original leaf guides.

A disposable OpenDB query set 47 named CLK preferences and retained the one already safe preference. It reused four alternate AP definitions by master and placement pattern, without writing the ODB. This is a proposed access correction. The original route continued and the M1 hypothesis remains to be evaluated in a reviewed private route.
