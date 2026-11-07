# BKSEL RF8 two-leaf structural landing candidate

SOURCE ONLY; no place/CTS/route pilot launched. Default OFF (`OT_RT_ETM_LOCALFACE=1`). No RTL, PIN-cycle, clock-period, uncertainty, or160ps ETM-target change. Baseline RF8/vH remains live and untouched.

Actual vH stable4CTS geometry has16 ETM BUF8 leaves,14 within30.41um of macro CLK and two output branches107.47/147.10um long. All300 negative native-bank FF input endpoints belong to those two banks (HC0,HC2). The original code deliberately placed BUF8 by the selected source driver. Those actual source drivers are BUF24, not weak pads.

The candidate moves those2 BUF8 to the actual bottom CLK faces and adds one source-local BUF24 per branch at the reviewed existing h3_0 source. Its purpose is to isolate the existing register clock tree from the long input-wire load. New cells are FIRM/dont_touch. The other14 ETM leaves retain RF8 behavior. No feedback pads are added to the two new branches.

Exact read-only TT extraction (13pins, normal ot-run16GB2T, unit `oth-ubuntu-2483114-1794083839`) gives h3_0 arrival_max_rise482.270325ps. Exact kit TT8-library selector/SDC and placementRC used; no repair/P&R/live-kit writes. Rise targets are g-160: HC0~671,HC2~673ps. Falling arrival includes half-cycle phase and is not compared directly to rise targets.

Exact TT INVBUF220122 input caps: BUF24=2.35026fF,BUF8=.852045fF; native macro CLK2.9406fF. Clock calibrated placement RC R=.0214161kOhm/um,C=.113298fF/um. Model uses NLDM interpolation (conservative clamp at smallest characterized load), source20ps slew assumption, extra existing-source load delay slope.25ps/fF and wire output slew sqrt(input_slew^2+(2.2*Elmore)^2). This is not a measured new-form timing result.

The candidate uses ONE source-local BUF24 per branch at(123.012,180.900)/(131.976,180.900), followed by the moved faceBUF8. These source drivers isolate the existing shared h3_0 clock/register tree from long-wire loads. No corridor padding stages. Zero added buffers would add60.41fF across the2 branches; source isolation reduces that to6.02fF (existing h3 report load~50.63fF,11existingfanout). The isolated branch wires are248/264um along macro-aware x106.434/x185.814 bent corridors. These paths are planned, not forced routing guides; actual routes remain an explicit review risk. Leaf reaches remain6.5/5.7um.

With exactTTNLDM +samewire model, comparison by extra buffers per branch (0direct;1sourceisolator;2source+1corridor;3source+2corridor), including BOTH source loads:

| extra buffers | HC0 estimated macro ps | HC2 estimated macro ps | HC0/HC2 max input slew ps | added shared-source load fF |
|---|---:|---:|---|---:|
|0|646.94|660.92|179.62/203.20|60.41|
|1|665.99|679.29|175.93/197.59|6.02|
|2|651.39|658.79|69.00/65.82|6.02|
|3|663.67|670.87|42.44/47.97|6.02|

All these slew estimates fit the existing BUF8 max_transition320ps, and output cap is far below BUF24 max1474.56fF; the85um planner stage envelope was NOT an existing qualification limit. Minimum load-isolated topology is1 extra buffer. Its ~30–35ps cell delay is explicitly the source-isolation/balance residual, not concealed in the old25ps iso budget. Zero direct buffers perturb h3/register arrival by~15ps; one isolated source gives~1.5ps shared perturbation. The one-buffer form estimates macro clocks~26/16ps earlier than H, consumes less than baseline initialGRT+50ps setup margin, and improves FF input hold directionally; exact FF residual remains unmeasured and must be collected in the one permitted CTS-only pilot. No new form is qualified from this estimate.

Current pinned projection budgets186/200ps include coupledsource load and pin/bend allowance. Projected/actual +/-15ps landing differences are ADVISORY; only normal signoff timing is authoritative. Structural wrong-master/region/row/selectedmacrocount/leafreach failures remain closed. The160ps target stays unchanged.

Structural guards refuse a wrong/absent BUF24 source, a source outside the reviewed physical region, non160ps target, missing legal row, unexpected selected-macro count, or resized/displaced leaf with output reach>8um. Timing projections and target+/-15ps checks are advisory.

Review the source/model and minimum-topology image before the ONE permitted CTS-only candidate. No route launch is authorized. The candidate must produce actual TT/FF results and images before any later decision. Preserve kit-generated leaf_affinity appendage when staging the canonical hook; that appendage is not part of canonical source.
