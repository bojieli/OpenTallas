"""Check actual source word permutation and fail-closed reservation lifecycle."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import head_ingress_request as request
import head_source_bands


class SourceBandsTest(unittest.TestCase):
    def test_actual_ingress_word_matches_ectl_wire_format(self):
        rtl = (Path(__file__).resolve().parents[2] /
            'rtl/qwen_sys/split_20261014/qkh_head_ingress_abc.sv').read_text()
        self.assertIn('{c_in,row_in,lt_in,q_valid_in,q_beat_in,q_data_in}', rtl)
        # ECTL C's actual wire format is {data512,beat6,valid1}; the raw
        # head ti0 puts {valid1,beat6,data512} in its low519 bits.
        for h in range(4):
            pair = h//2
            wires = {f't{pair}_row': list(range(10000,10512)),
                     'b_row': list(range(10512,11024)),
                     f't{pair}_cl': list(range(20000,20016)),
                     f't{pair}_q': list(range(30000,30519)),
                     f'e{h}': list(range(40000,40016))}
            def value(role, bit):
                match = re.fullmatch(r'(.+)\[(\d+)\]', request.signal(role,bit,h))
                key = 'b_row' if role == 'b' and '_row' in match[1] else match[1]
                return wires[key][int(match[2])]
            a = [value('a',i) for i in range(512)]
            b = [value('b',i) for i in range(528)]
            c = [value('c',i) for i in range(535)]
            got = c[:519]+b[:12]+a+b[12:524]+b[524:528]
            q, row, cl = (wires[f't{pair}_{k}'] for k in ('q','row','cl'))
            row = row+wires['b_row']
            self.assertEqual(got, q[7:]+q[1:7]+q[:1]+cl[4:]+row+cl[:4])
            self.assertEqual(c[519:], wires[f'e{h}'])
            chunks=dict(a=a,b=b,c=c)
            gathered=[chunks[role][index]for role,index in
                      (request.chunk_source_for_tstage(i)for i in range(1575))]
            self.assertEqual(gathered,got+c[519:])
        with self.assertRaises(ValueError):request.chunk_source_for_tstage(1575)

    def test_rejects_existing_relays_and_reduced_shape(self):
        with self.assertRaisesRegex(ValueError, 'precede ALL'):
            head_source_bands.reserve({'insts':[SimpleNamespace(master='qkd_rly_1')]},None)
        with self.assertRaisesRegex(ValueError, '128-head'):
            head_source_bands.reserve({'insts':[]},None)

    def test_case_refuses_unqualified_bands_even_for_api_caller(self):
        import kv_die
        with self.assertRaisesRegex(ValueError,'plan-only'):
            kv_die.case({'head_source_bands':{'adopted':False}},Path('/tmp/not-emitted'))

    def test_actual_reset_graph_enforces_flush_limit_and_clock_binding(self):
        def design(stages,clock=True):
            insts=[SimpleNamespace(name='host',master='host'),SimpleNamespace(name='head',master='head')]
            insts += [SimpleNamespace(name=f'r{i}',master='qkd_rly_t1')for i in range(stages)]
            names=['host']+[f'r{i}'for i in range(stages)]+['head']
            buses=[(f'rst_die__{i}','kv_oneway',1,[(a,'b'),(b,'a')])
                   for i,(a,b) in enumerate(zip(names,names[1:]))]
            if clock:buses.append(('clk_core_c','clock_trunk',1,[(n,'ck')for n in names]))
            return dict(insts=insts,buses=buses,head_source_bands={})
        valid=design(127)
        head_source_bands.lifecycle(valid,SimpleNamespace(RELAY_FLUSH=128))
        self.assertEqual(valid['head_source_bands']['lifecycle']['depths']['rst_die'],127)
        with self.assertRaisesRegex(ValueError,'flush128'):
            head_source_bands.lifecycle(design(128),SimpleNamespace(RELAY_FLUSH=128))
        with self.assertRaisesRegex(ValueError,'unclocked'):
            head_source_bands.lifecycle(design(1,False),SimpleNamespace(RELAY_FLUSH=128))


if __name__ == '__main__':
    unittest.main()
