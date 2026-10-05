import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('binding', Path(__file__).resolve().parents[1]
                                             / 'tools/dsrom_reduced_token_binding.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


class BindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.name = 'sys_fixture'
        self.img = self.root / 'cfg_sys_fixture'
        self.img.mkdir()
        prep = dict(config_name=self.name, config=dict(users=3, plen=2, ngen=2),
                    golden_prompts=[[10, 11], [20, 21]], golden_generated=[[12, 13], [22, 23]],
                    isa_pipeline=[dict(logits_bit_exact_every_step=True, argmax_and_value_every_step=True)])
        (self.root / 'prep_sys_fixture.json').write_text(json.dumps(prep))
        (self.root / 'svh_sys_fixture.svh').write_text('localparam integer NODES=2, NPR=2;')
        (self.img / 'prompts.hex').write_text('\n'.join(f'{x:04x}' for x in [10,11]+[0]*6+[20,21]+[0]*6))
        (self.img / 'expect_tokens.hex').write_text('\n'.join(f'{x:04x}' for x in [99,12,13]+[0]*13+[88,22,23]+[0]*13))
        for s in range(2):
            (self.img / f'prog_stage{s:02d}.hex').write_text(f'{(1<<1400)+s:x}\n')
            (self.img / f'qlist_stage{s:02d}.hex').write_text('0\n')

    def load(self):
        return binding.CachedReducedTokenBinding(self.root, self.name)

    def test_prompt_namespace_and_verbatim_program(self):
        b = self.load()
        self.assertEqual([b.input_token(u, 1) for u in range(3)], [11,21,11])
        self.assertEqual(b.expected_output(1, 0), 88)
        self.assertEqual(b.program(1), ((1<<1400)+1,))
        self.assertEqual(b.qlist_path(1), self.img / 'qlist_stage01.hex')

    def test_generated_input_requires_actual_matching_completion(self):
        b = self.load()
        for completion in [None, (1,1,12), (0,0,12), (0,1,-1), (0,1,65536)]:
            with self.assertRaises(ValueError):
                b.input_token(0, 2, previous_completion=completion)
        # Hardware feedback differing from the golden must remain visible.
        self.assertEqual(b.input_token(0, 2, previous_completion=(0,1,123)), 123)
        self.assertEqual(b.expected_output(0, 2), 13)

    def test_source_mismatch_and_missing_program_refuse(self):
        (self.img / 'prompts.hex').write_text('0\n'*16)
        with self.assertRaisesRegex(ValueError, 'prompt image'):
            self.load()

    def test_bounds_and_sparse_hex_refuse(self):
        b = self.load()
        for user,pos in [(3,0),(0,3),(-1,0),(True,0)]:
            with self.assertRaises(ValueError):
                b.input_token(user,pos)
        with self.assertRaises(ValueError):
            b.program(2)
        (self.img / 'prog_stage00.hex').write_text('@10\n0\n')
        with self.assertRaisesRegex(ValueError, 'non-dense'):
            self.load()


if __name__ == '__main__':
    unittest.main()
