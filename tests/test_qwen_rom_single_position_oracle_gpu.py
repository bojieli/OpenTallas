import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('single_position_oracle', ROOT/'tools/qwen_rom_single_position_oracle_gpu.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SinglePositionInputs(unittest.TestCase):
    def book(self):
        return dict(position=4095, token=1165,
                    history={f'L{n}_die{d}':{} for n in range(36) for d in range(4)})

    def test_full_actual_input_inventory(self):
        book = self.book()
        self.assertIs(module.validate_history(book,4095,1165),book['history'])

    def test_partial_reference_cannot_be_history(self):
        book = self.book()
        book['history'] = {k:v for k,v in book['history'].items() if int(k.split('_')[0][1:])<3}
        with self.assertRaisesRegex(ValueError,'144'):
            module.validate_history(book,4095,1165)

    def test_wrong_pending_position_and_token_rejected(self):
        for position, token in ((8191,1165),(4095,24)):
            with self.assertRaisesRegex(ValueError,'position/token'):
                module.validate_history(self.book(),position,token)

    def test_extra_or_missing_rank_rejected(self):
        book = self.book()
        book['history']['L35_die4'] = book['history'].pop('L35_die3')
        with self.assertRaisesRegex(ValueError,'144'):
            module.validate_history(book,4095,1165)
