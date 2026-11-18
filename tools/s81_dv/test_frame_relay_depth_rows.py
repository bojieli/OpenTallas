"""S81-D8E-LAT 11-18: relay_depth rows on a master's band types are visible to the frame schedule check."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'layer_prog')]
import frame_schedule_asb as F


def plan():
    parts = [dict(name=f'{f}{k}', type=f'col_h9_r{k}__t{f}') for f in ('a', 'b') for k in range(3)]
    types = {p['type']: {} for p in parts}
    types['col_h9_r2__ta']['relay_depth'] = [dict(inst='u_y_rt_20a_3', port='o', D=2)]
    types['col_h9_r1__tb']['relay_depth'] = [dict(inst='u_e3', port='xs_a', side='sink', bits=[0, 31], D=1)]
    types['col_h10_r0__tz'] = dict(relay_depth=[dict(inst='u_y_rt_1', port='o', D=1)])
    return dict(partitions=parts, partition_types=types)


def test_master_rows_only():
    rows = F.relay_depth_rows(plan(), 'col_h9')
    assert [(t, r['D']) for t, r in rows] == [('col_h9_r1__tb', 1), ('col_h9_r2__ta', 2)]
    assert F.relay_depth_rows(plan(), 'col_h10') == [('col_h10_r0__tz', plan()['partition_types']['col_h10_r0__tz']['relay_depth'][0])]


def test_frame_instance_rows():
    assert [t for t, _ in F.relay_depth_rows(plan(), 'col_h9', {'a0', 'a1', 'a2'})] == ['col_h9_r2__ta']
    assert F.relay_depth_rows(dict(partitions=plan()['partitions'], partition_types={}), 'col_h9') == []


def test_main_reports_unscheduled_rows():
    src = (HERE / 'frame_schedule_asb.py').read_text()
    assert 'RELAY_DEPTH_UNSCHEDULED' in src and "relay_depth_rows=len(rd_rows)" in src
