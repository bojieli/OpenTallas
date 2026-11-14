import importlib.util,json,sys,subprocess,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import kit_istations as K
BUS=dict(name='x_i0',dir='in',width=3)
def txt(epoch=''):
 return '''module top(input clk,input[3:0]x_i0);\nwire [2:0] x_i0_b,x_i0_q;\nwire x_i0_eb;\nwire x_i0_eq;\not_dp_st #(.W(3)) u_bin_x_i0(.clk(clk),.q(x_i0_b),.eq(x_i0_eb));\not_dp_dly #(.W(4),.D(1)) u_lpad_x_i0(.clk(clk),.d({x_i0_eb,x_i0_b}),.q({x_i0_eq,x_i0_q}));\n'''+epoch+'\nendmodule\n'
def make(src=None,W=3,Dp=1,banks=None,face=None):
 src=txt()if src is None else src;b=dict(BUS,width=W);p=K.packed_input_delay('t',b,src,W,Dp);banks=banks if banks is not None else[[[2*i,0]for i in range(W+1)]for j in range(Dp)];e=dict(regs_um=[[0,0]]*Dp)
 return K.packed_exact_geometry('t','x_i0',src,e,p,W,(banks,[1.404,.27],face))
def runtime(names,W=3,Dp=1,epoch=1,large=False,offsite=False,occupied=False,hard=False):
 prefix=r'''set placed 0
set reserved 0
proc ff_hits_explicit {x y w h} {return OCC}
proc ff_reserve_explicit {x y w h} {incr ::reserved}
set ff_dbu 1000
set ff_sw 100
set ff_x0 0
set ff_y0 0
set ff_x1 100000
set ff_y1 100000
set ff_orient [dict create 0 R0]
set is_n 0
set is_fh [open /dev/null w]
proc master {m args} {switch $m {getName {return DFFHQNx1} getWidth {return WIDTH} getHeight {return 270} isBlock {return 0}}}
'''.replace('WIDTH','2000'if large else'1404').replace('OCC',str(int(occupied)))
 prefix+='set ff_blk block\nproc block {m args} {return {'+' '.join('i'+str(i)for i in range(len(names)))+(' hardinst'if hard else'')+'}}\n'
 if hard:
  prefix+=r'''proc hardinst {m args} {switch $m {getMaster {return hardmaster} getBBox {return hardbox} getName {return HARD_MACRO}}}
proc hardmaster {m args} {if {$m eq "isBlock"} {return 1};return BLOCK}
proc hardbox {m args} {switch $m {xMin {return 0} yMin {return 0} xMax {return 2000} yMax {return 1000}}}
'''
 for i,n in enumerate(names):
  prefix+='proc i%d {m args} {switch $m {getName {return {%s}} getMaster {return master} setLocation {incr ::placed} default {return {}}}}\n'%(i,n)
 banks=[[[2*i+(0.03 if offsite else 0),0]for i in range(W+1)]for j in range(Dp)]
 table=' '.join('{'+' '.join('{%s %s}'%tuple(p)for p in b)+'}'for b in banks)
 cmd='is_packed_exact_banks u_lpad_x_i0 %d %d {%s} 1.404 .27 ist:x_i0 %d'%(W,Dp,table,epoch)
 code=prefix+K.PACKED_EXACT_BANK_TCL+'\nset rc [catch {'+cmd+'} msg]\nputs "RC=$rc PLACED=$placed RESERVED=$reserved MSG=$msg"\n'
 r=subprocess.run(['tclsh'],input=code,text=True,capture_output=True,check=True);return r.stdout+r.stderr
class Tests(unittest.TestCase):
 def test_metadata_unobserved(self):
  call,m=make();self.assertTrue(m['epoch_unobserved']);self.assertIn('is_packed_exact_banks',call);self.assertEqual(m['sites_per_stage'],4)
 def test_epoch_observed(self):self.assertFalse(make(txt('assign status=x_i0_eq;'))[1]['epoch_unobserved'])
 def test_epoch_alias_initializer_is_observed(self):self.assertFalse(make(txt('wire observed = x_i0_eq;'))[1]['epoch_unobserved'])
 def test_epoch_port_not_discarded(self):self.assertFalse(make(txt().replace('module top(input clk,input[3:0]x_i0);','module top(input clk,input[3:0]x_i0,output x_i0_eq);'))[1]['epoch_unobserved'])
 def test_wrong_actual_width(self):
  with self.assertRaises(ValueError):K.packed_input_delay('t',BUS,txt().replace('.W(4)','.W(5)'),3,1)
 def test_wrong_connection(self):
  with self.assertRaises(ValueError):K.packed_input_delay('t',BUS,txt().replace('{x_i0_eb,x_i0_b}','{x_i0_eb,wrong}'),3,1)
 def test_reject_partial_depth(self):
  with self.assertRaises(ValueError):make(txt().replace('.D(1)','.D(2)'))
 def test_reject_face_override(self):
  with self.assertRaises(ValueError):make(face=[[0,0]]*4)
 def test_wide1105_metadata(self):
  src=txt().replace('[3:0]x_i0','[1104:0]x_i0').replace('[2:0]','[1103:0]').replace('.W(3)','.W(1104)').replace('.W(4)','.W(1105)')
  b=dict(BUS,width=1104);p=K.packed_input_delay('wide',b,src,1104,1)
  self.assertEqual((p['width'],p['depth']),(1105,1))
  xy=[[2.16*(i%16),.54*(i//16)]for i in range(1105)]
  call,m=K.packed_exact_geometry('wide','x_i0',src,dict(regs_um=[[0,0]]),p,1104,([xy],[1.404,.27],None))
  self.assertTrue(m['epoch_unobserved']);self.assertEqual(m['sites_per_stage'],1105)
 def test_reject_overlap_including_reserved_epoch(self):
  with self.assertRaises(ValueError):make(banks=[[[0,0],[2,0],[4,0],[0,0]]])
 def test_reject_cross_stage_overlap(self):
  with self.assertRaises(ValueError):make(txt().replace('.D(1)','.D(2)'),Dp=2)
 def test_reserved_footprint_collision_before_any_place(self):self.assertIn('RC=1 PLACED=0 RESERVED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(4)],occupied=True))
 def test_hard_macro_collision_before_any_place(self):self.assertIn('RC=1 PLACED=0 RESERVED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(4)],hard=True))
 def test_pruned_epoch_slot_is_reserved(self):self.assertIn('RC=0 PLACED=3 RESERVED=4',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(3)]))
 def test_runtime_observed_epoch(self):self.assertIn('RC=0 PLACED=4',runtime(['u_lpad_x_i0/r[0][%d]$_DFF_P_'%i for i in range(4)],epoch=0))
 def test_runtime_optional_absent_epoch(self):self.assertIn('RC=0 PLACED=3',runtime(['u_lpad_x_i0/r[0][%d]$_DFF_P_'%i for i in range(3)]))
 def test_missing_payload_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][0]','u_lpad_x_i0/r[0][2]']))
 def test_missing_observed_epoch_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(3)],epoch=0))
 def test_duplicate_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][0]']*2))
 def test_footprint_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(4)],large=True))
 def test_row_site_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(4)],offsite=True))
 def test_later_stage_missing_before_any_place(self):self.assertIn('RC=1 PLACED=0',runtime(['u_lpad_x_i0/r[0][%d]'%i for i in range(4)],Dp=2))
 def test_escaped_brackets(self):self.assertIn('RC=0 PLACED=4',runtime(['top/u_lpad_x_i0/r\\[0\\]\\[%d\\]$_DFF_P_'%i for i in range(4)]))
if __name__=='__main__':unittest.main(verbosity=2)
