# QC East HC0 folded ST_A receiver occupancy

The exact ST_A +1 source on plan `62d1553bfb23` emits 1,573 eight-stage chains into `u_xh0` in shared type `sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304`. The `a_d` and `cid` bit ordering, face-flop and epoch mapping, and HC0 type geometry match the prior design. The fold removes the optional ninth stage and both count-selector fabrics. The old placed kit reported a 3,135-terminal count-select net.

I inspected a fresh cell-area projection based on the retained Intel1 C1p D8+DMAX1 placement. Its 1,574 south pins, including epoch, split evenly across M7 and M5. Removing just the 1,573 mapped optional flops releases 458.687 µm² in the projection, with up to 9.185 percentage points less fill in a 20 µm bin.

| Measured or projected connection | Worst Manhattan span |
| --- | ---: |
| Actual south pin to landing flop | 11.751 µm |
| Actual landing and eight fixed stage hops | 135.729 µm |
| Projected stage 8 to first functional load after bypassing the old selector | 173.988 µm |

The last projection follows all 1,573 retained bit paths through the old selector to their first functional loads. It finds at most five loads per bit. The source comparison and retained floorplan show sufficient room for the fold. Keep the existing HC0 landing-bank source and review the fresh integrated placement before routing. The projection uses existing cell centers and does not measure fresh CTS, hold, setup or routing. Independent HC0 closure issues have their existing holds.

The figure `hc0_b_hw_folded_occupancy.png` and supporting `impact.json` and `tail.json` are on Intel1 under `/srv/opentallas-scratch2/claude/codex-hc0-sta-pad-impact-1126`. The exact native RTL comparison receipt `exact_folded.json` is in the same relative scratch2 lane on epyc10.
