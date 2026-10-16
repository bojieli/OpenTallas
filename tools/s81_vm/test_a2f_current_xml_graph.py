"""Regression for source graph extraction: generated scopes, positional ports,
ordered static overrides and dead dataplane / live diagnostic separation."""
import gzip,json,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent

def var(name,direction=None,dtype='2',pin=None):
 return '<var name="%s" dtype_id="%s"%s%s/>'%(name,dtype,(' dir="'+direction+'"')if direction else '',(' pinIndex="'+str(pin)+'"')if pin else '')
def ref(name,dtype='2'):return '<varref name="'+name+'" dtype_id="'+dtype+'"/>'
def con(value):return '<const name="32\'h%x" dtype_id="3"/>'%value
def sel(name,bit):return '<sel dtype_id="1">'+ref(name)+con(bit)+con(1)+'</sel>'
def ass(rhs,lhs):return '<assign>'+rhs+lhs+'</assign>'
def wire(rhs,lhs):return '<contassign>'+rhs+lhs+'</contassign>'
class SourceGraphRegression(unittest.TestCase):
 def test_scope_position_alias_and_dead_output(self):
  dt='<typetable><basicdtype id="1" name="logic"/><basicdtype id="2" name="logic" left="1" right="0"/><basicdtype id="3" name="integer" left="31" right="0"/></typetable>'
  leaf='<module name="leaf" origName="dsfd_vm_static_cap_ctl">'+var('i','input',pin=1)+var('o','output',pin=2)+'</module>'
  top='<module name="top" origName="top" topModule="1">'+var('a','input')+var('b','input')+var('z','output')+var('dead')+var('flag',dtype='1')+var('q')
  # Procedural outputs have different observable cones; a dead data bus must not contaminate live diagnostic dependencies.
  top+='<always><begin>'+ass(ref('a'),ref('dead'))+ass('<and dtype_id="1">'+sel('b',0)+sel('b',1)+'</and>',ref('flag','1'))+'</begin></always>'
  # Clockless alias defaults are overridden in source order.
  top+='<always><begin>'+ass('<const name="2\'h0" dtype_id="2"/>',ref('q'))+ass(ref('b'),ref('q'))+'</begin></always>'
  for n,source in [('g0','a'),('g1','q')]:
   top+='<begin name="'+n+'">'+var('x')+wire(ref(source),ref('x'))+'<instance name="u" defName="leaf"><port name="__pinNumber1" portIndex="1">'+ref('x')+'</port><port name="__pinNumber2" portIndex="2">'+ref('z')+'</port></instance></begin>'
  top+='<instance name="diag" defName="leaf"><port name="i"><concat dtype_id="2"><const name="1\'h0" dtype_id="1"/>'+ref('flag','1')+'</concat></port><port name="o">'+ref('z')+'</port></instance></module>'
  xml='<verilator_xml><netlist>'+top+leaf+dt+'</netlist></verilator_xml>'
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp);(p/'in.xml').write_text(xml)
   subprocess.run([sys.executable,str(HERE/'a2f_current_xml_graph.py'),'--xml',str(p/'in.xml'),'--out',str(p/'out')],check=True,capture_output=True,text=True)
   roles=json.loads((p/'out/role_anchors.json').read_text());summary=json.loads((p/'out/summary.json').read_text());obs=json.loads((p/'out/observability.json').read_text())
   self.assertEqual(summary['hard_leaves'],3)
   anchors={(r['role'],r['leaf_path']):r['bits']for r in roles if r['direction']=='input'}
   self.assertEqual(anchors[('a','dut.g0.u')],2);self.assertEqual(anchors[('b','dut.g1.u')],2)
   self.assertNotIn(('a','dut.g1.u'),anchors);self.assertNotIn(('b','dut.g0.u'),anchors)
   node=next(o for o in obs if 'write:flag' in o['observable_outputs'])
   self.assertIn('write:dead',node['unobserved_outputs']);self.assertNotIn('write:dead',node['observable_outputs'])
   self.assertTrue(any(x['assigned_bits']==2 for x in summary['static_alias_blocks']))
if __name__=='__main__':unittest.main()
