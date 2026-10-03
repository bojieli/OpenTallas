"""KV transport fixtures, not actual HBM/RTL qualification."""
import unittest

from tools.gpu_sys.canonical_qwen_kv_ports import KVByteHandlers
from tools.gpu_sys.canonical_qwen_transport import DeliverySession, KINDS, KV_KINDS, TransportError, W2PrimaryPort
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA


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


def request(sequence=0, **fields):
    r = dict(program_sha256=PROGRAM_SHA, source_PC=20, sequence=sequence,
             rank=1, base=0, bytes=72, offset=0, count=1)
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
        reply = kv.handlers["kv_state_write"](request(offset=30, payload=b"ABCDE"))
        self.assertTrue(reply["write_completed"])
        self.assertEqual(bytes(port.data[:30]), original[:30])
        self.assertEqual(bytes(port.data[30:35]), b"ABCDE")
        self.assertEqual(bytes(port.data[35:]), original[35:])
        self.assertEqual([(a, w is not None) for _, a, _, _, w in port.calls],
                         [(0, False), (0, True), (32, False), (32, True)])
        self.assertTrue(all((c, t, g) == (5, 0xfedcba98, 3) for c, _, t, g, _ in port.calls))

    def test_aligned_payload_write_requires_actual_write_only(self):
        port, _, kv = self.fixture()
        kv.handlers["kv_payload_write"](request(offset=32, payload=b"z" * 32))
        self.assertEqual(len(port.calls), 1)
        self.assertEqual(port.calls[0][-1], b"z" * 32)

    def test_read_returns_physical_bytes_in_requested_order(self):
        port, _, kv = self.fixture()
        response = kv.handlers["kv_payload_read"](request(offset=29, count=9))
        self.assertEqual(response["payload"], bytes(range(29, 38)))
        self.assertEqual([x[1] for x in port.calls], [0, 32])

    def test_extent_tail_preserves_actual_padding_bytes(self):
        port, _, kv = self.fixture()
        old = bytes(port.data)
        kv.handlers["kv_state_write"](request(offset=68, payload=b"ABCD"))
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
        with self.assertRaisesRegex(TransportError, "byte aperture"):
            kv.handlers["kv_payload_write"](request(offset=71, payload=b"XX"))
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
        handlers.update(kv.handlers)
        session = DeliverySession(handlers)
        for seq, kind in enumerate(("source_page_read", "kv_state_read", "native_primitive", "kv_payload_read")):
            response = session.transact(dict(kind=kind, request=request(seq)))
            self.assertEqual(response["sequence"], seq)
        self.assertEqual(session.sequence, 4)

    def test_partial_kv_enrollment_refused(self):
        base = {k: lambda r: r for k in KINDS}
        base[KV_KINDS[0]] = lambda r: r
        with self.assertRaisesRegex(TransportError, "enroll together"):
            DeliverySession(base)


if __name__ == "__main__":
    unittest.main()
