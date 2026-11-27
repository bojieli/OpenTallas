"""QC-R3-STA 11-27 (C-STATION-BIT-SCRAMBLE): the monotone lane exit assignment is a PLAN property (ft_slots.lane_mono), not a per-run env flag.

plan ft_slots.lane_mono -> gen_phys.ft_lane_mono_exports -> OT_FT_LANE_MONO_SLOTS (config.mk) -> face_flops.tcl ff_mono_slot_on.
Replays the real station pass of test_face_flops_lane_mono (S81 kv_leaf t3 ft3 inputs): listing the slot gives the flag-on placement,
listing another slot (or none) gives the flag-off placement, and explicit-site slots stay bypassed.
"""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import gen_phys as G
import schema as S
import test_face_flops_lane_mono as T


def test_export_and_validation():
    assert G.ft_lane_mono_exports({}) == []
    assert G.ft_lane_mono_exports({'ft_slots': [{'name': 'cws0'}]}) == []
    assert G.ft_lane_mono_exports({'ft_slots': [{'name': 'cws0', 'lane_mono': True}, {'name': 'x_a', 'lane_mono': False},
                                                {'name': 'x_ctl_fw', 'lane_mono': True}]}) == [
        'export OT_FT_LANE_MONO_SLOTS = cws0 x_ctl_fw']
    with pytest.raises(ValueError, match='boolean'):
        G.ft_lane_mono_exports({'ft_slots': [{'name': 'cws0', 'lane_mono': 'yes'}]})
    with pytest.raises(ValueError, match='unsafe'):
        G.ft_lane_mono_exports({'ft_slots': [{'name': 'a b', 'lane_mono': True}]})


def test_schema_field():
    assert json.loads((BASE / 'die_plan.schema.json').read_text()) == S.SCHEMA
    item = S.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['ft_slots']['items']
    row = dict(name='cws0', in_face='N', out_face='S', width=516, stations=5, lane_mono=True)
    jsonschema.validate(row, item)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(row, lane_mono='yes'), item)


def test_plan_slot_list_selects_the_monotone_placement():
    fx = T.FIX
    off, _ = T._run(False)
    on, _ = T._run(True)
    listed, res = T._run(False, dict(fx, env={'OT_FT_LANE_MONO_SLOTS': fx['slot']}))
    other, _ = T._run(False, dict(fx, env={'OT_FT_LANE_MONO_SLOTS': 'not_this_slot'}))
    assert listed == on and "miss=0" in res
    assert other == off
    assert listed != off
