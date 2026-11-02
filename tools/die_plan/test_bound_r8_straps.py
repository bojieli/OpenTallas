"""Negative controls for default bound R8 metadata projection and instance ownership."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from bound_r8_straps import declared, project


class BoundR8(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.kr = dict(plan_type='T', bound_type='T', bind_out=str(self.d), instances=['a'],
                       bound_only_pins=[dict(port='strap_r8pad_x', dir='input', width=4)])
        self.m = dict(types={'T': {'strap_r8pad_x': dict(width=4, kind='r8pad_strap')}},
                      instances={'a': {'strap_r8pad_x': dict(width=4, value=2, kind='r8pad_strap')},
                                 'foreign': {'strap_r8pad_x': dict(width=99, value=999, kind='r8pad_strap')}})
        self.audit = dict(verdict='PASS', checked_bits=4, errors=[])
        self.raw = dict(partition_types={'T': {}}, partitions=[dict(name='a', type='T')])
        self.save()

    def save(self):
        for name, obj in [('kit_rtl.json', self.kr), ('bind_parent_id_straps.json', self.m),
                          ('bind_r8pad_strap_audit.json', self.audit)]:
            (self.d/name).write_text(json.dumps(obj))

    def reject(self):
        self.save()
        with self.assertRaises((ValueError, FileNotFoundError)):
            declared(self.d/'kit_rtl.json')

    def test_foreign_same_name_does_not_supply_or_poison_owning_tie(self):
        old = copy.deepcopy(self.raw)
        p = project(self.raw, {'T': str(self.d/'kit_rtl.f')})
        self.assertEqual(self.raw, old)
        self.assertEqual(p['partition_types']['T']['count_straps'], [dict(name='strap_r8pad_x', width=4)])

    def test_foreign_valid_tie_cannot_replace_missing_owner(self):
        del self.m['instances']['a']['strap_r8pad_x']; self.reject()

    def test_missing_audit(self):
        (self.d/'bind_r8pad_strap_audit.json').unlink()
        with self.assertRaises(FileNotFoundError): declared(self.d/'kit_rtl.json')

    def test_invalid_audit(self):
        for change in [dict(verdict='FAIL'), dict(errors=['bad tie']), dict(checked_bits=0)]:
            with self.subTest(change=change):
                self.audit = dict(verdict='PASS', checked_bits=4, errors=[]); self.audit.update(change); self.reject()

    def test_wrong_width_or_direction(self):
        self.m['types']['T']['strap_r8pad_x']['width'] = 3; self.reject()
        self.m['types']['T']['strap_r8pad_x']['width'] = 4
        self.kr['bound_only_pins'][0]['dir'] = 'output'; self.reject()

    def test_mismatched_inventory(self):
        del self.m['types']['T']['strap_r8pad_x']; self.reject()

    def test_extra_bound_r8(self):
        self.kr['bound_only_pins'].append(dict(port='strap_r8pad_extra', dir='input', width=4)); self.reject()

    def test_invalid_owner_value(self):
        self.m['instances']['a']['strap_r8pad_x']['value'] = 16; self.reject()

    def test_wrong_plan_instance_type(self):
        self.raw['partitions'][0]['type'] = 'Other'
        with self.assertRaises(ValueError): project(self.raw, {'T': str(self.d/'kit_rtl.f')})

    def test_missing_or_duplicate_owner_identity(self):
        for owners in [[], ['a', 'a']]:
            self.kr['instances'] = owners; self.reject()

    def test_strap_free_legacy_without_manifest(self):
        self.kr['bound_only_pins'] = []; self.save()
        (self.d/'bind_parent_id_straps.json').unlink()
        self.assertEqual(declared(self.d/'kit_rtl.json'), [])

    def test_r8_port_without_manifest_rejected(self):
        (self.d/'bind_parent_id_straps.json').unlink()
        with self.assertRaises(ValueError): declared(self.d/'kit_rtl.json')

    def test_native_station_manifest_without_bind_metadata_passes_through(self):
        self.kr = dict(bound_module='native_bound', files=['native.sv'])
        self.save()
        self.assertIs(project(self.raw, {'T': str(self.d/'kit_rtl.f')}), self.raw)

    def test_r8_input_without_bind_authority_rejected(self):
        del self.kr['bind_out']
        self.save()
        with self.assertRaisesRegex(ValueError, 'bind authority'):
            declared(self.d/'kit_rtl.json')

    def test_plain_native_filelist_without_metadata_passes_through(self):
        (self.d/'kit_rtl.json').unlink()
        self.assertIs(project(self.raw, {'T': str(self.d/'native.f')}), self.raw)


if __name__ == '__main__': unittest.main()
