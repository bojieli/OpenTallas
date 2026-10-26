"""Bounded source selection/join contracts, never a GEN or age qualification."""
import ast
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from qwen_split import headprep_source as H
from qwen_split.source_pin_plan import rtl_ports
ROOT=Path(__file__).resolve().parents[2]
class HeadprepSource(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tt=rtl_ports(ROOT/H.SOURCE,H.MASTER)
  cls.native=rtl_ports(ROOT/'rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv','qfd_native59_dv_headprep_obs1')
  cls.env=dict(OT_QWEN_HEAD_PREP='1',OT_QWEN_ROPE='1',OT_QWEN_STATUS_OBS='1',OT_QWEN_MU_NU='4')
 def test_default_identity_no_source_reads(self):
  old=('qfd_tt_ctlm_dv','rtl/qwen_dv/qfd_tt_ctlm_dv.sv')
  self.assertIs(H.select(old,'/does/not/exist',{}),old)
 def test_actual_selected_source_and_joins(self):
  # Actual source parser result above, all actual full-file SHAs still checked.
  with patch('qwen_split.source_pin_plan.rtl_ports',return_value=self.tt):
   self.assertEqual(H.select(None,ROOT,self.env),(H.MASTER,H.SOURCE))
  joins=H.prepare_joins(H.MASTER,self.tt,self.native)
  self.assertEqual([j[2]for j in joins],[1,18,18,2])
  self.assertEqual(len({tuple(j[3][1])for j in joins}),4)
 def test_wrong_selected_flags(self):
  for f in ('OT_QWEN_ROPE','OT_QWEN_STATUS_OBS','OT_QWEN_MU_NU'):
   e=dict(self.env);e[f]='0'
   with self.subTest(flag=f),self.assertRaises(ValueError):H.select(None,ROOT,e)
 def test_wrong_master(self):
  with self.assertRaises(ValueError):H.prepare_joins('qfd_tt_ctlm_dv',self.tt,self.native)
 def test_missing_tt_port(self):
  for p,_,_ in H.PREP:
   q=dict(self.tt);q.pop(p)
   with self.subTest(port=p),self.assertRaises(ValueError):H.prepare_joins(H.MASTER,q,self.native)
 def test_wrong_tt_width_or_direction(self):
  for v in ((1,'output'),(2,'input')):
   q=dict(self.tt);q['emb_user']=v
   with self.subTest(value=v),self.assertRaises(ValueError):H.prepare_joins(H.MASTER,q,self.native)
 def test_missing_native_port(self):
  n=dict(self.native);n.pop('head_prepare_position')
  with self.assertRaises(ValueError):H.prepare_joins(H.MASTER,self.tt,n)
 def test_wrong_native_user_width(self):
  n=dict(self.native);n['head_prepare_user']=(4,'input')
  with self.assertRaises(ValueError):H.prepare_joins(H.MASTER,self.tt,n)
 def test_missing_source_file(self):
  with tempfile.TemporaryDirectory()as td,self.assertRaises(FileNotFoundError):H.select(None,td,self.env)
 def test_fixed_source_age_refused(self):
  with self.assertRaisesRegex(ValueError,'never inherit old HR_PIN_REG1'):H.reject_unbound_hr_age()
 def test_default_dv_selector_matches_original_config(self):
  # Execute actual production source configuration statements through WCOL_VIEW;
  # no geometry/GEN routines. Flag OFF uses byte-identical historical map values.
  import subprocess
  before=subprocess.check_output(['git','show','3e13199b0:tools/qwen_split/dv_case.py'],cwd=ROOT).decode()
  after=(ROOT/'tools/qwen_split/dv_case.py').read_text()
  def config(text):
   tree=ast.parse(text);start=next(i for i,n in enumerate(tree.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='WCOL_RTL'for t in n.targets));stop=next(i for i,n in enumerate(tree.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='WCOL_VIEW'for t in n.targets))
   ns={'os':os,'Path':Path,'__file__':str(ROOT/'tools/qwen_split/dv_case.py')}
   exec(compile(ast.Module(body=tree.body[start:stop],type_ignores=[]),'<source-config>','exec'),ns);return ns['WCOL_RTL']
  with patch.dict(os.environ,{'OT_QWEN_HEAD_PREP':'0','OT_QWEN_STATUS_OBS':'0','OT_QWEN_FAULT_FACE':'0'}):self.assertEqual(config(before),config(after))
if __name__=='__main__':unittest.main(verbosity=2)
