import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('apply_locality', HERE / 'apply_locality.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
CONFIG = '''export DESIGN_NAME = dsdv_gunit_l1f_bf
export DIE_AREA = 0 0 432 172.8
export CORE_AREA = 4.32 4.32 427.68 168.48
export PLACE_DENSITY = 0.4
export VERILOG_DEFINES = -DSYNTHESIS -DOT_GUNIT_BF_M1REG -DOT_GUNIT_BF_C1REG -DOT_GUNIT_BF_SVREG
export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl
export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl
'''

class ConstructorGuards(unittest.TestCase):
    def test_reject_a1_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp); text = CONFIG.replace('dsdv_gunit_l1f_bf', 'dsdv_gunit_l1f_ba1')
            (kit / 'config.mk').write_text(text)
            with self.assertRaisesRegex(ValueError, 'A1 S-face'):
                mod.install(kit, 'a0-sort2cmp', HERE)
            self.assertEqual(list(kit.iterdir()), [kit / 'config.mk'])

    def test_missing_actual_form_define_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing captured form defines'):
            mod.validate(CONFIG.replace('-DOT_GUNIT_BF_SVREG', ''), 'f')

    def test_install_preserves_config_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp); (kit / 'config.mk').write_text(CONFIG)
            for name in ('face_flops.tcl', 'face_flops_release.tcl'):
                (kit / name).write_text('# original existing hook\n')
            first = mod.install(kit, 'f', HERE)
            before = {path.name: path.read_bytes() for path in kit.iterdir()}
            self.assertEqual(mod.install(kit, 'f', HERE), first)
            self.assertEqual(before, {path.name: path.read_bytes() for path in kit.iterdir()})
            self.assertEqual((kit / 'config.mk').read_text(), CONFIG)
            self.assertIn('# original existing hook', (kit / 'face_flops.tcl').read_text())

    def test_lost_pre_dpl_release_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp); (kit / 'config.mk').write_text(CONFIG)
            for name in ('face_flops.tcl', 'face_flops_release.tcl'):
                (kit / name).write_text('# original\n')
            mod.install(kit, 'f', HERE)
            (kit / 'face_flops_release.tcl').write_text('# release accidentally removed\n')
            with self.assertRaisesRegex(ValueError, 'installed hook changed'):
                mod.install(kit, 'f', HERE)

if __name__ == '__main__':
    unittest.main()
