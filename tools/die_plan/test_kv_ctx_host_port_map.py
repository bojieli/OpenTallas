"""The restored host must retain die-bundle translation for HSL rewires."""
import copy
import importlib.util
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location('kv_ctx_source_event', Path(__file__).with_name('kv_ctx_source_event.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class RestoredHostPortMap(unittest.TestCase):
    def test_rewire_bundle_slices_survive_module_replacement(self):
        old = {'masters': {'host': {'module': 'old_host', 'bundles': {
            'chf0': {'die_ports': ['chf0', 'chf1', 'chf2', 'chf3'],
                     'die_bits': 1164, 'rtl_bits': 1164, 'rtl_ports': ['chain_f']}}}}}
        parent = 'output [1163:0] chain_f;\n'
        result = _mod.host_port_map(old, parent, 'old_host', 'restored_host')
        # Production apply_rewires keys these translations by the current module.
        aliases = {v['module']: v['bundles'] for v in result['masters'].values()}
        self.assertEqual(aliases['restored_host'], aliases['old_host'])
        self.assertEqual(old['masters']['host']['module'], 'old_host')
        self.assertEqual(len(old['masters']), 1)
        for broken in ('output [1162:0] chain_f;\n', 'output [1163:0] wrong;\n'):
            with self.assertRaises(ValueError):
                _mod.host_port_map(old, broken, 'old_host', 'restored_host')

    def test_missing_or_ambiguous_old_module_refuses(self):
        for masters in ({}, {'one': {'module': 'old'}, 'two': {'module': 'old'}}):
            with self.assertRaises(ValueError):
                _mod.host_port_map({'masters': masters}, '', 'old', 'new')


if __name__ == '__main__':
    unittest.main()
