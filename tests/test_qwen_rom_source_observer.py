"""Passive observer preparation and deliberately fabricated native hooks only."""
import gzip,json,pathlib,sys,tempfile,unittest,subprocess,os,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_source_observer_prepare as P
import qwen_rom_source_observer_replay as R
import qwen_rom_source_release_export as E
from qwen_rom_program_identity import decoded,sha
from qwen_rom_kv_launch_readiness import FIELDS
from qwen_rom_program_kv_journal import me_fields
from qwen_rom_accepted_stage_journal import DispatchJournal
from qwen_rom_persistent_kv_g0 import Owner
from hdc_qwen_fullshape_isa_w12 import decode_instruction
class ObserverTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.bundle=json.loads(gzip.decompress((P.ROOT/'results/uarch/qwen_rom_program_identity_20261002/retained-reproduction-final.json.gz').read_bytes()))
 def raw(self):
  records=[]
  for layer in range(36):
   for rank in range(4):
    files=self.bundle['stages'][f'L{layer}/die{rank}']['files'];g=DispatchJournal(decoded(files['program.hex']),decoded(files['segments.hex']),Owner(0,rank,layer,0),0,0);edge=0
    records.append(f'B 0 {layer} {rank} 7')
    for i,base in enumerate(g.bases):
     records.append(f'S {edge} {layer} {rank} {i} {base} {g.words[i]:016x}');edge+=1
     end=g.bases[i+1] if i+1<len(g.bases) else len(g.stage.words)
     for pc in g.stage.expected:
      if not base<=pc<end:continue
      word=g.stage.words[pc];f=decode_instruction(word)
      line=f'I {edge} {layer} {rank} {i} {base} {pc-base} {f["unit"]}'
      if f['unit']==1:line+=' '+' '.join(str(me_fields(word,0,0)[n]) for n,w in FIELDS)
      records.append(line)
      for a in sorted(g.stage.producer.expected.get(pc,set())):records.append(f'W {edge} {layer} {rank} {a} 00000000')
      edge+=1
     records.append(f'D {edge} {layer} {rank} {i} {base} {g.words[i]:016x}');edge+=1
    records.append(f'B {edge} {layer} {rank} 7')
    for a in sorted(a for aa in g.stage.producer.expected.values() for a in aa):records.append(f'K {edge} {layer} {rank} {a} 00000000')
  return '\n'.join(records)+'\n'
 def test_prepare_has_no_build(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'prep';r=P.prepare(p);self.assertFalse(r['build_launched']);self.assertFalse(r['default_enabled']);s=(p/'qwen_rom_rt_observed.cpp').read_text();self.assertIn('observer.snapshot',s);self.assertIn('observer.write(edges-1',s);self.assertIn('observer.read(edges,cur,d,i,g,a',s)
 def test_exclusive_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(FileExistsError):P.prepare(pathlib.Path(td))
 def test_missing_anchor_rejected(self):
  with self.assertRaises(ValueError):P.once('no source anchor','core.issue','replacement')
 def test_all144_fixture_rows(self):
  r=R.replay(self.bundle,self.raw());self.assertEqual(len(r['states']),144);self.assertFalse(r['SMIN6_plus55_physical_transfer'])
 def test_missing_actual_snapshot_rejected(self):
  raw='\n'.join(l for l in self.raw().splitlines() if not l.startswith('K '))
  with self.assertRaisesRegex(ValueError,'state journal'):R.replay(self.bundle,raw)
 def test_missing_actual_write_rejected(self):
  raw=self.raw();line=next(l for l in raw.splitlines() if l.startswith('W '));raw=raw.replace(line+'\n','',1)
  with self.assertRaisesRegex(ValueError,'incomplete producer'):R.replay(self.bundle,raw)
 def test_snapshot_substitution_rejected(self):
  raw=self.raw();line=next(l for l in raw.splitlines() if l.startswith('K '));raw=raw.replace(line,line[:-8]+'3f800000',1)
  with self.assertRaisesRegex(ValueError,'snapshot differs'):R.replay(self.bundle,raw)
 def test_actual_descriptor_mutant_rejected(self):
  raw=self.raw();line=next(l for l in raw.splitlines() if l.startswith('S '));raw=raw.replace(line,line[:-16]+'0000000000000000',1)
  with self.assertRaisesRegex(ValueError,'descriptor dispatch'):R.replay(self.bundle,raw)
 def test_missing_source_controls_rejected(self):
  raw='\n'.join(l for l in self.raw().splitlines() if not l.startswith('B '))
  with self.assertRaisesRegex(ValueError,'source drain'):R.replay(self.bundle,raw)
 def test_busy_completion_rejected(self):
  raw='\n'.join(l[:-1]+'0' if l.startswith('B ') else l for l in self.raw().splitlines())
  with self.assertRaisesRegex(ValueError,'source drain'):R.replay(self.bundle,raw)
 def test_release_export_preserves_unknown_provider(self):
  result=E.export(R.replay(self.bundle,self.raw()))
  self.assertEqual(len(result['releases']),144)
  life=result['releases']['L0/die0']['source_lifetimes']
  self.assertEqual(sum(p['write_count'] for p in life['producer_completions']),512)
  self.assertEqual(len(life['descriptor_events']),10)
  self.assertTrue(all('ib379' in x for x in life['KV_consumer_accepts']))
  self.assertIsNone(result['calendar_overlap_credit_s'])
  self.assertIsNone(result['releases']['L0/die0']['next_layer_prefetch_release'])
  self.assertFalse(result['source_provenance_independently_qualified'])
 def test_release_completion_mutant_rejected(self):
  r=R.replay(self.bundle,self.raw())
  r['states']['L0/die0']['source_lifetimes']['producer_completions'][0]['last_write_edge']+=1
  with self.assertRaisesRegex(ValueError,'completion differs'):E.export(r)
 def test_release_missing_rank_rejected(self):
  r=R.replay(self.bundle,self.raw());del r['states']['L35/die3']
  with self.assertRaisesRegex(ValueError,'all144'):E.export(r)
 def read_raw(self):
  # Fabricated reads of current row; never actual provider ownership evidence.
  records=[]
  words=sorted({(h*512*128*16+d*16)//16 for h in range(2) for d in range(128)} | {(2097152+h*8192*128+d)//16 for h in range(2) for d in range(128)})
  for line in self.raw().splitlines():
   records.append(line);a=line.split()
   if a[0]=='I' and a[7]=='1' and int(a[11]):
    for n,word in enumerate(words):records.append('R '+' '.join(a[1:4])+f' {n//4} {n%4} {word} '+' '.join(['00000000']*16))
  return '\n'.join(records)+'\n'
 def test_source_read_deadlines_all144_fixture(self):
  r=R.replay(self.bundle,iter(self.read_raw().splitlines()),require_reads=True)
  self.assertTrue(all(s['source_lifetimes']['source_read_deadlines_complete'] for s in r['states'].values()))
  result=E.export(r)
  self.assertTrue(result['releases']['L0/die0']['actual_source_read_deadlines_complete'])
  self.assertIsNone(result['releases']['L0/die0']['window_reader_drain_reverse_grant_retire'])
 def test_source_read_return_mutant_rejected(self):
  raw=self.read_raw();line=next(l for l in raw.splitlines() if l.startswith('R '));raw=raw.replace(line,line[:-8]+'3f800000',1)
  with self.assertRaisesRegex(ValueError,'read differs'):R.replay(self.bundle,raw,require_reads=True)
 def test_source_read_missing_deadlines_rejected(self):
  with self.assertRaisesRegex(ValueError,'consumer deadlines required'):R.replay(self.bundle,self.raw(),require_reads=True)
 def test_source_duplicate_read_port_rejected(self):
  raw=self.read_raw();line=next(l for l in raw.splitlines() if l.startswith('R '));raw=raw.replace(line,line+'\n'+line,1)
  with self.assertRaisesRegex(ValueError,'duplicate source read'):R.replay(self.bundle,raw,require_reads=True)
 def test_L0_probe_cannot_export_full_calendar(self):
  raw='\n'.join(l for l in self.read_raw().splitlines() if l.split()[2]=='0')+'\n'
  r=R.replay(self.bundle,raw,require_reads=True,layers=1)
  self.assertEqual(len(r['states']),4);self.assertFalse(r['whole36'])
  with self.assertRaisesRegex(ValueError,'historical replay required'):E.export(r)
 def test_probe_rejects_extra_layers(self):
  with self.assertRaisesRegex(ValueError,'layer4rank identity'):R.replay(self.bundle,self.read_raw(),require_reads=True,layers=1)
 def test_portable_file_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'trace';p.write_bytes(b'actual-source-raw')
   self.assertEqual(R.file_sha256(p),sha(p.read_bytes()))
 def test_native_defaultoff_and_formatter(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);hpp=P.ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer.hpp'
   # Disabled includes must compile without generated Verilator headers.
   (p/'off.cpp').write_text(f'#include "{hpp}"\nint main(){{return 0;}}\n')
   subprocess.run(['g++','-std=c++20','-fsyntax-only',str(p/'off.cpp')],check=True,capture_output=True)
   (p/'Vdie___024root.h').write_text('#pragma once\n')
   (p/'on.cpp').write_text(f'#define QROM_OBSERVER 1\n#include "{hpp}"\nstruct State{{unsigned at(unsigned)const{{return 0;}}}};\nint main(){{QromObserver o;unsigned f[24]={{}};unsigned v[16]={{}};o.read(0,0,0,0,0,0,v);o.dispatch(\'S\',1,0,0,0,0,17);o.issue(2,0,0,0,0,0,1,f);o.write(3,0,0,0,0);o.snapshot(4,0,0,State{{}});}}\n')
   subprocess.run(['g++','-std=c++20','-O2','-I'+str(p),str(p/'on.cpp'),'-o',str(p/'unit')],check=True,capture_output=True)
   env=dict(os.environ,RT_QROM_JOURNAL=str(p/'raw'))
   subprocess.run([str(p/'unit')],env=env,check=True,capture_output=True)
   lines=(p/'raw').read_text().splitlines();self.assertEqual(len(lines),516);self.assertEqual(len(lines[0].split()),23);self.assertEqual(lines[1],'S 1 0 0 0 0 0000000000000011');self.assertEqual(len(lines[2].split()),32)
   self.assertNotEqual(subprocess.run([str(p/'unit')],env=env,capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
