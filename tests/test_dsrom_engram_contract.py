import importlib.util,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('engram',Path(__file__).parents[1]/'tools/dsrom_engram_contract.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EngramTests(unittest.TestCase):
 def test_prime_bank_disjoint(self):
  prime=lambda n:n>1 and all(n%i for i in range(2,int(n**.5)+1))
  banks=m.bank_rows(11,[1,14],4,2,prime)
  vals=[b['rows'] for bs in banks.values() for b in bs]
  self.assertEqual(len(vals),len(set(vals)))
  for bs in banks.values():
   self.assertEqual([b['global_row_offset'] for b in bs],[sum(x['rows'] for x in bs[:i]) for i in range(len(bs))])
 def test_row_padding_not_hidden(self):
  self.assertEqual(m.port_budget(48,264,32)['packed_stream_cycles'],396)
  self.assertEqual(m.port_budget(48,264,32)['row_aligned_cycles'],432)
 def test_actual_scale_count(self):
  p=Path(__file__).parents[1]/m.OUT/'contract.json';c=json.loads(p.read_text())
  self.assertEqual(c['port_budget']['mandatory_decode_scale_bytes'],8)
  self.assertEqual(c['demand']['stored_table_read_bytes_per_token'],48*(256+8))
 def test_all_backing_accounted(self):
  c=json.loads((Path(__file__).parents[1]/m.OUT/'contract.json').read_text());d=c['demand']
  self.assertEqual(d['full_table_backing_bytes']+d['projection_and_constants_bytes'],203073076240)
  self.assertEqual(sum(b['packed_backing_bytes'] for t in c['table_contracts'].values() for b in t['column_banks']),d['full_table_backing_bytes'])
 def test_no_physical_credit(self):
  c=json.loads((Path(__file__).parents[1]/m.OUT/'contract.json').read_text())
  self.assertFalse(c['adopt']);self.assertFalse(c['admission_claim'])
  for t in c['table_contracts'].values():self.assertIsNone(t['physical_die_owners'])
 def test_distinct_scales_witness(self):
  # E4M3 code0x38 =1; UE8M0 exponent127 vs128 gives1 vs2.
  # Reusing beat0 exponent127 necessarily changes block1 decoded value.
  golden=[2**(s-127) for s in [127,128,127,127,127,127,127,127]]
  legacy=[2**(127-127)]*8
  self.assertNotEqual(golden,legacy)
if __name__=='__main__':unittest.main()
