# hbm-forks 2026-10-09 (hfd_su registry IDLE): the quarter PDN + hard placement blockages over every lane-to-lane gap
# narrower than 12 um (fp-lint "sliver": 64 lane gaps of 10.37 um held placement rows; global placement and the wire
# buffers piled cells into them and the detail placer failed DPL-0033 with 16,746 overlaps on every r24 / r24p quarter
# calibrate).  Same blocker as the attention die tile (physical/hbm_attn_tile_r/die_tile/sliver_block.tcl).
source /src/physical/hbm_accel_die_views/su/pdn_quarter.tcl
set ot_sliver_um 12.0
source /src/physical/hbm_attn_tile_r/die_tile/sliver_block.tcl
