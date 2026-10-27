import unittest
from su_transport_contract import compare


def plan(*stations):
    return {'partition_types': {'hub': {'internal_stations': list(stations)}}}


def st(**kw):
    return dict(conn='producer.data|consumer', bits=4, regs_um=[[1, 1]], **kw)


class ServiceContract(unittest.TestCase):
    def test_unknown_duty_never_proves_su(self):
        p = plan(st(serial_k=2, bits_parallel=8))
        self.assertFalse(compare(p, p)['existing_su_transport_preserved'])

    def test_burst_conflict_even_when_mean_duty_low(self):
        p = plan(st(serial_k=2, bits_parallel=8))
        r = compare(p, p, {'hub:producer.data|consumer': {'launch_cycles': [0, 1, 1000], 'complete_static_schedule': True}})
        self.assertEqual(r['serializer_service'][0]['status'], 'SERVICE_CONFLICT')
        self.assertFalse(r['existing_su_transport_preserved'])

    def test_complete_static_launches_fit(self):
        p = plan(st(serial_k=2, bits_parallel=8))
        self.assertTrue(compare(p, p, {'hub:producer.data|consumer': {'launch_cycles': [0, 2, 1000], 'complete_static_schedule': True}})['existing_su_transport_preserved'])

    def test_changed_second_copy_detected(self):
        p = plan(st(), st())
        q = plan(st(), st(serial_k=2, bits_parallel=8))
        self.assertEqual(len(compare(p, q)['changes']), 1)

    def test_serialization_adds_pipeline_latency(self):
        r = compare(plan(st()), plan(st(serial_k=4, bits_parallel=4)))
        self.assertEqual(r['changes'][0]['candidate'][0][3], 4)

    def test_unmodeled_payload_refused(self):
        with self.assertRaises(ValueError):
            compare(plan(st()), plan(st(serial_k=2, bits_parallel=9)))


if __name__ == '__main__':
    unittest.main()
