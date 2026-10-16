# VIS-HBM visual layout audit, HBM 660 v5 (2026-10-16)

Owner order 2026-10-16 ~01:00 PT: fix crowding and pin-positioning problems; inspect tile AND die geometry.
Images: `contact_sheet_die.png` (plan floorplan, plan buses, pin-to-pin buses, die case d2) and
`contact_sheet_tiles.png` (worst 12 tiles: floorplan | post-place density | ORFS worst path).
All numbers are in `findings.json` (per finding: owner, job, images, measured numbers, structural fix, tile geometry).

Method: for each HBM job with a placed/routed odb still on the fleet, `scripts/dump_one.sh` runs
`tools/ref_tile/layout_dump.tcl` on the latest odb in the ORFS container and copies the ORFS `reports/*.webp`;
`tools/ref_tile/layout_png.py` renders floorplan/density; `scripts/geom.py` measures pins per face (pins/um,
peak per 20 um, layers), fill, density distribution and macro gaps. Die: `scripts/die_space.py` (20-um grid scan
of compact.P.json) and a scan of the d2 case placement (run.tcl place_inst vs block outlines).

## Die (H-DIE)
| id | finding | numbers | fix |
|---|---|---|---|
| D1 P0 | d2 die clock buffers placed FIRM inside SM outlines | 15,671 of 53,087 (15,645 stream, 26 hbm); stream insertion model 31.6 ns, hbm 14.3 ns from ONE root at (13,990, 10,630); stream pad buffers NE 0 / NW 249 | no buffer homes inside hard outlines; 4 quadrant roots or an H spine in the IDX channels |
| D2 P0 | 124.8 mm2 of the 660 is empty | corner voids beside the LK/EP column 5.5-8.5 mm2 each (~33 mm2), 4 x 240-um band slivers 12.4 mm2 | put the SU overflow (3.71 mm2 short) / HC / COLL in the corner voids, or pull the PHYs toward the EP column and shrink the die |
| D3 P1 | PC row on the PHY edge feeds SM rows 4-7 across the band | SM_HBM relays up to 15.3 mm / 31 stages; pin-to-pin mean HBM_VM 21.3, VM_HUB 15.1, COLL_RING 15.0 | SM slots = 362 mm2 at ~19.5 % fill: re-pack SM, PC row in the quadrant middle with SMs both sides; VM slices next to their PC rows |

## Tiles
| id | owner | master | what the image shows | fix |
|---|---|---|---|---|
| T1 P0 | H-SM | xload_cl2_ctl cl2d (TT -92.5, DRC 4) | 345.6 um square, fill 12 %, 10,786 pins on 100 % of all faces; worst path W-mid -> SE corner | split into face-local slices / strip; replicate lane_en per face |
| T2 P0 | H-SM | xload_cl2_bdring cl2d | clk on W face, all logic + 2,080 pins on E; W 40 % empty | clk to E/N next to the logic; width 172.8 -> ~110 |
| T3 P0 | H-SM | vms_bank_strap q0-q3 (TT -111 / -149.9) | centred 3-SRAM stack, logic in a 30-46 um ring, 4,518 pins on 98 % of all faces, paths wrap the stack | SRAMs against one face, logic one contiguous region, clk at its centre |
| T6 P0 | H-SM | smh_tile_eg rp3 | W/E: 3,705 pins each in 203 um (18.2 pins/um, 366 per 20 um), 83 % of each face empty | spread over >= 700 um / add M6 on N/S; tr_groups at the windows |
| T4 P1 | H-NETLIST | vm_calendar compact (native FAIL spread 92.8) | centred SRAM splits logic W/E; clk W-low wraps the macro | SRAM to N edge, clk S-centre |
| T5 P1 | H-NETLIST | coll vmwrite spread | 103.7 x 388.8 strip, clk at N end, 389 um to S capture | clk at mid-height of W/E |
| T7 P1 | H-SM | smh_bdc d62 | 1,094 of 1,158 pins on S, clk at N-W corner | clk to S face |
| T8 P1 | H-DIE | pc_ctrl_cfg (x128, setup -208) | SRAMs centre-right, C-shaped logic, empty E strip | SRAMs to E edge, clk W mid |
| T9 P1 | H-SU | su bank6 r11 / reduce r4 | fill 41 % / 27 %, reduce pins 14/um in 5 % of face | re-outline (SU is 3.71 mm2 over) |
| T12 P1 | H-LKEP | hfd_ep_static route 2 (GRT-0116) | (run deleted) overflow inside inward SRAM faces of a 47-um centre channel | pins outward or channel >= ~90 um |
| T10/T11 P2 | H-SM / H-NETLIST | bfq cl2 / dbk vp4 ctl | 33 % fill / over-full 0.59 mean, 27 % bins > 0.8 | shrink / grow at next re-kit |

Not inspectable: 27 of 39 HBM netlist masters are RTL-only (no odb); several failed runs were deleted before an image
was taken (smh_tile_rp2, strap2 q0, hep ep1, hcoll_ring_state, smh_tcl_gu d62). Owners: render gate_layout before submit.
