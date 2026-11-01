# cap_rt existing branch-driver locality corrections

These are prototype continuations, not SIGNED views or an adoption request. All sources preserve RTL, cells, cycles, pins,833ps and TT0/FF25 policy and explicit316.5/253.6 clock binding. Original A40 and B25r directories remain unchanged.

B25r finished actual GRT at10:38; the inherited Oct31 policy−2.17/+18.55 was stale and must not be used. Fresh m-s81 policy on own B25rP copy gives TT−32.90/FF+24.74. Its launch clock455.08 versus capture295.13 includes197.8ps branch-to-leaf delay. Two parents sit north of the SRAM while all14/16 real leaves are south.

A40R moves exactly2existingbranchdrivers+2existingdummyloads; B25rR moves2drivers+1dummy. Actual sink-centroid plans and Tcl are included. Both were personally LOOK viewed by the worker, parent, and independent geom_collect agent. The proposed locations clear the SRAM/halo; original AUTO failures remain. Both DPL runs completed with0illegalcells and the exact-mover guard passed; no other cell moved. A40R fresh policy is still FAIL TT−21.76/FF−66.64. The clock correction reduces setup loss but creates real data-hold debt. B25rR fresh policy was queued at this commit; premeasurementTT−24.361 is not a policy verdict, and an untouched dummy-route warning requires rerouting.

Actual A40R/B25rR geometry is included; A40R keepscol_v.418/channel_h.597, B keepscol_v.625/channel_h.605. Original full GRT was0overflow M2–M5; all retainr2r232.58/0over405, pinregp90<8/max53.09, local leafreach19.82/12.31. Root-distance248.96, unsupported5_GRTstage and no duplicateGRTprobe failures are preserved, never presented as AUTO PASS.

A40R20 reuses the legalized relocated ODB as its own4_cts resume input, then standard do-grt with two timing modes TTsetup/FFhold and requested repairtargets20/10. These repair targets are QoR only, not signoff waivers. Run_grt.sh already existed on the branch; no live job uses this working tree as mutable input. It must get actual GRT, subsequent geometry LOOK and released policy PASS before DRT. No DRT was launched in this continuation.
