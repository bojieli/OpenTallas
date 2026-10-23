# Roomy RTAG N32/SOQ replacement

The exact normal closure stopped at FLOORPLAN_MARGIN: measured standard-cell area 14,152 um² in 21,835.008 um² core, or 64.8% utilization. Its earlier pre-route gate and native census remain scoped evidence.

The replacement is 116.64 x 246.24 um, preserving width and adding 47.52 um of height. With the existing 2.16 um boundary margin, core area is 27,172.4544 um² and projected utilization from the measured cells is 52.08%. Outline area increases by 5,542.7328 um². This is geometry only: RTL, defines, behavioural contract and sequential edges are unchanged.

All 3,272 pin identities, layers and sizes are retained. Exactly 1,025 north-face pins, including io_n, move north by 47.52 um; the other 2,247 pins stay at their old local coordinates. Clock entries and parent relay endpoints must use the new north coordinates. The pin map is an explicit new request to the die owner, not an alias of the old grant or view. Native census, clocks, pin access and GRT must qualify the new geometry.

The old normal-closure positive behavioural bench exited 0 with its exact numerical and source checks. Normal source/route qualification remains required for the replacement. No final physical, parent-die or token rate is claimed.
