"""Exercise the real opt-in generator rather than a mirrored placement model."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import dsrom_s81_fulldie as die


class Sites:
    def __init__(self, failure=False, far=False):
        self.failure=failure; self.far=far
        self.unconstrained_calls=0
    def near(self,x,y,w,h,allowed,**kwargs):
        if kwargs.get('prev') is None:
            self.unconstrained_calls+=1
            return (x,y)
        if self.failure: return None
        return (x+1000,y) if self.far else (x,y)
    def add(self,it): return it


def model():
    return dict(insts=[die.Inst('root','root',0,0,10,10), die.Inst('sink','sink',100,0,10,10)],
                regions=[dict(name='frame_0',kind='field',rect=[0,0,2000,2000])],
                buses=[('ck_col_0','col_clock',1,[('root','ck')]),
                       ('rs_col_0','col_reset',1,[('root','rs'),('sink','rs')])])


class StrictTest(unittest.TestCase):
    def setUp(self):
        self.patches=[patch.object(die,'COL_RESET_STRICT',True),patch.object(die,'COL_RESET_TREE',32),
                      patch.object(die,'COL_RESET_SPAN_UM',250),patch.object(die,'relay_dims',return_value=(10,10))]
        for p in self.patches: p.start()
    def tearDown(self):
        for p in self.patches: p.stop()
    def test_small_fanout_still_checked(self):
        m=model(); die._col_reset_tree(m,Sites()); self.assertEqual(m['col_reset_tree']['registers'],1)
    def test_unreachable_never_uses_unconstrained_fallback(self):
        p=Sites(failure=True)
        with self.assertRaisesRegex(ValueError,'unreachable stage'): die._col_reset_tree(model(),p)
        self.assertEqual(p.unconstrained_calls,0)
    def test_bad_placement_refused(self):
        with self.assertRaisesRegex(ValueError,'pin-box upper bound'): die._col_reset_tree(model(),Sites(far=True))
    def test_missing_clock_refused(self):
        m=model(); m['buses']=m['buses'][1:]
        with self.assertRaisesRegex(ValueError,'missing clock'): die._col_reset_tree(m,Sites())


if __name__=='__main__': unittest.main()
