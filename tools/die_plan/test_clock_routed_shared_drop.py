import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import clock_routed as C
import spef_connectivity as S

class SharedDrop(unittest.TestCase):
    def emit(self,second_x=60.):
        cells={'u':{'x':10.,'y':20.25},'a':{'x':59.,'y':10.26},'b':{'x':59.,'y':30.24}}
        w=dict(name='n',drv='u',loads=['a','b'],horiz=True,trunk_tap=[10.81,21.249],
          branches=[['a',60.,10.395],['b',second_x,30.375]],
          segs=[['M8',10.81,21.249,max(60.,second_x),21.249],['M9',60.,10.395,60.,21.249],['M9',second_x,21.249,second_x,30.375]])
        return '\n'.join(C.routed_tcl([w],cells,{},'BUFx24_ASAP7_75t_R','ndr')[0])
    def test_opposite_drops_share_one_via_and_keep_both_pins(self):
        s=self.emit()
        self.assertEqual(s.count('set jd0 [$e addTechVia [V VIA89]]'),1)
        self.assertEqual(s.count('$e newPath $jd0 FIXED [RL M9]'),2)
        self.assertIn('addITerm [IT a A]',s);self.assertIn('addITerm [IT b A]',s)
    def test_distinct_roots_keep_distinct_vias(self):
        self.assertNotIn('set jd0',self.emit(62.))

class Connectivity(unittest.TestCase):
    def check(self,connections,resistors):
        text='*SPEF "ieee"\n*NAME_MAP\n*1 n\n*2 src\n*3 dst\n*D_NET *1 1\n*CONN\n'+connections+'\n*CAP\n1 *2:Y 1\n*RES\n'+resistors+'\n*END\n'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.spef';p.write_text(text);return S.audit(p)
    def test_conn_and_positive_rc_do_not_hide_open_sink(self):
        r=self.check('*I *2:Y O\n*I *3:A I','1 *2:Y *1:1 10\n2 *3:A *1:2 10')
        self.assertEqual(r['unreachable_pins'],1);self.assertEqual(r['failures'][0]['unreachable'],['dst:A'])
    def test_connected_cell_and_output_port(self):
        r=self.check('*I *2:Y O\n*I *3:A I\n*P out O','1 *2:Y *1:1 10\n2 *1:1 *3:A 10\n3 *1:1 out 10')
        self.assertEqual(r['nets_disconnected'],0)
    def test_input_port_is_driver_and_output_port_is_sink(self):
        r=self.check('*P in I\n*I *3:A I\n*P out O','1 in *3:A 10\n2 out *1:2 10')
        self.assertEqual(r['failures'][0]['unreachable'],['out'])

if __name__=='__main__':unittest.main()
