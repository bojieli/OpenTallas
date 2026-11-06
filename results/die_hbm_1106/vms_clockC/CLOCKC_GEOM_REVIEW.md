CODEX reviewed clockC_review.png before any route launch, 2026-11-06.
PASS-COND: original A macro geometry and regional clock topology retained.
Three positive BUFx12f repeaters proposed at (35.64,161.73), (35.64,235.17),
(35.64,307.26), entirely west of the SRAM column beginning at x47.616.
Clock leg source (133.380,161.730), sink (80.514,307.260); split Manhattan
lengths97.740/73.440/72.090/44.874um versus198.396um original endpoint leg.
RTL, native clock-root membership/phase and pin latency unchanged (0cycles).
Construction must preserve exact native root/phase for every clock endpoint.
This is a separate new clock construction from immutable A4_cts.odb;
existing i1/i2 data ECO freeze checks are untouched. Ordinary full signoff,
DRV,DRC,clock checks and actual routed LEC decide adoption.
Current flow tools: released flow-20261106-an-hbm, helper cohort current.
