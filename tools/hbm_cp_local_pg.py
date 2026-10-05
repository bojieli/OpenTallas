#!/usr/bin/env python3
"""Finite CP-local PG bridge in the existing 43.2um slot; no clock/RTL change."""
import math


def cp_local_pg_model():
    # Legal ASAP7 width classes from actual tech LEF; bridges stay in the CP core.
    core = 43.2
    pitch = core/10
    return dict(core_outline_um=[core,core], extra_cell_area_um2=0,
        additional_RTL_latency_cycles=0, memory_ports_added=0,
        rails=dict(layers=['M1','M2'],width_um=.018,pitch_um=.54,followpins=True),
        local_bridges=[dict(layer=l,width_um=w,pitch_um=pitch,offset_um=pitch/2,
                           total_PG_metal_fraction=2*w/pitch)
                       for l,w in [('M3',.09),('M4',.12),('M7',.16)]],
        feed_connections=[['M1','M2'],['M2','M3'],['M3','M4'],
                          ['M4','M7'],['M7','M8'],['M8','M9']],
        intermediate_via_landings=['M5','M6'], M6_stripes_added=0,
        outer_grid=dict(layers=['M8','M9'],width_um=.48,pitch_um=2.7669,
                        total_PG_metal_fraction=2*.48/2.7669,unchanged=True),
        raw_M6_core_tracks=675, actual_PDNon_retained_tapcell_projected_M6_tracks=63,
        clock_other_tracks=64, signal_via_tracks=math.ceil(675*.05),
        residual_M6_core_tracks=675-63-64-math.ceil(675*.05),
        required_signal_tracks=236, west_signal_entrance_PG_intersections=0,
        PDN_only_shape_connected=True, loaded_IR_qualified=False,
        placement_CTS_route_qualified=False, clock_protection_policy_changed=False)


def cp_local_pdn_tcl():
    return '# Existing 43.2um CP core: local rail/bridge grid, unchanged outer M8/M9 PG.\nadd_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power\nadd_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground\nglobal_connect\nset_voltage_domain -name CORE -power VDD -ground VSS\ndefine_pdn_grid -name cp_service -voltage_domains {CORE} -pins {M8 M9}\nadd_pdn_stripe -grid cp_service -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins\nadd_pdn_stripe -grid cp_service -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins\n# Local vertical collectors / horizontal crossbar; explicit M4-M7 via landings.\nadd_pdn_stripe -grid cp_service -layer M3 -width 0.090 -spacing 2.070 -pitch 4.32 -offset 2.16\nadd_pdn_stripe -grid cp_service -layer M4 -width 0.120 -spacing 2.040 -pitch 4.32 -offset 2.16\nadd_pdn_stripe -grid cp_service -layer M7 -width 0.160 -spacing 2.000 -pitch 4.32 -offset 2.16\nadd_pdn_stripe -grid cp_service -layer M8 -width 0.48 -spacing 0.90345 -pitch 2.7669 -offset 1.38345\nadd_pdn_stripe -grid cp_service -layer M9 -width 0.48 -spacing 0.90345 -pitch 2.7669 -offset 1.38345\nadd_pdn_connect -grid cp_service -layers {M1 M2}\nadd_pdn_connect -grid cp_service -layers {M2 M3}\nadd_pdn_connect -grid cp_service -layers {M3 M4}\nadd_pdn_connect -grid cp_service -layers {M4 M7}\nadd_pdn_connect -grid cp_service -layers {M7 M8}\nadd_pdn_connect -grid cp_service -layers {M8 M9}\n'
