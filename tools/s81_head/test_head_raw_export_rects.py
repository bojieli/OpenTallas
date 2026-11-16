"""Real he10 fixed reset/clock short, with NF14r metal reservations."""
import copy
from head_raw_export_rects import fix


def case(tmp_path):
    # Exact final DEF geometry of the one he10 DRC marker. A placement blockage
    # cannot move either fixed BPin; the plan's scalar export must change.
    (tmp_path/'hd_host_e.io.tcl').write_text('''place_pin -pin_name clk_t5 -layer M7 -location {93.2800 51.8720} -pin_size {0.0320 0.7680}
place_pin -pin_name {rst_start_raw_1} -layer M7 -location {93.2800 51.8400} -pin_size {0.0800 0.4320}
place_pin -pin_name {rst_start_raw_3} -layer M7 -location {17.3120 473.6880} -pin_size {0.0800 0.4320}
''')
    clock=dict(landing_contract=dict(pins=[dict(name='rst_start_raw_1',xy_um=[93.28,51.84]),
                                               dict(name='rst_start_raw_3',xy_um=[17.28,473.688])]),
               reserved_sites_um=[dict(rect_um=[92.178,51.3,94.338,52.38],kind='die_clock_tree',route_layers='M1-M7'),
                                  dict(rect_um=[92.718,50.76,94.878,51.84],kind='die_clock_tree',route_layers='M1-M7'),
                                  dict(rect_um=[16.686,473.04,18.846,474.12],kind='die_clock_tree',route_layers='M1-M7'),
                                  dict(rect_um=[17.226,472.5,19.386,473.58],kind='die_clock_tree',route_layers='M1-M7')])
    return dict(partition_types=dict(hd_host_e=dict(outline_um=[600,570],clock=clock)))


def test_actual_short_clears_clock_pin_and_complete_metal_reservation(tmp_path):
    raw=case(tmp_path)
    report=fix(raw,tmp_path,avoid_clock_sites=True)
    changed={r['port']:r['new_um'] for r in report['changes']}
    assert changed=={'rst_start_raw_1':[92.064,51.84], 'rst_start_raw_3':[16.608,473.688]}
    assert not report['overlaps_after']
    assert report['clock_pins_moved'] is False and report['added_cycles']==0
    # Check physical edges directly, independently of the helper overlap routine.
    assert changed['rst_start_raw_1'][0]+.040+.032 < 92.178
    assert changed['rst_start_raw_3'][0]+.040+.032 < 16.686


def test_reservation_avoidance_is_opt_in_and_layer_specific(tmp_path):
    raw=case(tmp_path)
    original=copy.deepcopy(raw)
    report=fix(raw,tmp_path)
    assert 'rst_start_raw_3' not in {r['port'] for r in report['changes']}
    for row in original['partition_types']['hd_host_e']['clock']['reserved_sites_um']:
        row['route_layers']='M8-M9'
    report=fix(original,tmp_path,avoid_clock_sites=True)
    assert 'rst_start_raw_3' not in {r['port'] for r in report['changes']}
    assert original['partition_types']['hd_host_e']['clock']['landing_contract']['pins'][1]['xy_um']==[17.28,473.688]
