"""Control packet views preserve source identity and coherent valid/data ages."""
import copy
import unittest
from layer_prog.bound_control import BoundControl

class Backend:
    def __init__(self):
        self.units={'s':dict(ports={'data':dict(dir='output',bits=[100,101,102]),'valid':dict(dir='output',bits=[103])}),
                    't':dict(ports={'data':dict(dir='input',bits=[200,201,202]),'valid':dict(dir='input',bits=[203])})}
        self.ages={(100,200):2,(101,201):2,(102,202):2,(103,203):2};self.sinks={}
    def route(self,source,sp,target,tp):
        pairs=list(zip(self.units[source]['ports'][sp]['bits'],self.units[target]['ports'][tp]['bits']))
        try:ages={self.ages[p] for p in pairs}
        except KeyError as e:raise ValueError('wrong current per-bit source') from e
        if len(ages)!=1:raise ValueError('mixed per-bit ages')
        return dict(age_edges=ages.pop(),width=len(pairs))

class NativeControlTest(unittest.TestCase):
    def model(self):
        c=object.__new__(BoundControl);c.die=Backend();c.cache={};return c
    def test_explicit_views_keep_bit_identity_and_original_inventory(self):
        c=self.model();before=copy.deepcopy(c.die.units)
        r=c.transport('s','data','t','data',[2,1],[2,1])
        self.assertEqual(r['age_edges'],2);self.assertEqual(r['source_bits'],[2,1])
        self.assertEqual(c.die.units,before)
    def test_wrong_bit_permutation_is_not_an_alias(self):
        c=self.model()
        with self.assertRaisesRegex(ValueError,'wrong current'):c.transport('s','data','t','data',[0,1],[1,0])
    def test_valid_and_payload_must_have_same_current_age(self):
        c=self.model();c.die.ages[(103,203)]=3
        with self.assertRaisesRegex(ValueError,'ages disagree'):
            c.group('actual control',[('s','data','t','data'),('s','valid','t','valid')])
    def test_out_of_bounds_and_duplicate_views_fail(self):
        c=self.model()
        with self.assertRaises(ValueError):c.transport('s','data','t','data',[-1],[0])
        with self.assertRaises(ValueError):c.transport('s','data','t','data',[1,1],[1,1])

if __name__=='__main__':unittest.main()
