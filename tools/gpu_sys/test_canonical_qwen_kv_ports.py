"""KV transport fixtures, not actual HBM/RTL qualification."""
import unittest
from collections import Counter
from types import SimpleNamespace

from tools.gpu_sys.canonical_qwen_kv_ports import KVByteHandlers, KVHandlers, CONTROL_KINDS, CONTROL_ACKS
from tools.gpu_sys.canonical_qwen_transport import DeliverySession, KINDS, KV_KINDS, TransportError, W2PrimaryPort
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA
from tools.h4_qwen_released_kv_delivery import KVStorageDelivery, PhysicalReadWindow


class SectorFixture(W2PrimaryPort):
    def __init__(self):
        self.data = bytearray(range(96))
        self.calls = []
        self.fail = False

    def sector(self, client, address, tag, generation, write=None):
        self.calls.append((client, address, tag, generation, write))
        if self.fail:
            raise TransportError("fixture W2 fault")
        if write is not None:
            self.data[address:address + 32] = write
        return dict(payload=None if write is not None else bytes(self.data[address:address + 32]))


class Authority:
    def __init__(self, port):
        self.port = port
        self.retained = True

    def kv_aperture(self, request, region):
        return 0, 72

    def resolve_kv_sector(self, request, address, we):
        return self.port, 5, address, 0xfedcba98, 3

    def kv_owner_retained(self, request):
        return self.retained

    def kv_payload_address_valid(self, request, address):
        return 0 <= address < 72 and request['key'] == [0, 1, 0]


def request(sequence=0, **fields):
    r = dict(program_sha256=PROGRAM_SHA, source_PC=20, sequence=sequence,
             rank=1, address=0, bytes=1, lease=5, key=[0, 1, 0], addresses=[0])
    r.update(fields)
    return r


class KVTest(unittest.TestCase):
    def fixture(self):
        port = SectorFixture()
        authority = Authority(port)
        return port, authority, KVByteHandlers(authority)

    def test_physical_partial_write_preserves_both_adjacent_sectors(self):
        port, _, kv = self.fixture()
        original = bytes(port.data)
        reply = kv.handlers["kv_state_write"](request(address=30, payload=b"ABCDE"))
        self.assertTrue(reply["visible"])
        self.assertEqual(bytes(port.data[:30]), original[:30])
        self.assertEqual(bytes(port.data[30:35]), b"ABCDE")
        self.assertEqual(bytes(port.data[35:]), original[35:])
        self.assertEqual([(a, w is not None) for _, a, _, _, w in port.calls],
                         [(0, False), (0, True), (32, False), (32, True)])
        self.assertTrue(all((c, t, g) == (5, 0xfedcba98, 3) for c, _, t, g, _ in port.calls))

    def test_aligned_payload_write_requires_actual_write_only(self):
        port, _, kv = self.fixture()
        kv.handlers["kv_state_write"](request(address=32, payload=b"z" * 32))
        self.assertEqual(len(port.calls), 1)
        self.assertEqual(port.calls[0][-1], b"z" * 32)

    def test_read_returns_physical_bytes_in_requested_order(self):
        port, _, kv = self.fixture()
        response = kv.handlers["kv_payload_read"](request(addresses=[37, 29, 32, 29]))
        self.assertEqual(response["payload"], bytes([37, 29, 32, 29]))
        self.assertEqual([x[1] for x in port.calls], [32, 0])

    def test_extent_tail_preserves_actual_padding_bytes(self):
        port, _, kv = self.fixture()
        old = bytes(port.data)
        kv.handlers["kv_state_write"](request(address=68, payload=b"ABCD"))
        self.assertEqual(bytes(port.data[72:]), old[72:])
        self.assertEqual(bytes(port.data[:68]), old[:68])

    def test_fault_retains_pending_and_never_retries(self):
        port, _, kv = self.fixture(); port.fail = True
        with self.assertRaisesRegex(TransportError, "W2 fault"):
            kv.handlers["kv_state_read"](request())
        self.assertIsNotNone(kv.pending)
        self.assertTrue(kv.stopped)
        with self.assertRaisesRegex(TransportError, "no reuse"):
            kv.handlers["kv_state_read"](request())
        self.assertEqual(len(port.calls), 1)

    def test_out_of_extent_rejected_without_port_transaction(self):
        port, _, kv = self.fixture()
        with self.assertRaisesRegex(TransportError, "state aperture"):
            kv.handlers["kv_state_write"](request(address=71, payload=b"XX"))
        self.assertEqual(port.calls, [])

    def test_owner_loss_is_not_success(self):
        _, authority, kv = self.fixture(); authority.retained = False
        with self.assertRaisesRegex(TransportError, "owner not retained"):
            kv.handlers["kv_state_read"](request())

    def test_same_sequence_crosses_rf_native_and_kv(self):
        _, _, kv = self.fixture()
        def base_handler(r):
            return dict(r, accepted=True, fault=False)
        handlers = {k: base_handler for k in KINDS}
        handlers.update({k: base_handler for k in CONTROL_KINDS})
        handlers.update(kv.handlers)
        session = DeliverySession(handlers)
        for seq, kind in enumerate(("source_page_read", "kv_state_read", "native_primitive", "kv_payload_read")):
            response = session.transact(dict(kind=kind, request=request(seq)))
            self.assertEqual(response["sequence"], seq)
        self.assertEqual(session.sequence, 4)

    def test_partial_kv_enrollment_refused(self):
        base = {k: lambda r: r for k in KINDS}
        base[KV_KINDS[0]] = lambda r: r
        with self.assertRaisesRegex(TransportError, "missing simulator handlers"):
            DeliverySession(base)

    def test_all_ten_services_enroll_with_six_existing_one_sequence(self):
        port = SectorFixture()
        calls = []
        def actual_control(kind):
            def invoke(r):
                calls.append((kind, r['sequence']))
                result = dict(r, accepted=True, fault=False)
                result.update({k: True for k in CONTROL_ACKS[kind]})
                if kind == 'kv_stage_write':
                    import hashlib
                    result['payload_sha256'] = hashlib.sha256(r['payload']).hexdigest()
                return result
            return invoke
        services = KVHandlers(Authority(port), {k: actual_control(k) for k in CONTROL_KINDS})
        handlers = {k: lambda r: dict(r, accepted=True, fault=False) for k in KINDS}
        handlers.update(services.handlers)
        self.assertEqual(len(handlers), 16)
        session = DeliverySession(handlers)
        for seq, kind in enumerate(KINDS + KV_KINDS):
            r = request(seq, tag=3, producer_tag=3, stage='SCORES', payload=b'A')
            result = session.transact(dict(kind=kind, request=r))
            self.assertEqual(result['sequence'], seq)
        self.assertEqual(session.sequence, 16)
        self.assertEqual([k for k, _ in calls], list(CONTROL_KINDS))

    def test_missing_real_lifecycle_handlers_refused(self):
        with self.assertRaisesRegex(TransportError, 'seven actual KV lifecycle'):
            KVHandlers(Authority(SectorFixture()), {})

    def test_no_bare_ack_for_final_reader_release(self):
        def bare(r):
            return dict(r, accepted=True, fault=False)
        services = KVHandlers(Authority(SectorFixture()), {k: bare for k in CONTROL_KINDS})
        with self.assertRaisesRegex(TransportError, 'lifecycle completion missing'):
            services.handlers['kv_reader_release'](request())
        self.assertTrue(services.bytes.stopped)
        with self.assertRaisesRegex(TransportError, 'no reuse'):
            services.handlers['kv_state_read'](request())

    def test_control_cannot_mutate_key_to_retag_completion(self):
        def corrupt(r):
            r['key'][0] = 99
            return dict(r, accepted=True, fault=False, writer_retained=True)
        services = KVHandlers(Authority(SectorFixture()), {k: corrupt for k in CONTROL_KINDS})
        with self.assertRaisesRegex(TransportError, 'identity mismatch'):
            services.handlers['kv_begin'](request(tag=3))

    def test_committed_ampere_client_state_payload_protocol_joins_ports(self):
        # Exercise the ACTUAL committed client methods, with small port/control
        # fixtures. This bypasses constructor qualification solely in this unit
        # test; it cannot qualify an original machine or hardware execution.
        port, authority, _ = self.fixture()
        def actual_control(kind):
            def invoke(r):
                response = dict(r, accepted=True, fault=False)
                response.update({k: True for k in CONTROL_ACKS[kind]})
                return response
            return invoke
        kv = KVHandlers(authority, {k: actual_control(k) for k in CONTROL_KINDS})
        handlers = {k: lambda r: dict(r, accepted=True, fault=False) for k in KINDS}
        handlers.update(kv.handlers)
        session = DeliverySession(handlers, require_kv=True)
        memory = SimpleNamespace(state={1: {'base': 0, 'bytes': 72}},
                                 counters=Counter(), leases={5: {'key': (0, 1, 0)}})
        def exchange(kind, **fields):
            r = dict(program_sha256=PROGRAM_SHA, source_PC=20, sequence=session.sequence, **fields)
            return session.transact(dict(kind=kind, request=r))
        delivery = SimpleNamespace(machine=SimpleNamespace(memory=memory),
                                   stopped=False, pending=False, exchange=exchange)
        client = KVStorageDelivery.__new__(KVStorageDelivery)
        client.delivery = delivery; client.memory = memory
        client.original = {'state_write': lambda *args: None}
        client.state_write(1, 30, b'ABCDE')
        self.assertEqual(client.state_read(1, 29, 7), bytes([29]) + b'ABCDE' + bytes([35]))
        import numpy as np
        window = PhysicalReadWindow(client, 5, np.array([34, 30, 34, 29]))
        self.assertEqual([window[1, i] for i in (34, 30, 34, 29)], [69, 65, 69, 29])
        self.assertEqual(session.sequence, 3)
        self.assertFalse(delivery.stopped)


if __name__ == "__main__":
    unittest.main()
