"""Safety properties of the A-scoped physical ECO selector."""
import copy, unittest
import ectl_native_hold_plan as E

class SelectionSafety(unittest.TestCase):
    def setUp(self):
        self.cells={
            'ot_inhold_0':(E.HB,{'A':'rs[1]','Y':'pad'}),
            'ot_ihdrv_0':('BUFx4f_ASAP7_75t_R',{'A':'pad','Y':'pre'}),
            'hold1':(E.HB,{'A':'pre','Y':'mid'}),
            'hold2':(E.BF,{'A':'mid','Y':'post'}),
            'ff':('DFFHQNx1_ASAP7_75t_R',{'D':'post','CLK':'ck'})}
        self.loads={'rs[1]':[('ot_inhold_0','A')],'pad':[('ot_ihdrv_0','A')],
                    'pre':[('hold1','A')],'mid':[('hold2','A')],'post':[('ff','D')]}
        self.paths=[{'endpoint':'ff/D','slack_ps':80,'points':{'hold1/A':100,'hold2/Y':140}}]
    def choose(self):
        return E.choose('rs[1]',221,self.cells,self.loads,self.paths)
    def test_keeps_original_pin_pad(self):
        c=self.choose();self.assertEqual(c['remove'],['hold1','hold2'])
        self.assertEqual(c['FF_paths'][0]['estimated_hold_ps'],40)
    def test_real_extra_load_blocks_pair(self):
        self.loads['mid'].append(('other','D'));self.assertIsNone(self.choose())
    def test_no_sequential_or_clock_cell_removal(self):
        self.cells['hold1']=('DFFHQNx1_ASAP7_75t_R',self.cells['hold1'][1])
        self.assertIsNone(self.choose())
    def test_every_reached_endpoint_must_have_margin(self):
        bad=copy.deepcopy(self.paths[0]);bad['endpoint']='async/RESETN';bad['slack_ps']=65
        self.paths.append(bad);self.assertIsNone(self.choose())
    def test_missing_timing_is_not_evidence(self):
        self.paths[0]['points'].pop('hold2/Y');self.assertIsNone(self.choose())
    def test_cannot_remove_a_named_original_pad(self):
        self.cells['ot_inhold_second']=self.cells.pop('hold1')
        self.loads['pre']=[('ot_inhold_second','A')]
        self.assertIsNone(self.choose())

if __name__=='__main__':unittest.main()
