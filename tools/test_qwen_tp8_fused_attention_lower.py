import json
import unittest
from pathlib import Path
from unittest.mock import patch

import hdc_qwen_fullshape_isa_w12 as ISA
from qwen_tp8_native_dispatch_audit import audit
from qwen_tp8_fused_attention_lower import lower

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/arch/qwen_tp8_native_dispatch_1014'


class LoweringTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((DATA / 'program_profile.json').read_text())
        self.image = DATA / 'program.hex'

    def test_exact_retained_bits_and_segment_addresses(self):
        candidate = lower(self.profile, self.image)
        self.assertEqual(candidate['program_words'], 23)
        for old, new in candidate['original_to_candidate_pc'].items():
            if old not in (11, 16):
                self.assertEqual(candidate['program_hex'][new], self.profile['program_hex'][old])
        old = [ISA.decode_descriptor(int(w, 16)) for w in self.profile['descriptor_hex']]
        new = [ISA.decode_descriptor(int(w, 16)) for w in candidate['descriptor_hex']]
        self.assertEqual([d['program_base'] for d in new], [0, 14, 21])
        for a, b in zip(old, new):
            for field in ('kind', 'vm_word', 'words', 'row0'):
                self.assertEqual(a[field], b[field])
        request = ISA.decode_instruction(int(candidate['program_hex'][11], 16))
        self.assertEqual(request['me_obase']*16, 50672)
        self.assertEqual(request['me_nout'], 512)
        self.assertEqual(request['me_xbase'], 13696)
        following = ISA.decode_instruction(int(candidate['program_hex'][12], 16))
        self.assertEqual(following['barrier'], 1)
        self.assertEqual(following['chase'], 0)

    def test_later_consumer_of_removed_raw_attention_is_refused(self):
        audited = audit(self.profile, self.image)
        audited['instructions'][16]['encoded_fields']['me_xbase'] = self.profile['vm_map']['ATT']
        with patch('qwen_tp8_fused_attention_lower.audit', return_value=audited):
            with self.assertRaisesRegex(ValueError, 'PC16 ROM_X_read aliases.*ATT'):
                lower(self.profile, self.image)

    def test_later_sfu_consumer_of_removed_denominator_is_refused(self):
        audited = audit(self.profile, self.image)
        audited['instructions'][20]['encoded_fields']['a_base'] = self.profile['vm_map']['Z']
        with patch('qwen_tp8_fused_attention_lower.audit', return_value=audited):
            with self.assertRaisesRegex(ValueError, 'PC20 read_a aliases.*Z'):
                lower(self.profile, self.image)


if __name__ == '__main__':
    unittest.main()
