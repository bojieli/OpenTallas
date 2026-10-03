"""Live socket/pipe plumbing tests. Fixture replies are not RTL qualification."""
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest

import numpy as np

from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA, UnixRTLTransport
from tools.gpu_sys.canonical_qwen_transport import (
    DeliverySession, KINDS, KV_KINDS, ALL_KINDS, SimulatorPipes, TransportError, UnixDeliveryServer, W2PrimaryPort, decode, encode)


def request(sequence=0, pc=40, **fields):
    result = dict(program_sha256=PROGRAM_SHA, sequence=sequence, source_PC=pc)
    result.update(fields)
    return result


def reply(req, **fields):
    result = dict(req, accepted=True, fault=False)
    result.update(fields)
    return result


class TransportTest(unittest.TestCase):
    def test_all_six_actual_client_socket_pipe_routes(self):
        # Existing-client -> server -> inherited simulator pipes -> server ->
        # existing-client, including scalar/array exact bytes and opaque owner.
        sim_read, host_write = os.pipe()
        host_read, sim_write = os.pipe()
        pipes = SimulatorPipes(host_read, host_write)
        observed = []
        errors = []
        def simulator_fixture():
            try:
                with os.fdopen(sim_read, "rb") as reader, os.fdopen(sim_write, "wb") as writer:
                    for _ in KINDS:
                        message = decode(reader.readline())
                        observed.append(message)
                        writer.write(encode(reply(message["request"], owner55=(1 << 54) + 38)))
                        writer.flush()
            except BaseException as exc:
                errors.append(exc)
        with tempfile.TemporaryDirectory() as td:
            server = UnixDeliveryServer(Path(td) / "sim.sock", pipes.handlers)
            def serve():
                try:
                    server.serve_once()
                except BaseException as exc:
                    errors.append(exc)
            sim_thread = threading.Thread(target=simulator_fixture)
            host_thread = threading.Thread(target=serve)
            sim_thread.start(); host_thread.start()
            client = UnixRTLTransport(server.path, PROGRAM_SHA)
            try:
                for sequence, kind in enumerate(KINDS):
                    values = np.array([0x80000000, 0x7fc00001, 0xffffffff], dtype="<u4")
                    req = request(sequence, payload=bytes(range(256)) * 2, words=values,
                                  source_key=["RF", 0, 0, 38], version="actual-source-version")
                    got = client.transact(kind, req)
                    self.assertEqual(got["payload"], req["payload"])
                    self.assertEqual(got["words"].tobytes(), values.tobytes())
                    self.assertEqual(got["owner55"], (1 << 54) + 38)
                    self.assertEqual(got["sequence"], sequence)
            finally:
                client.close()
                host_thread.join(10); sim_thread.join(10)
                server.close(); pipes.close()
                os.close(host_read); os.close(host_write)
            self.assertFalse(host_thread.is_alive())
            self.assertFalse(sim_thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual([m["kind"] for m in observed], list(KINDS))
            self.assertEqual(server.session.sequence, 6)

    def test_full_token_requires_complete_kv_lifecycle(self):
        handlers = {k: reply for k in KINDS}
        with self.assertRaisesRegex(TransportError, "kv_state_read"):
            DeliverySession(handlers, require_kv=True)
        handlers["kv_begin"] = reply
        with self.assertRaisesRegex(TransportError, "kv_reader_release"):
            DeliverySession(handlers)

    def test_kv_and_rf_share_sequence_and_retained_fault_debt(self):
        observed = []
        def actual_handler(req):
            observed.append(req["sequence"])
            return reply(req)
        session = DeliverySession({k: actual_handler for k in ALL_KINDS}, require_kv=True)
        for seq, kind in enumerate(ALL_KINDS):
            req = request(seq, payload=b"actual port fixture")
            self.assertEqual(session.transact(dict(kind=kind, request=req))["payload"], req["payload"])
        self.assertEqual(observed, list(range(16)))
        stale = dict(kind="kv_reader_release", request=request(15))
        with self.assertRaisesRegex(TransportError, "out-of-order"):
            session.transact(stale)
        self.assertIs(session.pending, stale)
        self.assertTrue(session.stopped)

    def test_missing_actual_handler_refused(self):
        with self.assertRaisesRegex(TransportError, "missing simulator handlers"):
            DeliverySession({})

    def test_stale_owner_response_identity_faults_without_retry(self):
        calls = []
        def stale(req):
            calls.append(req)
            return reply(dict(req, sequence=req["sequence"] + 1))
        session = DeliverySession({k: stale for k in KINDS})
        message = dict(kind="source_page_write", request=request())
        with self.assertRaisesRegex(TransportError, "identity mismatch"):
            session.transact(message)
        self.assertIs(session.pending, message)
        with self.assertRaisesRegex(TransportError, "no further grants"):
            session.transact(message)
        self.assertEqual(len(calls), 1)

    def test_handler_cannot_retag_by_mutating_request(self):
        def mutate(req):
            req["sequence"] = 99
            return reply(req)
        session = DeliverySession({k: mutate for k in KINDS})
        with self.assertRaisesRegex(TransportError, "identity mismatch"):
            session.transact(dict(kind="native_primitive", request=request()))

    def test_no_synthetic_accepted_ack(self):
        session = DeliverySession({k: lambda req: dict(req) for k in KINDS})
        with self.assertRaisesRegex(TransportError, "rejected or faulted"):
            session.transact(dict(kind="source_retire", request=request()))

    def test_duplicate_sequence_refused_before_handler(self):
        calls = []
        def actual(req):
            calls.append(req)
            return reply(req)
        session = DeliverySession({k: actual for k in KINDS})
        message = dict(kind="source_publish", request=request())
        session.transact(message)
        with self.assertRaisesRegex(TransportError, "duplicate/out-of-order"):
            session.transact(message)
        self.assertEqual(len(calls), 1)

    def test_reduced_program_refused(self):
        session = DeliverySession({k: reply for k in KINDS})
        with self.assertRaisesRegex(TransportError, "noncanonical/reduced"):
            session.transact(dict(kind="source_page_read", request=request(program_sha256="reduced")))

    def test_simulator_pipe_eof_latches_failure(self):
        reader, writer = os.pipe()
        input_reader, input_writer = os.pipe()
        pipes = SimulatorPipes(reader, input_writer)
        os.close(writer)
        try:
            with self.assertRaisesRegex(TransportError, "EOF"):
                pipes.handlers["native_primitive"](request())
            with self.assertRaisesRegex(TransportError, "no retry"):
                pipes.handlers["native_primitive"](request())
        finally:
            pipes.close()
            os.close(reader); os.close(input_reader); os.close(input_writer)

    def test_existing_endpoint_not_removed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "owned.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as owned:
                owned.bind(str(path))
                with self.assertRaises(OSError):
                    UnixDeliveryServer(path, {k: reply for k in KINDS})
                self.assertTrue(path.exists())

    def test_fault_reply_reaches_ampere_client_and_closes_session(self):
        errors = []
        with tempfile.TemporaryDirectory() as td:
            server = UnixDeliveryServer(Path(td) / "sim.sock", {k: lambda req: reply(req, fault=True) for k in KINDS})
            def serve():
                try:
                    server.serve_once()
                except TransportError as exc:
                    errors.append(str(exc))
            thread = threading.Thread(target=serve)
            thread.start()
            client = UnixRTLTransport(server.path, PROGRAM_SHA)
            try:
                result = client.transact("source_retire", request())
                self.assertIs(result["accepted"], False)
                self.assertIs(result["fault"], True)
            finally:
                client.close(); thread.join(10); server.close()
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ["simulator completion rejected or faulted"])
            self.assertTrue(server.session.stopped)


class W2PortFixture:
    """Handshake test fixture only; no RTL behavior or timing qualification."""
    def __init__(self, we=False):
        self.cycle = 0
        self.we = we
        self.inputs = {}
        self.history = []
        self.wrong_generation = False
        self.params = dict(NC=6, MAX_OUT=16, AW=34, CTAGW=32, GENW=4, PTAGW=35, OPT_EXACT=1, OPT_RESET_QUARANTINE=1, PC_ID=7)

    def parameter(self, name):
        return self.params[name]

    def set_client(self, client, name, value):
        self.inputs[client, name] = value

    def settle(self):
        pass

    def get(self, name):
        if name == "fault":
            return 0
        if name == "repair_busy":
            return int(self.cycle < 2)
        if name == "c_req_rdy":
            return (1 << 5) if self.cycle >= 2 else 0
        if name in ("c_rsp_v", "c_wr_done_v"):
            return (1 << 5) if self.cycle >= 4 else 0
        if name in ("c_rsp_tag", "c_wr_done_tag"):
            return 0xfedcba98 << (32 * 5)
        if name in ("c_rsp_gen", "c_wr_done_gen"):
            return (4 if self.wrong_generation else 3) << (4 * 5)
        if name == "c_rsp_data":
            return int.from_bytes(bytes(range(32)), "little") << (256 * 5)
        raise AssertionError(name)

    def tick(self):
        self.history.append((self.cycle, dict(self.inputs)))
        self.cycle += 1

    def completion_ready(self, client, tag, generation, we):
        return self.cycle >= 6

    def reverse_validated(self, client, tag, generation, we):
        return self.cycle >= 9


class W2AdapterTest(unittest.TestCase):
    def test_actual_port_names_held_tag_capture_reverse_authorities(self):
        port = W2PortFixture()
        driver = W2PrimaryPort(port, port)
        result = driver.sector(5, 0x123456780, 0xfedcba98, 3)
        self.assertEqual(result["payload"], bytes(range(32)))
        self.assertEqual(port.cycle, 9)
        self.assertIsNone(driver.pending)
        for cycle, inputs in port.history[:3]:
            self.assertEqual(inputs[5, "c_req_v"], 1)
            self.assertEqual(inputs[5, "c_req_tag"], 0xfedcba98)
            self.assertEqual(inputs[5, "c_req_gen"], 3)
            self.assertEqual(inputs[5, "c_req_addr"], 0x123456780)
        self.assertTrue(all(name.startswith("c_") for client, name in port.inputs))
        self.assertEqual(port.inputs[5, "c_rsp_rdy"], 0)

    def test_write_waits_wr_done_not_read_completion(self):
        port = W2PortFixture(we=True)
        driver = W2PrimaryPort(port, port)
        sector = bytes(range(32))
        result = driver.sector(5, 32, 0xfedcba98, 3, write=sector)
        self.assertTrue(result["write"])
        self.assertIsNone(result["payload"])
        self.assertEqual(port.inputs[5, "c_req_data"], int.from_bytes(sector, "little"))
        self.assertEqual(port.inputs[5, "c_wr_done_rdy"], 0)

    def test_default_off_primary_cannot_be_selected(self):
        port = W2PortFixture()
        port.params["OPT_EXACT"] = 0
        with self.assertRaisesRegex(TransportError, "widths/opt-in differ"):
            W2PrimaryPort(port, port)

    def test_reset_quarantine_required_for_canonical_service(self):
        port = W2PortFixture()
        port.params["OPT_RESET_QUARANTINE"] = 0
        with self.assertRaisesRegex(TransportError, "widths/opt-in differ"):
            W2PrimaryPort(port, port)
        del port.params["OPT_RESET_QUARANTINE"]
        with self.assertRaisesRegex(TransportError, "reset-safe parameter interface missing"):
            W2PrimaryPort(port, port)

    def test_stale_generation_retains_pending_and_blocks_retry(self):
        port = W2PortFixture()
        port.wrong_generation = True
        driver = W2PrimaryPort(port, port)
        with self.assertRaisesRegex(TransportError, "tag/generation mismatch"):
            driver.sector(5, 32, 0xfedcba98, 3)
        self.assertIsNotNone(driver.pending)
        self.assertTrue(driver.stopped)
        self.assertEqual(port.inputs[5, "c_req_v"], 0)
        with self.assertRaisesRegex(TransportError, "no owner reuse"):
            driver.sector(5, 32, 0xfedcba98, 3)

    def test_no_address_or_tag_truncation(self):
        port = W2PortFixture()
        driver = W2PrimaryPort(port, port)
        with self.assertRaisesRegex(TransportError, "invalid W2 address"):
            driver.sector(5, 1 << 34, 0xfedcba98, 3)
        with self.assertRaisesRegex(TransportError, "invalid W2 tag"):
            driver.sector(5, 32, 1 << 32, 3)
        self.assertEqual(port.inputs, {})


if __name__ == "__main__":
    unittest.main()
