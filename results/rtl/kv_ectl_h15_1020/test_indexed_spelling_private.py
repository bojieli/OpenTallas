import importlib.util
from pathlib import Path
import unittest
import tempfile,subprocess,json
p=Path(__file__).with_name('native_audit_indexed_private.py');s=importlib.util.spec_from_file_location('private',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def js(n):return {'modules':{'gold':{'netnames':n}}}
class Spelling(unittest.TestCase):
 def test_generate_and_offset(self):
  t=m.signal_table(js({'u.g[0].v':{'bits':[11,12,13],'offset':24}}))
  self.assertEqual(t['u.g[0].v[26]'],dict(wire='u.g[0].v',index=26,rtlil_bitindex=2,bit=13,spelling='\\u.g[0].v[2]'))
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
  out,rows=m.rewrite(src,n);self.assertEqual(len(rows),1);self.assertIn('\\u.g[0].v[1]',out);self.assertEqual(out.count('connect -set'),2)
  with self.assertRaisesRegex(ValueError,'missing exact'):
   m.rewrite(src.replace('v[26]','v[27]'),n)
 def test_non_gold_and_missing_rejected(self):
  with self.assertRaisesRegex(ValueError,'non-gold'):m.rewrite('cd gate\nconnect -set S__p x\n',js({'x':{'bits':[1]}}))
class ActualYosys(unittest.TestCase):
 def test_exact_json_bits_offsets_reverse_and_literal_array(self):
  y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
  cases=[('[26:24]','u.g[0].v',26),('[5:7]','u.g[3].r',5),('','u.g[1].scalar[26]',None),('[4:4]','u.g[2].one',4)]
  for rng,wire,logical_index in cases:
   with tempfile.TemporaryDirectory(prefix='native-index-test-') as d:
    w=Path(d);w.joinpath('v.v').write_text(f'module gold(input {rng} \\{wire} ,output out); assign out=~&\\{wire} ; endmodule\n')
    subprocess.run([str(y),'-Q','-T','-p','read_verilog v.v; write_json gold.json'],cwd=w,check=True,capture_output=True)
    j=json.loads(w.joinpath('gold.json').read_text());key=wire if logical_index is None else f'{wire}[{logical_index}]';row=m.signal_table(j)[key]
    src='read_json gold.json\ncd gold\nadd -wire S__p 1\nconnect -set S__p '+key+'\ncd\nwrite_json out.json\n'
    repaired,rows=m.rewrite(src,j);w.joinpath('t.ys').write_text(repaired)
    subprocess.run([str(y),'-Q','-T','-s','t.ys'],cwd=w,check=True,capture_output=True)
    got=json.loads(w.joinpath('out.json').read_text())['modules']['gold']['netnames']['S__p']['bits']
    self.assertEqual(got,[row['bit']],(key,row,got))
    # Causal bit perturbation: adjacent physical bit gives a different actual JSON bit.
    n=j['modules']['gold']['netnames'][wire]
    if len(n['bits'])>1:
     wrong=(row['rtlil_bitindex']+1)%len(n['bits']);w.joinpath('bad.ys').write_text(repaired.replace(row['spelling'],'\\'+wire+f'[{wrong}]').replace('out.json','bad.json'))
     subprocess.run([str(y),'-Q','-T','-s','bad.ys'],cwd=w,check=True,capture_output=True)
     bad=json.loads(w.joinpath('bad.json').read_text())['modules']['gold']['netnames']['S__p']['bits'];self.assertNotEqual(bad,[row['bit']])
if __name__=='__main__':unittest.main()
