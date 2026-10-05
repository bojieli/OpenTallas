"""Adapter software handshake tests; pin fixtures are not RTL qualification."""
from dataclasses import replace
import unittest

from tools.gpu_sys.canonical_qwen_payload_w2 import PayloadRoute, PayloadW2Adapter
from tools.gpu_sys.canonical_qwen_transport import TransportError, W2PrimaryPort


class ControllerPins:
    def __init__(self):
        self.values = dict(fault=0, por_n=1, run_enable=1, writer_retained=1,
                          writer_identity=0xfedcba9876543210, writer_key=0xe2345,
                          payload_req_valid=1, payload_req_write=0,
                          payload_req_sector=191, payload_req_source_addr=0x300000020,
                          payload_req_data=0, payload_req_rmw=1, payload_req_rmw_last=0,
                          payload_ready=0)
        self.writes = []

    def parameter(self, name):
        return {'ENABLE': 1}[name]

    def get(self, name):
        return self.values.get(name, 0)

    def set(self, name, value):
        self.writes.append((name, value))
        self.values[name] = value

    def settle(self):
        pass


class W2Pins:
    WIDTHS = dict(c_req_v=1, c_req_we=1, c_req_addr=34, c_req_tag=32,
                  c_req_gen=4, c_req_data=256, c_rsp_rdy=1, c_wr_done_rdy=1)

    def __init__(self):
        self.params = dict(NC=6, MAX_OUT=16, AW=34, CTAGW=32, GENW=4,
                           PTAGW=35, PC_ID=7, OPT_EXACT=1, OPT_RESET_QUARANTINE=1)
        self.values = dict(fault=0, repair_busy=0, c_req_rdy=0)
        self.writes = []
        self.on_settle = None

    def parameter(self, name):
        return self.params[name]

    def get(self, name):
        return self.values.get(name, 0)

    def set_client(self, client, name, value):
        self.writes.append((client, name, value))
        bits = self.WIDTHS[name]
        mask = ((1 << bits) - 1) << (bits * client)
        self.values[name] = (self.get(name) & ~mask) | (value << (bits * client))

    def settle(self):
        if self.on_settle:
            self.on_settle(self)


class CallerAuthority:
    def __init__(self):
        self.reverse = False
        self.observed = []

    def completion_ready(self, *args):
        raise AssertionError('controller payload_ready owns capture')

    def reverse_validated(self, *args):
        self.observed.append(args)
        return self.reverse


class SectorAuthority:
    def __init__(self, port):
        self.grant = object()
        self.route = PayloadRoute(port, 5, 0x300000020, 0xfedcba98, 14, self.grant)
        self.available = False
        self.new_available = False
        self.release_ready = False
        self.acquires = []
        self.continues = []
        self.releases = []

    def acquire_payload_sector(self, offer):
        self.acquires.append(dict(offer))
        return self.route if self.available else None

    def continue_payload_rmw(self, grant, offer):
        self.continues.append((grant, dict(offer)))
        return self.route if self.new_available else None

    def release_payload_sector(self, grant, offer):
        self.releases.append((grant, dict(offer)))
        return self.release_ready


class PayloadAdapterTest(unittest.TestCase):
    def setUp(self):
        self.c = ControllerPins()
        self.w = W2Pins()
        self.caller = CallerAuthority()
        self.port = W2PrimaryPort(self.w, self.caller)
        self.a = SectorAuthority(self.port)
        self.pump = PayloadW2Adapter(self.c, self.a, enabled=True)

    def edge(self):
        self.pump.before_edge()
        # The production enclosing simulator advances its single actual clock
        # HERE. These fixtures inspect handshake logic only, not RTL timing.
        self.pump.after_edge()

    def accepted(self):
        self.a.available = True
        self.w.values['c_req_rdy'] = 1 << 5
        self.edge()
        self.assertEqual(self.pump.state, 'CAPTURE')
        self.c.values['payload_req_valid'] = 0

    def response(self, write=False, data=(1 << 255) | 0x123456789):
        stem = 'c_wr_done' if write else 'c_rsp'
        self.w.values[stem + '_v'] = 1 << 5
        self.w.values[stem + '_tag'] = 0xfedcba98 << (5 * 32)
        self.w.values[stem + '_gen'] = 14 << (5 * 4)
        self.w.values['c_rsp_data'] = data << (5 * 256)

    def old_reverse(self):
        self.accepted()
        self.response()
        self.c.values['payload_ready'] = 1
        self.edge()
        self.assertEqual(self.pump.state, 'REVERSE')
        self.caller.reverse = True
        self.edge()
        self.caller.reverse = False
        self.w.values['c_rsp_v'] = 0
        self.assertEqual(self.pump.state, 'IDLE')
        self.assertIs(self.pump.rmw[1], self.a.grant)
        self.assertEqual(self.a.releases, [])

    def new_request(self):
        self.c.values.update(payload_req_valid=1, payload_req_write=1,
                             payload_req_rmw_last=1, payload_req_data=(1 << 255) | 0xabcd)

    def test_default_off_and_requires_actual_authorities(self):
        with self.assertRaisesRegex(TransportError, 'default off'):
            PayloadW2Adapter(self.c, self.a)
        with self.assertRaisesRegex(TransportError, 'missing actual'):
            PayloadW2Adapter(self.c, object(), enabled=True)

    def test_actual_grant_and_w2_request_backpressure_preserve_full_tuple(self):
        self.edge()
        self.assertEqual(self.pump.accepted, 0)
        self.assertEqual(self.w.writes, [])
        self.a.available = True
        self.edge()
        self.assertEqual(self.pump.state, 'OFFER')
        self.assertEqual(self.c.get('payload_req_ready'), 0)
        for name, expected, bits in [('c_req_addr', 0x300000020, 34),
                                     ('c_req_tag', 0xfedcba98, 32), ('c_req_gen', 14, 4)]:
            self.assertEqual(self.w.get(name) >> (bits * 5), expected)
        self.w.values['c_req_rdy'] = 1 << 5
        self.edge()
        self.assertEqual(self.pump.accepted, 1)

    def test_k_read_write_reverse_then_real_sector_release(self):
        self.old_reverse()
        self.new_request()
        self.edge()
        self.assertEqual(self.pump.accepted, 1)  # Actual new route not ready.
        self.a.new_available = True
        self.edge()
        self.assertEqual(self.pump.accepted, 2)
        self.assertEqual(self.w.get('c_req_data') >> (5 * 256), (1 << 255) | 0xabcd)
        self.c.values['payload_req_valid'] = 0
        self.response(write=True)
        self.edge()
        self.assertEqual(self.c.get('payload_visible'), 1)
        self.assertEqual(self.c.get('payload_reverse'), 0)
        self.edge()
        self.assertEqual(self.pump.state, 'REVERSE')
        self.assertEqual(self.a.releases, [])
        self.caller.reverse = True
        self.edge()
        self.assertEqual(self.pump.state, 'RELEASE')
        self.assertEqual(self.c.get('payload_visible'), 0)
        self.assertEqual(self.c.get('payload_reverse'), 1)
        self.edge()
        self.assertIsNotNone(self.pump.rmw)
        self.a.release_ready = True
        self.edge()
        self.assertEqual(self.pump.state, 'IDLE')
        self.assertIsNone(self.pump.rmw)
        self.assertEqual((self.pump.accepted, self.pump.captured, self.pump.reversed), (2, 2, 2))
        self.assertEqual(self.caller.observed[-1], (5, 0xfedcba98, 14, True))
        self.assertTrue(all(g is self.a.grant for g, _ in self.a.continues + self.a.releases))

    def test_capture_backpressure_reads_actual_high_bits_and_source_identity(self):
        self.accepted()
        self.response()
        self.edge()
        self.assertEqual(self.pump.captured, 0)
        self.assertEqual(self.w.get('c_rsp_rdy'), 0)
        self.assertEqual(self.c.get('payload_identity'), 0xfedcba9876543210)
        self.assertEqual(self.c.get('payload_key'), 0xe2345)
        self.assertEqual(self.c.get('payload_sector'), 191)
        self.assertEqual(self.c.get('payload_source_addr'), 0x300000020)
        self.assertEqual(self.c.get('payload_rdata'), (1 << 255) | 0x123456789)
        self.c.values['payload_ready'] = 1
        self.edge()
        self.assertEqual(self.pump.captured, 1)

    def test_v_full_sector_write_does_not_acquire_rmw(self):
        self.c.values.update(payload_req_sector=271, payload_req_rmw=0,
                             payload_req_write=1, payload_req_data=(1 << 255) | 3)
        self.accepted()
        self.response(write=True)
        self.c.values['payload_ready'] = 1
        self.edge()
        self.caller.reverse = True
        self.edge()
        self.assertEqual(self.pump.state, 'RELEASE')
        self.assertIsNone(self.pump.rmw)
        self.assertEqual(self.a.continues, [])

    def test_stale_generation_retains_pending_and_no_retry(self):
        self.accepted()
        self.response()
        self.w.values['c_rsp_gen'] = 13 << 20
        with self.assertRaisesRegex(TransportError, 'tag/generation mismatch'):
            self.edge()
        self.assertTrue(self.port.stopped)
        self.assertIsNotNone(self.port.pending)
        self.assertEqual(self.a.releases, [])
        with self.assertRaisesRegex(TransportError, 'faulted'):
            self.edge()

    def test_fault_between_old_and_new_keeps_external_grant(self):
        self.old_reverse()
        self.w.values['fault'] = 1
        with self.assertRaisesRegex(TransportError, 'quarantine'):
            self.edge()
        self.assertTrue(self.port.stopped)
        self.assertIs(self.pump.rmw[1], self.a.grant)
        self.assertEqual(self.a.releases, [])

    def test_controller_reset_retains_original_sector(self):
        self.old_reverse()
        self.c.values['por_n'] = 0
        with self.assertRaisesRegex(TransportError, 'retained external'):
            self.edge()
        self.assertIs(self.pump.rmw[1], self.a.grant)
        self.assertEqual(self.a.releases, [])

    def test_unknown_changed_or_reassociated_new_requests_refused(self):
        for field in ('payload_req_source_addr', 'writer_identity', 'writer_key', 'payload_req_sector'):
            with self.subTest(field=field):
                self.setUp()
                self.old_reverse()
                self.new_request()
                self.c.values[field] += 32 if field == 'payload_req_source_addr' else 1
                with self.assertRaisesRegex(TransportError, 'differs|writer changed/lost'):
                    self.edge()
                self.assertEqual(self.a.releases, [])

    def test_original_rmw_grant_and_physical_mapping_cannot_change(self):
        for changed in (dict(grant=object()), dict(generation=13), dict(tag=1),
                        dict(client=4), dict(address=0x300000040)):
            with self.subTest(changed=changed):
                self.setUp()
                self.old_reverse()
                self.new_request()
                self.a.new_available = True
                self.a.route = replace(self.a.route, **changed)
                with self.assertRaisesRegex(TransportError, 'changed'):
                    self.edge()
                self.assertIs(self.pump.rmw[1], self.a.grant)
                self.assertEqual(self.a.releases, [])

    def test_request_changes_while_waiting_for_grant_or_w2_are_refused(self):
        for granted in (False, True):
            with self.subTest(granted=granted):
                self.setUp()
                self.a.available = granted
                self.edge()
                self.c.values['payload_req_data'] = 1 << 255
                with self.assertRaisesRegex(TransportError, 'request changed'):
                    self.edge()

    def test_repair_does_not_create_request_or_completion_acceptance(self):
        self.a.available = True
        self.w.values.update(repair_busy=1, c_req_rdy=1 << 5)
        with self.assertRaisesRegex(TransportError, 'during repair'):
            self.edge()
        self.assertEqual(self.pump.accepted, 0)

    def test_old_source_without_reset_quarantine_is_refused(self):
        self.w.params['OPT_RESET_QUARANTINE'] = 0
        self.a.available = True
        with self.assertRaisesRegex(TransportError, 'R7 reset-quarantine'):
            self.edge()

    def test_actual_signal_mutation_during_capture_is_refused(self):
        self.accepted()
        self.response()
        self.c.values['payload_ready'] = 1
        def changed(p):
            if p.get('c_rsp_rdy'):
                p.values['c_rsp_data'] ^= 1 << (5 * 256)
        self.w.on_settle = changed
        with self.assertRaisesRegex(TransportError, 'read data changed'):
            self.edge()
        self.assertEqual(self.pump.captured, 0)

    def test_held_completion_cannot_change_or_disappear_under_backpressure(self):
        for withdrawn in (False, True):
            with self.subTest(withdrawn=withdrawn):
                self.setUp()
                self.accepted()
                self.response()
                self.edge()
                if withdrawn:
                    self.w.values['c_rsp_v'] = 0
                else:
                    self.w.values['c_rsp_data'] ^= 1 << (5 * 256)
                with self.assertRaisesRegex(TransportError, 'held W2 completion'):
                    self.edge()
                self.assertEqual(self.pump.captured, 0)
                self.assertIsNotNone(self.port.pending)

    def test_writer_loss_after_request_acceptance_is_not_a_completion(self):
        self.accepted()
        self.c.values['writer_retained'] = 0
        with self.assertRaisesRegex(TransportError, 'writer changed/lost'):
            self.edge()
        self.assertEqual(self.a.releases, [])
        self.assertIsNotNone(self.port.pending)

    def test_pause_before_offer_leaves_real_grant_unacquired(self):
        self.c.values['run_enable'] = 0
        self.a.available = True
        self.edge()
        self.assertEqual(self.a.acquires, [])
        self.assertEqual(self.w.writes, [])
        self.c.values['run_enable'] = 1
        self.edge()
        self.assertEqual(self.pump.state, 'OFFER')

    def test_nonboolean_reverse_and_release_cannot_retire_a_grant(self):
        self.accepted()
        self.response()
        self.c.values['payload_ready'] = 1
        self.edge()
        self.caller.reverse = 1
        with self.assertRaisesRegex(TransportError, 'boolean observation'):
            self.edge()
        self.assertEqual(self.pump.reversed, 0)
        self.setUp()
        self.c.values.update(payload_req_sector=256, payload_req_rmw=0, payload_req_write=1)
        self.accepted()
        self.response(write=True)
        self.c.values['payload_ready'] = 1
        self.edge()
        self.caller.reverse = True
        self.edge()
        self.a.release_ready = 1
        with self.assertRaisesRegex(TransportError, 'boolean handshake'):
            self.edge()
        self.assertIs(self.pump.route.grant, self.a.grant)

    def test_edges_are_external_and_no_fences_provider_or_stage_pins_driven(self):
        self.old_reverse()
        self.assertTrue(all(name in W2Pins.WIDTHS for _, name, _ in self.w.writes))
        self.assertTrue(all(name.startswith('payload_') for name, _ in self.c.writes))
        with self.assertRaisesRegex(TransportError, 'no valid sampled edge'):
            self.pump.after_edge()
        self.pump.before_edge()
        with self.assertRaisesRegex(TransportError, 'edge not completed'):
            self.pump.before_edge()
        self.pump.after_edge()


if __name__ == '__main__':
    unittest.main()
