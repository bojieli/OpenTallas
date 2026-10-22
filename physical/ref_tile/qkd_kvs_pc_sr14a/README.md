# Enlarged PC structural clock replacement

The sr13a PC_H gate reached GRT overflow zero with measured setup +94.8 ps. Its boundary clock spread failed: core TT/FF124.4/109.3 ps and HBM120.1/104.7 ps. Its 19% fill is pin-bound: N and E faces are fully occupied at roughly4 pins/um, and actual SRAM channels must remain open. No outline shrink.

This replacement constructs two dedicated boundary subtrees, one from ck/core_clk and one from hck/hclk, using the existing count-median geometric balanced-tree technique with equal buffer depth and measured leaf-delay equalisation. These are branches of their original clocks, not new clock domains. Core and HBM stay independent. Macro/internal register clocks retain existing CTS. MAIN uses6 balanced levels/80um relay spacing/35ps equalisation target; FALLBACK uses7 levels/55um/25ps. Actual TT+FF spread and timing decide; no waiver or mask.

Safe design review:
1 Pins PASS: source unchanged, real landing registers inherited; full-face N/E density about4/um.
2 Reach PASS in plan:388.8x356.4 frame; new clock repeaters <=80um (FB55); existing data relay/pin-flop structure retained; actual gate rechecks.
3 Fanout PASS inherited native census max32, gate rechecks source; clock leaf fanout is physically buffered, not a shared data driver.
4 Depth PASS inherited setup path; no new logic/data stage, actual setup/hold rechecked after changed clock structure.
5 Storage PASS:23 real SRAMs, no new data storage.
6 Floorplan PASS:5 separated SRAM columns, >=20um pin channels, continuous standard-cell rows; pin-bound low fill disclosed, no shrink.
7 Clock CHANGED: structural balanced boundary branch per original clock; actual TT/FF spread must pass80ps; hold margin0.05ns retained. Internal/macro tree remains original CTS.
8 Schedule/reset PASS unchanged by this clock change: inherited PC sr13 source has i_grp+1ck and i_grp_h+1hck; current die calendar still needs those distinct-domain edge laws before adoption. No new data edge or reset change in sr14.

Exactness benches and mutants are inherited unchanged from sr13 source. Physical buffers/area/clock energy are measured by the gate; no physical or die-calendar PASS asserted in this kit.
