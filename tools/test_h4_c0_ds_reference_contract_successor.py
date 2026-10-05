import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from h4_c0_ds_reference_contract_successor import successor
from h4_c0_ds_whole_reference import sha,payload

class SuccessorTests(unittest.TestCase):
    def setup_reference(self,d):
        old=d/'old.py';new=d/'new.py';old.write_text('pinned source\n');new.write_bytes(old.read_bytes())
        a=np.array([-0.0,1.0],dtype='<f4');np.save(d/'field.npy',a)
        r=d/'historical.json';r.write_text(json.dumps(dict(reference_source_sha256={str(old):sha(old)},expectations=[dict(PC=77,version='route',rank=0,generation=1,field='data',path='field.npy',file_sha256=sha(d/'field.npy'),payload_sha256=payload(a),shape=[2],dtype='<f4')])));return r,old,new
    def test_explicit_same_bytes_keeps_historical_contract_and_field(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);r,old,new=self.setup_reference(d);before=r.read_bytes()
            successor(r,sha(r),{str(old):str(new)},d/'successor.json')
            s=json.loads((d/'successor.json').read_text());self.assertEqual(r.read_bytes(),before)
            self.assertEqual(s['expectations'][0]['payload_sha256'],payload(np.array([-0.0,1.0],dtype='<f4')))
            self.assertEqual(s['reference_source_sha256'][str(new)],sha(old))
    def test_changed_source_or_signed_zero_payload_refused(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);r,old,new=self.setup_reference(d);new.write_text('changed\n')
            with self.assertRaisesRegex(ValueError,'source remap bytes differ'):successor(r,sha(r),{str(old):str(new)},d/'fail.json')
            new.write_bytes(old.read_bytes());np.save(d/'field.npy',np.array([0.0,1.0],dtype='<f4'))
            with self.assertRaisesRegex(ValueError,'comparison payload'):successor(r,sha(r),{str(old):str(new)},d/'fail.json')

if __name__=='__main__':unittest.main()
