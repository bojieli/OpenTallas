"""Attention microcalendar: production w16 ages, explicit link ages, static single-request occupancy."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import attention as A
from qwen_static_schedule.calendar import compile_calendar, ScheduleError, sha


class Attention(unittest.TestCase):
    def test_service_lengths_are_the_measured_w16(self):
        # measured on the w16 production binary (results/arch/qwen_attention_rate_1015/receipt.json)
        self.assertEqual(A.per_layer_table((1, 1000, 8192)), {1: 882, 1000: 943, 8192: 1555})
        with self.assertRaises(ScheduleError):
            A.service(8192, pv='w1')
        with self.assertRaises(ScheduleError):
            A.service(0)

    def test_link_ages_required(self):
        rec = dict(stage=0, pc=0, word='1', unit=1)
        for link in ({}, dict(request_edges=5), dict(request_edges=0, result_edges=5)):
            with self.subTest(link=link), self.assertRaises(ScheduleError):
                A.pc11_implementation(rec, 8192, 'L0', link, period_fs=833333)

    def test_compiles_and_refuses_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'svc.sv').write_text('module m; endmodule\n')
            prog = root / 'p.hex'
            prog.write_text('1\n1\n')
            P = 1000
            link = dict(request_edges=30, result_edges=35)
            recs = [dict(stage=0, pc=0, word='1', unit=1), dict(stage=0, pc=1, word='1', unit=1)]
            instr = [A.pc11_implementation(recs[0], 8192, 'L0', link, period_fs=P),
                     A.pc11_implementation(recs[1], 8192, 'L1', link, period_fs=P)]
            instr[1]['events'][0]['requires'] = ['attn_out:L0']       # L1's q depends on L0's attention output
            contract = dict(schema='opentallas.qwen-native-microcalendar.v1', source_sha256={'svc.sv': sha(root / 'svc.sv')},
                            clocks={'core': dict(period_fs=P, phase_fs=0)}, resources=A.resources(), buffers=A.buffers(),
                            deadline_fs=10 ** 9, start_fs=0,
                            external_inputs=[dict(key='q:L0', boundary='reset', available_fs=0)], instructions=instr)
            out = compile_calendar([prog], contract, root)
            t = [i['time_fs'] for i in out['issues']]
            self.assertEqual(t[0], P)                                 # strictly after the reset-boundary q
            self.assertEqual(t[1], t[0] + (30 + 1555 + 35) * P + P)  # strictly after the landed result
            self.assertEqual(out['buffer_peaks'], {'attn.service': 1})
            instr[1]['events'][0]['requires'] = ['q:L0']             # overlap: second request while the service is busy
            with self.assertRaises(ScheduleError):
                compile_calendar([prog], contract, root)


if __name__ == '__main__':
    unittest.main()
