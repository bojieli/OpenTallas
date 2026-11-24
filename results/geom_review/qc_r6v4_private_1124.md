# Viewed QC R6V4 private placements, November 24

Both views are the exact `3_place` images from the named epyc7 kits. The private results retain their original verdicts. Both forms remain held for new route admission.

| Type and kit stamp | Observations | Next changed form |
|---|---|---|
| `sle_hc2__clcc5e3e61_1123214807` | [FAIL](qc_r6v4_private_1124/hc2.png). Density and clock taps bunch in the lower 250 µm, with two dense central spines and sparse upper channels. Tap t84 drives 7,876 sinks. The placed scan shows 72 bits over 405 µm on the xh2-to-cw output group (longest 475 µm). The GRT diagnostic finished with zero overflow and policy TT +16.50 ps, FF −87.44 ps, with reused LEC. | Split or rehome the heaviest t84 sinks, keeping the fast output group close to its boundary. Review the resulting clock geometry before rerun. |
| `native59_1123214723` | [FAIL](qc_r6v4_private_1124/native59.png). Two banks of four macros leave a central aisle, but std cells and cross-bank links bunch in its lower and middle throats (estimated V cut 1.026). Three groups need stations or relocation, led by the 62-bit dd_i landing/receiver at 692 µm. Auto-GRT diagnostic overflow 0. Actual GRT was cancelled at pregrt_ff_hold after two hours without progress on the uncapped c66090 runtime. | Retain the live native59 functional hold. Read the existing C1h replacement on the capped runtime as a private diagnostic and align the replacement producer/image before release. Spread the center and shorten dd_i landing in the revised form. |

Kits are under epyc7 `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/`. These placement images give no abutting peer pin-order or final PDN continuity credit.
