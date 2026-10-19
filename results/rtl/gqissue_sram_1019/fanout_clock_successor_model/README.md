GQ gate successor is BLOCKED at source/model stage. The original tree/route stays intact.

The independent actual DB graph measured21784 sinks (21776FF plus8macros),3654 native I/O clock pins, all/native13..15 stages, macros14..14,2819 buffers/inverters. It covers every expected sink and finds no unreachable clock. New kit-local corrected clock builder plus independent DB graph is prepared, with all-instance and macro support. No successor gate has launched.

Mapped fanout shows a1[290]514,fire_q513,fire/calendar417,RFrowwrite407,reset318,scan_row264 and other256/201/192/182 controls. This supersedes the original source-only SAFE checklist. Current OT_GQ_FAN32 prototype adds16same-edge native kept FF copies for the a1 merge select and exponent clear. It is default off, not activated in the kit and not yet qualification: remaining calendar/RF/target/reset cones still require measured repair.

RF read/write storage is16x101=1616bits, below2kb; the installed bitmap is256bits. Both quantizer long lines are actual8 SRAMs, not flop rings. Same9edge line/AQ13latency/II1 and twohosttransportedges must remain. Target output write-enable/address copies must be emitted on the original programme edge; recapturing p_we/p_wa in GQ would add an unauthorized edge.

Next source repair: split calendar fire enables at held-state/one-hot groups; split RF into <=8bit write chunks using same-edge private programme controls; target scan through retained local pointer copies/one-hot; target-installed reset through native kept parallel two-stage reset copies; census every mapped control and all actual macro instances, then functional positive/reset/mutants and floorplan-only audit before CTS. Source (*keep*) wires alone do not qualify copies.
