import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('combined_launcher', ROOT/'tools/qwen_rom_combined_launch.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CombinedLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in (m.DRIVER, m.CONTEXT, m.CORRECTED_SERVICE, m.CANONICAL_SERVICE, 'selected/adapter.sv', 'selected/cdc.sv', 'selected/top.sv', 'selected/binding.cpp'):
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(name)
        self.binary = self.root/'combined'
        self.binary.write_bytes(b'control binary identity only')
        self.oldsha = m.CORRECTED_SHA
        m.CORRECTED_SHA = m.sha(self.root/m.CORRECTED_SERVICE)
        self.addCleanup(setattr, m, 'CORRECTED_SHA', self.oldsha)
        self.book = {
            'schema': 'opentallas.qwen-rom-combined-driver.v1',
            'geometry': {'tp': 4, 'groups': 6144, 'sw': 64, 'nw': 18}, 'real_mem': True,
            'source_sha256': {name: m.sha(self.root/name) for name in
                              (m.DRIVER, m.CONTEXT, m.CORRECTED_SERVICE, m.CANONICAL_SERVICE, 'selected/adapter.sv', 'selected/cdc.sv', 'selected/top.sv', 'selected/binding.cpp')},
            'top_source': 'selected/top.sv', 'binding_source': 'selected/binding.cpp',
            'memory_service_source': 'selected/adapter.sv', 'crossing_sources': ['selected/cdc.sv'],
            'near_hbm_enabled': False,
            'clocks': {'core': {'period_fs': 834000, 'first_rise_fs': 417000, 'port': 'clk'},
                       'service': {'period_fs': 1024000, 'first_rise_fs': 300000, 'port': 'hclk'}},
            'memory_model_clk_ps': 1024, 'executable': str(self.binary),
            'executable_sha256': m.sha(self.binary), 'driver_abi': 'combined-driver-v1'}

    def test_source_selection_positive(self):
        # Baseline adapter/CDC needs no reduced-near-service pin or new schema.
        del self.book['source_sha256'][m.CORRECTED_SERVICE]
        del self.book['schema']
        del self.book['driver_abi']
        self.assertEqual(m.validate_selection(self.book, self.root), self.binary)

    def test_wrong_geometry_and_service_fail_closed(self):
        for key, value in [('groups', 4), ('sw', 1024), ('tp', 2), ('nw', 16)]:
            b = copy.deepcopy(self.book);b['geometry'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate_selection(b, self.root)
        b = copy.deepcopy(self.book);b['near_hbm_enabled'] = True;b['source_sha256'][m.CORRECTED_SERVICE] = '0'*64
        with self.assertRaisesRegex(ValueError, 'corrected'):
            m.validate_selection(b, self.root)

    def test_clock_alias_mismatch_zero_and_no_compiled_consumer(self):
        for patch in ('alias', 'period', 'phase', 'model', 'consumer', 'top', 'binding'):
            b = copy.deepcopy(self.book)
            if patch == 'alias': b['clocks']['service']['port'] = 'clk'
            if patch == 'period': b['clocks']['core']['period_fs'] = 0
            if patch == 'phase': b['clocks']['core']['first_rise_fs'] = 0
            if patch == 'model': b['memory_model_clk_ps'] = 833
            if patch == 'consumer': b['driver_abi'] = 'old_reduced_context_driver'
            if patch == 'top': b['top_source'] = m.CORRECTED_SERVICE
            if patch == 'binding': b['binding_source'] = m.DRIVER
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                m.validate_selection(b, self.root)

    def test_changed_executable_and_source(self):
        self.binary.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'executable'):
            m.validate_selection(self.book, self.root)
        self.book['executable_sha256'] = m.sha(self.binary)
        (self.root/'selected/top.sv').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            m.validate_selection(self.book, self.root)

    def test_literal_stage_list_and_layer_bounds(self):
        directories = [self.root/f'die{r}' for r in range(4)]
        for d in directories:d.mkdir()
        paths = ' '.join(map(str, directories))
        p = self.root/'stages.txt';p.write_text(f'E {paths} 0\nL0 {paths} 1\nL1 {paths} 1\n')
        self.assertEqual(m.layers_from_stages(p), [0, 1])
        for text in (f'E {paths} 0\nL1 {paths} 1\n', f'E {paths} 0\nL0 {paths} 2\n',
                     f'E {directories[0]}\nL0 {paths} 1\n'):
            p.write_text(text)
            with self.assertRaises(ValueError):m.layers_from_stages(p)

    def test_actual_driver_controls_compile_and_run(self):
        exe = self.root/'driver-controls'
        subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(ROOT/'tools/runtime/qwen_combined/combined_driver_test.cpp'), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], check=True, text=True, capture_output=True)
        self.assertIn('PASS 58 driver controls', result.stdout)


if __name__ == '__main__':unittest.main()
