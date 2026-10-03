"""Source-only pin guards; no invented ACK metadata or timing credit."""
import pathlib,sys,json,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import Euclid_installed_RFACK_CDC_contract as E
class ContractTests(unittest.TestCase):
 def test_actual_source_has_no_wire_identity(self):
  r=E.contract();self.assertIsNone(r['wire_ACK_identity']);self.assertFalse(r['production_RF_ACK_CDC_connection']);self.assertFalse(r['hardware_or_rate_admitted'])
 def test_unknowns_never_become_zero(self):
  r=E.contract();self.assertTrue(r['unknown_cycles']);self.assertTrue(all(v is None for v in r['unknown_cycles'].values()))
 def fixture(self,p):
  model=json.loads((E.RECORD/'pre-verification-model-r1.json').read_text())
  for name in list(model['source_pins'])+['tools/uarch_model.py']:
   f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((E.ROOT/name).read_bytes())
  record=p/'record';record.mkdir();(record/'pre-verification-model-r1.json').write_text(json.dumps(model));return record
 def test_fence_RF_or_FIFO_reset_mutation_refused(self):
  for file,old,new in [(E.RF[0],b'ack_valid<=0;',b'ack_valid<=1;'),(E.RF[1],b'rst_n && pending && host_ack_valid',b'rst_n && host_ack_valid'),(E.CDC[0],b'wrn&&rrn',b'wrn')]:
   with self.subTest(file=file),tempfile.TemporaryDirectory() as td:
    p=pathlib.Path(td);record=self.fixture(p);f=p/file;assert old in f.read_bytes();f.write_bytes(f.read_bytes().replace(old,new));root,rec=E.ROOT,E.RECORD
    try:
     E.ROOT=p;E.RECORD=record
     with self.assertRaisesRegex(ValueError,'source pin'):E.contract()
    finally:E.ROOT=root;E.RECORD=rec
 def test_handoff_no_epoch_or_drain_credit(self):
  r=json.loads((E.RECORD/'to-Popper-Dewey-r1.json').read_text());self.assertFalse(r['tagged_ACK_installed']);self.assertFalse(r['actual_owner_switch_or_generation_reuse_admitted']);self.assertFalse(r['calendar_or_rate_admitted']);self.assertIsNone(r['production_common_reset_trace'])
if __name__=='__main__':unittest.main()
