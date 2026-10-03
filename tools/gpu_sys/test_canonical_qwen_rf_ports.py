"""Handshake fixtures test transactors; these are not RTL/token verdicts."""
import hashlib
import unittest

from tools.gpu_sys.canonical_qwen_rf_ports import RFPageHandlers, RFPorts
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA


class Pins:
    def __init__(self):
        self.inputs = {}
        self.cycle = 0
        self.wrong_owner = False
        self.bad_mirror = False
        self.data = bytes(range(256)) * 2

    def parameter(self, name):
        return 1

    def set(self, name, value):
        self.inputs[name] = value

    def settle(self):
        pass

    def tick(self):
        self.cycle += 1

    def get(self, name):
        if name == "ack_identity_fault":
            return 0
        if name in ("wr_ready", "rd_ready"):
            return int(self.cycle >= 2)
        if name in ("ack_valid", "rsp_valid"):
            return int(self.cycle >= 5)
        if name == "ack_slot":
            return self.inputs["wr_addr"]
        if name == "ack_owner":
            return self.inputs["wr_owner"] ^ int(self.wrong_owner)
        if name in ("rsp_a", "rsp_b"):
            bits = int.from_bytes(self.data, "little")
            return bits ^ int(name == "rsp_b" and self.bad_mirror)
        raise AssertionError(name)


class Authority:
    def __init__(self, rf):
        self.rf = rf
        self.retained = True
        self.calls = []

    def resolve_source(self, request, write):
        self.calls.append((request["source_key"], write))
        return self.rf, (1 << 45) + 7

    def source_owner_retained(self, request, owner):
        return self.retained


def request(raw):
    return dict(program_sha256=PROGRAM_SHA, source_PC=39, sequence=0,
                source_key=["RF", 0, 0, 38], version="producer-version",
                lease="value:producer-version", mirrors=2,
                payload=raw, payload_sha256=hashlib.sha256(raw).hexdigest())


class RFPortTest(unittest.TestCase):
    def test_actual_slot_owner_ack_handshake(self):
        pins = Pins()
        rf = RFPorts(pins)
        owner = (1 << 45) + 7
        self.assertEqual(rf.write(38, owner, pins.data), (38, owner))
        self.assertEqual(pins.cycle, 6)
        self.assertEqual(pins.inputs["wr_owner"], owner)
        self.assertEqual(pins.inputs["wr_data"], int.from_bytes(pins.data, "little"))
        self.assertEqual(pins.inputs["wr_valid"], 0)
        self.assertEqual(pins.inputs["ack_ready"], 0)

    def test_stale_ack_blocks_reuse_and_preserves_owner(self):
        pins = Pins(); pins.wrong_owner = True
        rf = RFPorts(pins)
        with self.assertRaisesRegex(TransportError, "slot/owner mismatch"):
            rf.write(38, 42, pins.data)
        self.assertEqual(rf.pending, (38, 42))
        self.assertTrue(rf.stopped)
        with self.assertRaisesRegex(TransportError, "no reuse"):
            rf.write(38, 42, pins.data)

    def test_mirror_capture_disagreement_refused(self):
        pins = Pins(); pins.bad_mirror = True
        rf = RFPorts(pins)
        with self.assertRaisesRegex(TransportError, "mirror read disagreement"):
            rf.read(38, 42)
        self.assertTrue(rf.stopped)
        self.assertEqual(rf.pending, (38, 42))

    def test_page_handler_returns_actual_captured_bytes(self):
        pins = Pins()
        authority = Authority(RFPorts(pins))
        handler = RFPageHandlers(authority)
        response = handler.source_page_read(request(pins.data))
        self.assertEqual(response["payload"], pins.data)
        self.assertIs(response["captured"], True)
        self.assertIs(response["owner_retained"], True)
        self.assertEqual(authority.calls, [(["RF", 0, 0, 38], False)])

    def test_write_handler_waits_actual_ack_before_visibility(self):
        pins = Pins()
        handler = RFPageHandlers(Authority(RFPorts(pins)))
        response = handler.source_page_write(request(pins.data))
        self.assertEqual(response["visible_copies"], 2)
        self.assertEqual(pins.cycle, 6)

    def test_upstream_owner_loss_blocks_grants(self):
        pins = Pins()
        authority = Authority(RFPorts(pins)); authority.retained = False
        handler = RFPageHandlers(authority)
        with self.assertRaisesRegex(TransportError, "owner was not retained"):
            handler.source_page_read(request(pins.data))
        with self.assertRaisesRegex(TransportError, "no further grants"):
            handler.source_page_read(request(pins.data))


if __name__ == "__main__":
    unittest.main()
