"""Physical SRAM leaves of a soft logical group must reach the normal macro contract checks."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as K


def test_outline_less_logical_group_places_its_physical_parts(tmp_path):
    kd = tmp_path / 'kit'
    pd = tmp_path / 'plan'
    kd.mkdir()
    pd.mkdir()
    (kd / 'budget.json').write_text(json.dumps({'type': 'pc'}))
    (kd / 'memory.lef').write_text('MACRO bank\n SIZE 55.32 BY 22.44 ;\nEND bank\n')
    (kd / 'config.mk').write_text('export ADDITIONAL_LEFS = /work/memory.lef\n'
                                  'export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n'
                                  'export CORE_AREA = 4.32 4.32 300 300\n')
    (kd / 'macro_place.tcl').write_text('place_macro -macro_name {u_bound.u_group.u_mem} '
                                        '-location {30 40} -orientation R0 -exact\n')
    (pd / 'die_plan.json').write_text(json.dumps({'partition_types': {'pc': {'contents': [dict(
        inst='group', module='soft_group', physical_parts=[dict(physical_inst='u_bound.u_group.u_mem',
        physical_master='bank', origin_um=[30, 40], outline_um=[55.32, 22.44], orient='R0')]) ]}}}))
    boxes, error = K.macro_boxes(kd, pd)
    assert error is None
    assert boxes == [('bank#0', 30.0, 40.0, 85.32, 62.44)]
    errors, info = K.macro_channels(kd, pd)
    assert errors == []
    assert info['macros'] == 1
