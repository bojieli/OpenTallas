"""Never release zero-overflow prototypes on planned rather than actual sites."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from proto_geometry import hop_stats
from proto_sweep import classify


def source(tmp, out=(800,0)):
    (tmp/'io.tcl').write_text('place_pin -pin_name {ft0_i[0]} -layer M6 -location {0 0}\n'
        f'place_pin -pin_name {{ft0_o[0]}} -layer M6 -location {{{out[0]} {out[1]}}}\n')
    (tmp/'probe.tcl').write_text('place_inst -name st_ft0_0_0 -location {4 0}\n'
        'place_inst -name st_ft0_0_1 -location {400 0}\n')


def record(g):
    return dict(exit='EXIT 0',done=True,total_overflow=0,outline_um=[800,200],
                sta=dict(tt_setup_wns=80,ff_hold_wns=5),ft_hops=g)


def test_pin_window_tail_not_bundle_center(tmp_path):
    source(tmp_path,(800,100))
    (tmp_path/'insts.tsv').write_text('st_ft0_0_0\tDFFHQNx1_ASAP7_75t_R\t4\t0\n'
        'st_ft0_0_1\tDFFHQNx1_ASAP7_75t_R\t400\t0\n')
    g=hop_stats(tmp_path)
    assert g['actual_sites'] and g['over_reach']['ft0']>499
    assert classify(record(g),[])['cls']=='STRUCTURAL'


def test_actual_move_under_old_displacement_threshold_breaks405(tmp_path):
    source(tmp_path)
    # Planned hop396um. A10um legalizer movement is below the old50um
    # displacement threshold but creates a406um actual register hop.
    actual='st_ft0_0_0\tDFFHQNx1_ASAP7_75t_R\t4\t0\n'
    (tmp_path/'insts.tsv').write_text(actual+'st_ft0_0_1\tDFFHQNx1_ASAP7_75t_R\t410\t0\n')
    g=hop_stats(tmp_path)
    assert g['max_hop_um']==406 and g['over_reach_bits']==1
    assert classify(record(g),[])['cls']=='STRUCTURAL'
    # Mutant substitutes planned sites for the second actual cell.
    (tmp_path/'insts.tsv').write_text(actual+'st_ft0_0_1\tDFFHQNx1_ASAP7_75t_R\t400\t0\n')
    assert classify(record(hop_stats(tmp_path)),[])['cls']=='CLEAN'


def test_no_actual_dump_never_falls_back_to_planned_locations(tmp_path):
    source(tmp_path)
    g=hop_stats(tmp_path)
    assert not g['actual_sites'] and g['max_hop_um'] is None and g['errors']
    assert classify(record(g),[])['cls']=='STRUCTURAL'


def test_missing_actual_cell_and_unknown_size_fail_closed(tmp_path):
    source(tmp_path)
    (tmp_path/'insts.tsv').write_text('st_ft0_0_0\tDFFHQNx1_ASAP7_75t_R\t4\t0\n')
    assert hop_stats(tmp_path)['missing_actual_cells']==1
    (tmp_path/'insts.tsv').write_text('st_ft0_0_0\tUNKNOWN\t4\t0\n'
        'st_ft0_0_1\tUNKNOWN\t400\t0\n')
    assert not hop_stats(tmp_path)['actual_sites']


def test_actual_bounding_boxes_cover_new_station_masters(tmp_path):
    source(tmp_path)
    (tmp_path/'insts.tsv').write_text('st_ft0_0_0\tNEW_CELL\t4\t0\t6\t.4\n'
        'st_ft0_0_1\tNEW_CELL\t400\t0\t402\t.4\n')
    g=hop_stats(tmp_path)
    assert g['actual_sites'] and g['max_hop_um']==399.2 and not g['errors']


def test_zero_overflow_cannot_hide_actual_cell_in_core(tmp_path):
    source(tmp_path)
    (tmp_path/'probe.tcl').write_text((tmp_path/'probe.tcl').read_text()+'create_blockage -region {10 10 90 90}\n')
    # Planned cell is outside; actual legalized cell is inside.
    (tmp_path/'insts.tsv').write_text('st_ft0_0_0\tDFFHQNx1_ASAP7_75t_R\t50\t50\n'
        'st_ft0_0_1\tDFFHQNx1_ASAP7_75t_R\t400\t0\n')
    g=hop_stats(tmp_path)
    assert g['st_in_core']==1
    assert classify(record(g),[])['cls']=='STRUCTURAL'
