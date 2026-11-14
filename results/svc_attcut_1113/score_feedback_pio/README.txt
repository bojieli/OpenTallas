NamedT32 head0 actual P-prefetch/return schedule: PASS

Extends aa7281b932 staged score→SX→SM→P cone with runtime +pio; default800
retained. Reuses the existing protectedSX master; no production source/native
compile. Same sourceGO128/root257..264/tap277..284/SE281,285/SMwrites391,393.

Conservative +pio=384: selected sourcefirst394 (=firstwrite391+3 andfinalwrite
393+1), fires394..408 II2; Proot436..450; header437/body438..452, all8words
exact. Counts identical to late800 positive: roots8,taps8,SE2,SM2nonzero2,
Psource8,Proot8,header1/body8;missing0,errors0,SXfault0,SMfu/fo0. GOrelative:
fire266..280,root308..322,header309,body310..324.

Tooearly +pio=380 +early=1: selectedfirst390 is beforefirstSMwrite391;
actual Psource missing1; 4returnedFP32coefficients and1packedPword are lost,
plus finalmissingpredicate giveserrors6. SXfault0/SMfu/fo0, so the control
isolates actual Pbuffer availability. Same binary, no repeated default/drop
runs or broad offset sweep. Earliest392/393 NOT tested; this is a conservative
namedfixture schedule, not a minimum or global/allhead PIO calibration.

E7unit oth-ubuntu-2836674-1794616601 exit0; capsule score_feedback/out_pio.
Runner PIO_PRICE_ONLY=1 uses conservative/early cases and may reuse an exact
protectedSX cache via SX_PROTECTED_CACHE. Default mode retains late800 and
its dropped-valid control. No readiness wait or request-driven source issue.
SM/SErows and fixedPIO dates stay separate facts; no invented scalar PIO/PVO.
