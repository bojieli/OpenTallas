# V4.1 microblock hold and clock repair

The root-approved follow-up retains the two existing microblock outlines, original RTL, SRAM views,0.92ns period,60ps clock uncertainty,32-fanout limit and all physical checks. It requests20ps positive hold-repair margin on both cuts and16-sink CTS clustering on VM only. It uses the same immutable ORFS image and source hashes as the completed PG-corrected negative baseline. No architectural pipeline stage is added.

## VM: standalone physical pass

The source-pinned routed VM cut passes: setup+264.783ps, hold+9.088ps; zero setup/hold endpoints, DRC, antenna, slew, capacitance and fanout violations. Physical VDD/VSS connectivity checks pass. This is one512x128 SRAM and its local registered interface at ASAP7 TT, not the full four-bank VM or die. Primary test pins remain false-pathed, so a real producer/consumer composition still needs its own I/O budgets.

Compared with the same-image PG-corrected baseline, the repair adds289 standard cells and30.035um2 cell area (535.465um2 total),665um wire and1518vias. FF count remains680. CTS logs create52 clock buffers versus27 previously; hold-repair buffers291 versus10. Tool-estimated total power rises2.36724→2.72305mW; this is neither measured silicon power nor isolated clock power. The die envelope stays280x160um. Full final report and record are under results/physical_abi3/asap7/chip/v41_macro_local_hold20.

## MP1: standalone physical pass

The MP1 cut also passes: extracted setup+411.059ps and hold+10.566ps, with zero timing, DRC, antenna, slew, capacitance and fanout violations; physical VDD/VSS checks pass. Its20ps repair target adds261 standard cells and19.027um2 cell area (304.460um2 total),1065vias, while wire length changes by-16um. FF count stays413. Tool-estimated total power changes1.44591→1.46255mW. The die envelope remains220x160um. CTS retains20 clock buffers; hold buffers increase124→364.

Both approved jobs finished on the same immutable image without constraint relaxation. These TT predictive-PDK microblock passes remove the specific local pin-access, power-orientation, hold and fanout blockers. Next architecture work is explicit producer/consumer timing and placement budgets for composition; no larger neighborhood, full2MiB VM, die clock, MCMM signoff or token-rate claim is established.
