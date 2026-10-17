import copy
from pathlib import Path
import tempfile
import unittest
from exact_view_plan import plan


class ExactPlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'m.sv').write_text('module m; endmodule\n')
        self.inst = dict(master='m', source='m.sv', params={'QID':0}, ports={'clk':dict(direction='input',bits=1)})
        self.view = dict(master='m',params={'QID':0},representative='a',instances=['a','b'],kind='SYNTH')

    def inventory(self, other):
        return plan({'instances':{'a':self.inst,'b':other}},{'m':self.view},self.root,self.root)

    def test_same_params_clone_request(self):
        got=self.inventory(copy.deepcopy(self.inst))
        self.assertEqual(got['exact_requests'],1)
        self.assertEqual(got['instance_counts']['EXACT_DECLARATION_CANDIDATE'],2)
        self.assertFalse(got['rows'][0]['native_qualified'])

    def test_wrong_identity_refused(self):
        other=copy.deepcopy(self.inst);other['params']['QID']=1
        got=self.inventory(other)
        self.assertEqual(got['instance_counts']['NEEDS_EXACT_EXPORT_OR_GENERIC_STRAP'],1)
        self.assertEqual(len({r['request_id'] for r in got['rows']}),2)

    def test_same_count_wrong_port_refused(self):
        other=copy.deepcopy(self.inst);other['ports']={'other_clk':dict(direction='input',bits=1)}
        self.assertEqual(self.inventory(other)['instance_counts']['NEEDS_EXACT_EXPORT_OR_GENERIC_STRAP'],1)

    def test_request_identity_independent_of_instance_order(self):
        first=self.inventory(self.inst)['rows'][0]['request_id']
        got=plan({'instances':{'b':self.inst,'a':self.inst}},{'m':self.view},self.root,self.root)
        self.assertEqual(first,got['rows'][0]['request_id'])


if __name__ == '__main__':
    unittest.main()
