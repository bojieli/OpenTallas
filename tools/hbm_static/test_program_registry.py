"""Contract tests for actual native target dispatch and raw256 host lowering."""
import copy
import unittest
from host_program_image import build
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

    def test_old_registered_profile_unchanged(self):
        spec = fixture(); spec['required_targets'].pop(); spec['images'].pop()
        image = build(spec)
        self.assertEqual(image['schema'], 'opentallas.hbm.actual-host-program-image.v1')
        self.assertEqual(len(image['axi_writes']), 45)
        self.assertEqual(image['axi_writes'][-1]['address'], 0xc10)


if __name__ == '__main__': unittest.main()
