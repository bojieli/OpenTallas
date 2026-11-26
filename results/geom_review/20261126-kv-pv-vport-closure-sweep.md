# KV PV VPORT reach review

The examined A5t6 detailed-placement records for pve and v8e match current G4 normalized type blocks and die context. Their old setup stop was the START receive gate and shared face copies. G5R2 already incorporates the separate START repair. The planned origin rectangle is [3.36, 749.52, 20.64, 762.48] µm at the actual input pin [2.656, 756]. The source has six reader stages on both types and seven or six writer stages. An independent G4 reconstruction found the same reader and writer stage coordinates and cleared stock R-REACH-1 for both. Native post-fix placement remains pending.

## Wide VPORT transport

These direct registered paths are independent of START. I opened the exact pve and v8e placed AutoGeom images. Both have densely used central macro passages. The G5R2 source retains the G4 hard cores, buses, internal stations, FT slots and outlines on both types.

| Type | Exact matched block | VPORT sequential legs over 580 µm | Exact joined ring-to-output chains | Joined chains requiring at least 3 more registered legs with outer endpoints fixed | Worst outer span |
| --- | --- | ---: | ---: | ---: | ---: |
| `kv3_pve` | `11d3bc9fecb7` | 1,552 | 896 | 560 | 1,880.874 µm |
| `kv3_pv_v8e` | `cbf25d1efb86` | 1,740 | 1,024 | 558 | 1,953.990 µm |

The native edge join follows the exact mapped ring read flop through buffer and inverter cells to the bin flop, then to the bout flop. The lower bound divides the fixed straight-line Manhattan span by the 405 µm reach limit and subtracts the two existing registered legs. It ignores obstacles, so it cannot establish final route feasibility. Moving the sole midpoint does not clear these cases. One inspected output goes from the bout Q directly through an inverter and buffer to its top pin. The token owner found no spare compatible three-stage budget in the exact F5 schedule. Keep this pair route-held for an independent boundary placement or transport rebooking. The catalog and per-bit results are in `epyc8:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/pve_v8e_vport_1126/`.

## v3e existing scalar station

The exact v3e type from E8 retained kit `kv3_pv_v3e_1125215107` is unchanged in G5R2. Its native placed VPORT scan has zero sequential legs above 580 µm and one over 405 µm. The named single-bit `u_bin_i_vport_W_N_f_p/q` to `u_ist_o_vport_W_N_f_0/q` path measures 454.815 µm end-to-end, with 76.896 µm the maximum individual buffer segment.

The private G5R2-based candidate `d51c0d9bf4a0` moves only station 0 of `bus:o_vport_W_N_f` to [380.16, 538.488] µm. Its seven stages remain in place logically. The exact old actual endpoint coordinates project to 375.192 µm inbound, 149.391 µm outbound on Q, 150.201 µm on the paired equality register and 119.691 µm on its old reset source. An 8.64 µm placement envelope stays outside the observed hard macro bounds and under 405 µm for the inbound leg. I opened the revised stock plan render at `epyc8:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/pve_v8e_vport_1126/v3e_reseat_r2_render/kv3_pv_v3e.png`. This is a source-only scalar correction. The inherited north channel and START findings remain holds alongside mission VPORT parity. No placement or route was submitted for this candidate.
