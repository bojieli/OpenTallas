"""Prebuild actual18-SRAM port direct-capture placement, no circuit change."""
def model():
    from tools.hbm_coll_port_interior_model import model as base
    m=base()
    m['capture_placement']=dict(default_enabled=False,observed_unanchored_outputs=2147,
        physical_hook='physical/hbm_accel_die_views/coll/rtl_ps/capture_adjacent_place.tcl',
        master='ot_sram_1r1w_128x256_m1_r2c2',maximum_pin_to_capture_um=100,
        local_density=.55,added_cells=0,added_registers=0,added_cycles=0,
        required_reservation='sum(ceil(capture_master_width / .55 / site_width)*site_width*row_height)',
        fit='actual copied floorplan ODB gate must place every directly connected capture D at legal free row site',
        actual_reservation_um2=1764.0342,actual_capture_cell_area_um2=953.532,
        actual_direct_capture_count=3270,measured_max_pin_to_capture_um=7.701,
        runtime_API_qualified=True,
        validation='fail closed on combinational macro load, no legal site, or zero capture count')
    m['qualification']['physical_capture_placement']='PASS copied full floorplan ODB only; routed closure pending'
    return m
