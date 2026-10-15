"""Contract tests for actual native target dispatch and raw256 host lowering."""
import copy
import unittest
from host_program_image import build, raw_fragment
from program_registry import target_contract


def fixture():
    images = []
    for target, width in enumerate((202, 147, 187, 147)):
        images.append(dict(target=target, PCW=10, payload_bits=width, programme=dict(
            start=dict(base=0, limit=1, loops=1), configuration_writes=[
                dict(addr=0, data=f'{0xc7a1 << 240:064x}')])) )
    images.append(dict(target=120, encoding='raw_control256', programme=dict(
        start=dict(base=2, limit=5, loops=1), configuration_writes=[
            dict(addr=ordinal, data=f'{(1 << 237) | ordinal:064x}') for ordinal in range(2, 6)])))
    return dict(kernel='actual_native_raw256_transport_contract', required_targets=[0, 1, 2, 3, 120], images=images)


class RegistryTest(unittest.TestCase):
    def test_ordered_profile_has_distinct_limit(self):
        image = dict(target=120, encoding='raw_control256', native_profile='slot160_21_ordered_drain5',
                     programme=dict(start=dict(base=0, limit=2091, loops=1),
                       configuration_writes=[dict(addr=pc,data='0') for pc in range(2092)]))
        self.assertEqual(raw_fragment(image)['launch_guard_core_edges'], 1346)
        image['programme']['start']['limit'] = 2574
        with self.assertRaisesRegex(ValueError, 'limit2091'): raw_fragment(image)

    def test_explicit_drain5_profile(self):
        image = dict(target=120, encoding='raw_control256', native_profile='slot160_21_drain5',
                     programme=dict(start=dict(base=0, limit=2574, loops=1),
                       configuration_writes=[dict(addr=pc,data='0') for pc in range(2574)]))
        self.assertEqual(raw_fragment(image)['launch_guard_core_edges'], 1346)
        image['programme']['start']['limit'] = 2569
        with self.assertRaisesRegex(ValueError, 'limit2574'): raw_fragment(image)
        image['programme']['start']['limit'] = 2574
        image['programme']['configuration_writes'][2570]['data'] = '1'
        with self.assertRaisesRegex(ValueError, 'five actual zero'): raw_fragment(image)

    def test_collision_and_unallocated(self):
        self.assertEqual(target_contract(56)['owner'], 'COLL bridge49')
        self.assertEqual(target_contract(52)['payload_bits'], 1536)
        self.assertEqual(target_contract(120)['native_op_pc_bits'], 13)
        with self.assertRaises(ValueError): target_contract(119)

    def test_raw_fullwidth_and_doorbell(self):
        image = build(fixture())
        writes = image['axi_writes']
        frames = []
        for index, write in enumerate(writes):
            if write.get('address') == 0xf20:
                self.assertEqual(write['data'] & 255, 120)
                pieces = writes[index+1:index+9]
                self.assertTrue(all(piece['address'] == 0xf24 for piece in pieces))
                frames.append((write['data'] >> 8, sum(piece['data'] << (32*n) for n, piece in enumerate(pieces))))
        self.assertEqual(frames, [(n, (1 << 237) | n) for n in range(2, 6)])
        self.assertEqual(writes[-2]['idle_core_edges'], 1218)
        self.assertEqual(writes[-1], dict(address=0xc10, data=1))

    def test_raw_faults(self):
        mutations = [
            lambda image: image.update(target=56),
            lambda image: image['programme']['start'].update(base=3),
            lambda image: image['programme']['start'].update(limit=2433),
            lambda image: image['programme']['start'].update(loops=2),
            lambda image: image['programme']['configuration_writes'].pop(),
            lambda image: image['programme']['configuration_writes'][0].update(data=f'{1 << 238:064x}'),
            lambda image: image['programme']['configuration_writes'].append(copy.deepcopy(image['programme']['configuration_writes'][0])),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                spec = fixture(); mutate(spec['images'][-1])
                spec['required_targets'][-1] = spec['images'][-1]['target']
                with self.assertRaises(ValueError): build(spec)

    def test_protected_alias_refused(self):
        spec = fixture(); image = spec['images'][-1]
        image.pop('encoding'); image.update(PCW=10, payload_bits=223)
        with self.assertRaisesRegex(ValueError, 'cannot consume protected'): build(spec)

    def test_fetch_raw224_and_opcode_faults(self):
        spec = fixture(); spec['required_targets'].append(124)
        word = 1 | (2 << 32) | (3 << 192)
        fetch = dict(target=124, encoding='raw_engram_fetch7x32', programme=dict(
            start=dict(base=0, limit=7, loops=1),
            configuration_writes=[dict(addr=0, data=f'{word:064x}')]))
        spec['images'].append(fetch)
        result = build(spec)
        self.assertEqual(result['targets'][-1]['payload_bits'], 224)
        self.assertEqual(result['axi_writes'][-2]['idle_core_edges'], 1218)
        for bad in (word | (1 << 224), 4, 1 << 4):
            bad_spec = copy.deepcopy(spec)
            bad_spec['images'][-1]['programme']['configuration_writes'][0]['data'] = f'{bad:064x}'
            with self.assertRaises(ValueError): build(bad_spec)
        for change in (dict(base=1), dict(limit=897), dict(loops=2)):
            bad_spec = copy.deepcopy(spec)
            bad_spec['images'][-1]['programme']['start'].update(change)
            with self.assertRaises(ValueError): build(bad_spec)

    def test_fetch_disable_fragment_has_no_fake_programme(self):
        fragment = raw_fragment(dict(target=124, encoding='raw_engram_fetch7x32', programme=dict(disabled=True)))
        self.assertEqual(fragment['axi_writes'], [dict(address=0xf20, data=124), dict(address=0xf28, data=0), dict(address=0xf2c, data=0)])
        self.assertEqual(fragment['launch_guard_core_edges'], 2)
        with self.assertRaises(ValueError):
            raw_fragment(dict(target=120, encoding='raw_control256', programme=dict(disabled=True)))

    def test_sw_quant_requires_versioned_real_ports(self):
        spec = fixture(); spec['required_targets'][-1] = 125
        spec['images'][-1] = dict(target=125, PCW=10, payload_bits=94, programme=dict(
            start=dict(base=0, limit=1, loops=1),
            configuration_writes=[dict(addr=0, data=f'{0xc7a1 << 240:064x}')]))
        with self.assertRaisesRegex(ValueError, 'sw_quant_v2'): build(spec)
        spec['vm_profile'] = 'sw_quant_v2'
        self.assertEqual(build(spec)['targets'][-1]['target'], 125)
        spec['images'][-1]['payload_bits'] = 48
        with self.assertRaises(ValueError): build(spec)

    def test_control256_new_profile_cannot_overwrite_legacy_capacity(self):
        spec = fixture(); image = spec['images'][-1]
        image['programme'] = dict(start=dict(base=0, limit=2569, loops=1),
            configuration_writes=[dict(addr=n, data='0'*64) for n in range(2570)])
        with self.assertRaises(ValueError): raw_fragment(image)
        image['native_profile'] = 'slot160_21'
        fragment = raw_fragment(image)
        self.assertEqual(fragment['launch_guard_core_edges'], 1346)
        self.assertEqual(fragment['target_manifest']['native_banks'], 21)
        with self.assertRaisesRegex(ValueError, 'matching hardware'): build(spec)
        spec['native_target_profiles'] = {'120': 'slot160_21'}
        self.assertEqual(build(spec)['axi_writes'][-2]['idle_core_edges'], 1346)

    def test_old_registered_profile_unchanged(self):
        spec = fixture(); spec['required_targets'].pop(); spec['images'].pop()
        image = build(spec)
        self.assertEqual(image['schema'], 'opentallas.hbm.actual-host-program-image.v1')
        self.assertEqual(len(image['axi_writes']), 45)
        self.assertEqual(image['axi_writes'][-1]['address'], 0xc10)


if __name__ == '__main__': unittest.main()
