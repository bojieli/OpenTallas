# KV ESTRIP G3 PV v2 placed review

I viewed the layout and density images from exact place-only kit kv3_pv_v2_1125211633 on Intel1. Placement passed, with 159,645 cells. The staggered center macros leave the upper channel open. Several smaller blocks and cells concentrate at the lower east edge.

Estimated channel use peaks at 0.465 and pin-track use at 0.464. The local-density estimate reaches 1.032, and the review flags 16 opposite-face pins. The largest observed data fanout is the bound ctl_cmd register bit 1 at 1,407.2 µm across three sinks. Carry the existing pad-stage ownership into the bounded geometry repair.

Verdict. Hold route on the shared VPORT mission parity condition. CTS, GRT and PDN signoff remain pending.
