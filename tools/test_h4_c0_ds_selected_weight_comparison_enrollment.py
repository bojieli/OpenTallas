import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from h4_c0_ds_selected_weight_comparison_enrollment import SelectedWeightComparisons
from h4_c0_ds_selected_bf16_payload_witness import sha

class EnrollmentTests(unittest.TestCase):
    def fixture(self,root):
        value=np.zeros((1,1),dtype='<f4');rows=[]
        for pc in [115,443,776]:
            for rank in range(96):rows.append(dict(plan=dict(PC=pc,rank=rank,template='controlled_fixture',shape=[1,1]),expected_F32_bits_sha256=hashlib.sha256(value.tobytes()).hexdigest()))
        p=Path(root)/'controlled_fixture.json';p.write_text(json.dumps(rows));return p,rows,value
    def test_complete_actual_observations_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,rows,value=self.fixture(tmp);w=SelectedWeightComparisons(p,reviewed_proof_sha256=sha(p))
            with self.assertRaisesRegex(ValueError,'incomplete'):w.finish()
            for row in rows:w.observe(row['plan'],value)
            self.assertEqual(w.finish()['calls'],288)
            with self.assertRaisesRegex(ValueError,'duplicate'):w.observe(rows[0]['plan'],value)
            with self.assertRaisesRegex(ValueError,'failed'):w.finish()
    def test_mismatch_is_terminal_even_if_correct_values_follow(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,rows,value=self.fixture(tmp);w=SelectedWeightComparisons(p,reviewed_proof_sha256=sha(p))
            with self.assertRaisesRegex(ValueError,'bytes differ'):w.observe(rows[0]['plan'],np.ones((1,1),dtype='<f4'))
            with self.assertRaisesRegex(ValueError,'no retry'):w.observe(rows[0]['plan'],value)
    def test_unreviewed_or_incomplete_reference_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,rows,value=self.fixture(tmp)
            with self.assertRaisesRegex(ValueError,'SHA'):SelectedWeightComparisons(p,reviewed_proof_sha256='wrong')
            p.write_text(json.dumps(rows[:-1]))
            with self.assertRaisesRegex(ValueError,'all288'):SelectedWeightComparisons(p,reviewed_proof_sha256=sha(p))

if __name__=='__main__':unittest.main()
