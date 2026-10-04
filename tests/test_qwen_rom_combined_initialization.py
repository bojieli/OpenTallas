import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

class InitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old=sys.path[:]
        try:
            sys.path.insert(0,str(ROOT/'tools'))
            spec=importlib.util.spec_from_file_location('init_emitter',ROOT/'tools/qwen_rom_combined_runtime_emit_initialized.py')
            cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
        finally:sys.path[:]=old

    def test_actual_all_model_initial_eval_precedes_first_image_and_payload(self):
        old=self.module.BASE_EMIT(ROOT)
        src=self.module.emit(ROOT)
        load='for (int d = 0; d < D; d++) load_images(mem[d], stages[0].dir[d]);'
        self.assertLess(old.index(load),old.index('Vcoll coll(&cctx, "coll");'))
        start=src.index('// Complete Verilator initial blocks')
        end=src.index(load)
        block=src[start:end]
        for call in ('die[d]->eval();','coll.eval();','hbm[d]->eval();','fab[d]->eval();'):
            self.assertIn(call,block)
        self.assertLess(block.index('tile->rst_n=0'),block.index('die[d]->eval();'))
        self.assertNotIn('=1;',block)
        self.assertLess(end,src.index('rm_vm(r)[i] ='))
        self.assertLess(end,src.index('rm_embed_codes(r)['))
        self.assertEqual(src.count(load),1)
        # Initial-eval never modifies released payload encoder/readback code.
        self.assertEqual(src[src.index('static int f32_e4m3'):src.index('struct DieMem')],
                         old[old.index('static int f32_e4m3'):old.index('struct DieMem')])

    def test_missing_or_ambiguous_real_source_anchor_refuses(self):
        src=self.module.BASE_EMIT(ROOT)
        anchor='    Vcoll coll(&cctx, "coll");'
        for mutant in (src.replace(anchor,''),src+anchor):
            with self.assertRaises(ValueError):self.module.initialize_source(mutant)

    def test_initializer_is_single_application_and_original_unchanged(self):
        src=self.module.emit(ROOT)
        with self.assertRaises(ValueError):self.module.initialize_source(src)
        self.assertNotIn('INITIALIZATION_ABI',self.module.BASE_EMIT(ROOT))

if __name__=='__main__':unittest.main()
