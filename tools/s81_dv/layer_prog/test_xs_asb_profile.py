#!/usr/bin/env python3
"""The shared phase planner and BF qualification must preserve the actual frame profile."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools/s81_dv'), str(ROOT/'tools'), str(Path(__file__).parent)]
import xs_place as XP
import xs_bf as XB
import frame_return_plan as P
import v41_rom_ksplit_bankmap as S


def main():
    with patch.dict(os.environ, {}, clear=True):
        assert XB.frame_variant('col_h9_l4_lp_asb_x') == 'asb_x'
        assert XB.frame_variant('col_h9_l4_lp_asb_nx') == 'asb_nx'
        assert XB.frame_variant('col_h9_l4_lp') == 'lp'
        assert XB.frame_variant('col_h9_l4') is None
        assert XB.meas_for({XB.shape_key('col_h9', 2, 'asb_x'): {'pv': {}}}, 'col_h9', 5, 'asb_x') == (None, None)
        with patch.dict(os.environ, {'OT_XS_BF_FRAME':'lp'}):
            try: XB.frame_variant('col_h9_l4_lp_asb_x')
            except ValueError as e: assert 'older frame calendar' in str(e)
            else: raise AssertionError('old BF calendar admitted')
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/'schedule.json'; path.write_text(json.dumps(dict(actual_ret_edge=7)))
        def planner(master,pairs,mat,x,nseg,**kwargs):
            schedule = kwargs.get('frame_schedule')
            # Omitting the profile would reproduce the observed use of the wrong flat return calendar.
            edge = json.loads(schedule.read_text())['actual_ret_edge'] if schedule else 99
            return dict(assign_slots=[(0,0,0)], emission={}, ret=[edge])
        mat=SimpleNamespace(fmt=0,K=8)
        with patch.object(P,'plan_phase',planner), patch.object(XP.LX,'source_frame_schedule',return_value=path), \
             patch.object(S,'segments',return_value=[(0,0)]), patch.object(S,'unit_range',return_value=(0,8)):
            plan=XP.phase_plan('col_h9_l4_lp_asb_x',0x492,[0],0,mat,[],1,0)
        assert plan['ret'] == [7], plan
    print('test_xs_asb_profile PASS: exact phase calendar forwarded; BF old-view reuse refused')

if __name__ == '__main__': main()
