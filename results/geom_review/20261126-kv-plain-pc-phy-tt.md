# KV plain PC PHY ingress setup

Four retained detailed placements fail on the same PHY-ingress to PCC path. The launch is a local west PHY landing flop in `i_phy_Q__sN_piN_d1`, and the capture is `u_kvpc1.pc__pi` at the bottom of the right-hand PCC macro. The clock period is 833 ps. On the first type, the path spends 1,415.21 ps after launch through 19 buffers or inverters and still misses setup by about 534 ps if the full ideal and macro clock penalty is removed.

| Type suffix | Retained TT setup slack |
| --- | ---: |
| r872e39b5a | −1058.15 ps |
| r8b421e514 | −1094.51 ps |
| r85c02c25c | −1077.76 ps |
| r882954158 | −1087.26 ps |

The worst direct launch-to-capture distance is about 1,453 µm. The private proposal adds four stages to each of the four 289-bit PCC words. I viewed all four stock-lattice projections. Each seats 4,624 distinct flops with a worst projected intermediate hop of 400.680 µm and final hop of 78.957 µm. The failing PCC1's projected final hop is 41.211 µm. The model uses exact retained macro, pin and launch positions and the stock station-site allocator on the modeled lattice.

The scoped strict source bind passed with zero errors and declared all 4,624 affected native pins at four additional edges. Native RTL comparison confirms the 1,152 data and four valid bits per type retain their bit order and all have the same four additional `clk` edges. The six independent wire epochs still feed their existing fault-fold paths. The programme and hard-ready schedule need a new proof for the shifted arrival ages. No new placement or routing was submitted.

The exact AUTH8 compiled report `75cfd39f5002` reproduces T8192 K and V leads 140 and −139 and the published group pacing. The 16 affected PCs in ES_0, WS_0, EN_0 and WN_0 each have zero slack in the model for their latest allowed front-end arrival. With four added controller edges at the old dates, all 1,024 modeled K and V block-go obligations would be early. Keep the candidate private until the revised controller and front-end reservation schedule, queue occupancy and boot/epoch behavior are priced and proven. The coordinator assigned that work to the programme lane.

The proposed source plan is `b485a1b1974f` under epyc8 `/srv/opentallas-scratch2/claude/codex-kv-pc-tt-1126/candidate/plan_pc_phy_plus4_private_r3.json`. The same directory's parent contains `plain_pc_phy_plus4_projection.png`, `emitted_stage_proof.json`, `native_path_class.json`, and `compiled_front_hold.json`. The native RTL proof used identical stage rows on `fef9716724a7`. The reviewed plan updates the physical rank keys to the emitted names.
