# S81-AGGRO: the more-dies knee and the hub shape (2026-10-15)

PLANNING SCREEN. Field capacity comes from the real canonical packer (tools/s81/canonical_capacity.py through
hub_shape_sweep.place). Stage counts come from the real allocator (tools/dsrom_s73_pair1.py alloc, 416 runs; each point
is the smallest S that passes after S-1 failed). Hub blocks use their actual outlines and actual closed-port faces
(S-DIE 2210 pin JSONs, capture_face_review_2118). Routability comes from a gcell maze screen, not OpenROAD GRT.
Data: `s81_aggro.json` (roll-up), `knee_summary.json`, `hub_vm_centred.json`, `hub_grt_screen.json`. Images: `img/`.
Tools: tools/s81/{hub_shape_sweep,hub_vm_centred,hub_grt_screen,aggro_render,aggro_summary}.py.

## 1. The more-dies knee (rm-k = k field columns removed, uniform roots, no refill)

| point | pairs/die | stages | dies | MTP / AR tok/s | silicon | hub width | strip tier fits | road cut | hub whitespace |
|---|---|---|---|---|---|---|---|---|---|
| today (legacy map) | 2,417 | 81 | 376 | 4,238 / 1,448 | 0 | 6.1 mm | - | - | - |
| rm0-rm2 | 2,385-2,322 | **74** | 348 | 4,264 / 1,460 | -6.5 % | 6.1-8.5 mm | no | >1 | 0.09-0.35 |
| rm3 | 2,000 | 89 | 408 | 4,210 / 1,434 | +7.4 % | 9.7 mm | no (0.60 cut) | 3.96 | 0.43 |
| rm4 | 1,985 | 89 | 408 | 4,210 / 1,434 | +7.4 % | 10.9 mm | yes | 0.45 | 0.48 |
| **rm5 (C5, adopted)** | 1,973 | 89 | 408 | 4,210 / 1,434 | +7.4 % | 12.1 mm | yes | 0.28 | 0.53 |
| rm6-rm7 | 1,715-1,706 | 103 | 464 | 4,160 / 1,410 | +20.4 % | 13.3-14.5 mm | yes | 0.17-0.14 | 0.58-0.61 |
| rm8 | 1,513 | >119 | ? | - | - | 15.7 mm | yes | 0.11 | 0.65 |

The allocator stripes every matrix over all 128 roots, so the stage count moves in steps: 74 for 2,322 pairs or more,
84 only for the ragged 2,116 point (rm3 with parity refill), 89 for 1,973-2,088, 103 for 1,706-1,838, 111 for 1,631 or
fewer. **rm5 is the knee.** It is the widest hub on the 89-stage plateau, at the same die count as rm3/rm4. One more
column (rm6) costs +56 dies and +13 % silicon for 1.2 mm of hub. The 74-stage plateau (-60 dies vs rm5) has at most
8.5 mm of hub (9.4 mm with the TILE-FILL node-strip refill), and no hub arrangement with the actual blocks fits that
width with roads at 0.45 or below. Every point clears the owner floor (MTP well above 3,000).

## 2. Hub shape on rm5: C5 strip vs VM-centred

The actual faces force one vertical chain: gather (N face) -> capture (t_vm 13,376 b on its S face) -> VM -> SU (all
17,137 VM bits on its N face). The C5 strip (SU | VM | capture column | VCH | HC) breaks that chain. It has
**6 structural turns** (SU-VM, capture-VM, PQ-VM, WFC-VM, WFC-collective, host-collective) and no reserved turn
channel. Screen: max utilisation 2.94, 496 edges over 0.60, 27 overflowing.

| layout | struct. turns | hub relays (12 flows) | worst flow cut | roads W/E (cut) | screen max / >0.60 / overflow | field-tree hub edges | net tok/s vs C5 |
|---|---|---|---|---|---|---|---|
| C5 strip (Codex combined_2118) | 6 | 25 | turns unroutable | 662/552 (0.56/0.36) | 2.94 / 496 / 27 | 65 | - |
| vmc VM-centred column | 0 | 5 | 0.187 | 1,426/771 (0.26/0.26) | 0.66 / 27 / 0 | 88 | +0.9 % AR / +0.8 % MTP |
| **vmc2 = vmc + S-DIE D1/D2 (adopted by S-DIE)** | 0 | 9 | 0.187 | 1,426/771 (0.26/0.26) | 0.73 / 14 / 0 | 91 | +0.6 % / +0.6 % (MTP ~4,234) |
| vmc3 VM-centred square, low, HC side by side | 0 | 8 | 0.187 | 1,557/530 (0.24/0.38) | 1.11 / 55 / 9 | 70 | +1.1 % / +1.0 % (MTP ~4,250) |
| vmsq square (HC side by side, high) | 0 | 4 | 0.187 | needs a hub of 12.7 mm or more (rm6 or refill) | - | - | - |

Per-flow cuts for vmc2 (W/E faces M4+M6 36.46 t/um, N/S faces M3+M5 48.61 t/um):

| flow | cut | relays |
|---|---|---|
| SU-VM 17,137 b | 0.187 | 0 |
| capture-VM 13,376 b | 0.159 | 0 |
| MIX4-VM 12,732 b | 0.111 | 0 |
| HC_s-HC_t 15,660 b | 0.177 | 1 |
| collective-HC_s 8,225 b | 0.083 | 0 |
| capture-gather 6,959 b | 0.083 | 0 |
| HC_s-VM | 0.093 | 4 |
| PQ-VM | 0.126 | 4 |

The WFC is mirrored (MY) so that its E-face ports face the VM. Token-rate deltas use 1 edge on every node of the class:
su 0.130 %, field 0.035 %, coll 0.021 % AR (accepted_cost.rom_loss on token_path_20261009). SU-VM counts 4 crossings
per SU job. Field-tree edges are the max collect plus the max broadcast hub hops in the gcell screen. With the gather at
the top of the chain, the trees are longer, and that gives back most of the relay gain.

## 3. The two large ledger rows

- **VM.RELAY (+25 edges, 5.13 %) does not change with the hub shape.** I re-ran a2f_reach_price on midcapd with SU on
  the S face: write 9 and read 16, unchanged. The cost comes from VM size: ingress and read-to-port spans of 5.4 mm.
  Scaling the measured hops by sqrt(area) gives 17 edges at x0.5 area, 22 at x0.75, 31 at x1.25 and 34 at x1.5
  (~0.205 % AR per edge).
- **More dies do not shrink the VM** (S-VM). Row width sets its size (128 banks x 128 b; 53 sources x 16,384 b), not the
  number of layers per die. Halving SRAM depth saves only ~1 mm2 of 19.06.
- **VM.READ (9.09 %):** the hop-2 -> hop-1 figure was measured on the legacy bgq28 leaf. In A2-F, "hop 1" means dropping
  the b4 relay level: -2 cycles per round trip, -32 leaves, -0.54 mm2 and no outline growth, so it fits in every
  candidate. VM.READ and VM.RELAY must be re-priced together on A2-F.
- The remaining lever is VM-internal port placement (each client's port next to its leaves). S-VM is measuring it with
  the vmc faces: SU on S, capture and MIX4 on N, PQ on W, collective, WFC and HC on E. The VM may grow to 5,037 um wide
  in rm5 with roads kept at 0.45.

## 4. Recommendation

Keep **rm5_p1973 / 89 stages / 408 dies** (the knee). Replace the C5 strip with the **VM-centred column vmc2**. It has
0 structural turns, every flow at 0.19 or below, roads at 0.26, and 0 screen overflow. S-DIE adopted it at 23:xx with
the AGGRO r2 fixes: a 432-um SU|VM channel and a 237.6-um channel under the collective. Its tok/s gain is small (+0.6 %).
The win is routability: it removes the 6 unroutable turns behind the C5 capture-face and SU-face failures. The next
candidate is vmc3 (low chain, HC side by side), at +1.1 %, after a seam fix. The VM.RELAY/READ prize sits inside the VM
(port placement and b4 removal) with S-VM, not in the hub shape or the die count.
