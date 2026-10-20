import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name('native_audit_indexed_private.py');s=importlib.util.spec_from_file_location('private',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def js(n):return {'modules':{'gold':{'netnames':n}}}
class Spelling(unittest.TestCase):
 def test_generate_and_offset(self):
  t=m.signal_table(js({'u.g[0].v':{'bits':[11,12,13],'offset':24}}))
  self.assertEqual(t['u.g[0].v[26]'],dict(wire='u.g[0].v',index=26,bit=13,spelling='\\u.g[0].v [26]'))
  self.assertNotIn('u.g[0].v[23]',t)
 def test_reverse_range(self):
  t=m.signal_table(js({'u.g[3].v':{'bits':[31,32,33],'offset':5,'upto':1}}))
  self.assertEqual([t[f'u.g[3].v[{i}]']['bit'] for i in [5,6,7]],[33,32,31])
 def test_literal_scalar_brackets(self):
  t=m.signal_table(js({'u.g[0].v[26]':{'bits':[44]}}));self.assertEqual(t['u.g[0].v[26]']['spelling'],'\\u.g[0].v[26]')
 def test_ambiguous_alias_rejected(self):
  with self.assertRaisesRegex(ValueError,'ambiguous'):
   m.signal_table(js({'x':{'bits':[10,11]},'x[0]':{'bits':[99]}}))
 def test_observations_preserved_and_wrong_index_rejected(self):
  n=js({'u.g[0].v':{'bits':[1,2],'offset':25}})
  src='cd gold\nconnect -set S__p u.g[0].v[26]\ncd\ncd gate\nconnect -set S__p 1\'0\n'
  out,rows=m.rewrite(src,n);self.assertEqual(len(rows),1);self.assertIn('\\u.g[0].v [26]',out);self.assertEqual(out.count('connect -set'),2)
  with self.assertRaisesRegex(ValueError,'missing exact'):
   m.rewrite(src.replace('v[26]','v[27]'),n)
 def test_non_gold_and_missing_rejected(self):
  with self.assertRaisesRegex(ValueError,'non-gold'):m.rewrite('cd gate\nconnect -set S__p x\n',js({'x':{'bits':[1]}}))
if __name__=='__main__':unittest.main()
