import unittest
from hbm_idx_static_calendar import compile_program, FIELDS


def events(prog, field):
    lo, width = FIELDS[field]
    return [i for i,w in enumerate(prog) if (w >> lo) & ((1<<width)-1)]


class ExchangeCalendar(unittest.TestCase):
    def test_four_cycle_banks_match_burst_service(self):
        p,m=compile_program(query_period=4,key_period=4)
        heads=events(p,'head'); keys=events(p,'beat')
        self.assertEqual(len(heads),32);self.assertEqual(len(keys),171)
        self.assertEqual(set(b-a for a,b in zip(heads,heads[1:])),{4})
        self.assertEqual(set(b-a for a,b in zip(keys,keys[1:])),{4})
        self.assertEqual(m['bank_exchange']['added_query_span'],93)
        self.assertEqual(m['bank_exchange']['added_key_span'],510)
        self.assertLessEqual(len(p),2048)
        slo=FIELDS['op'][0];alo=FIELDS['addr'][0]
        stores={((w>>alo)&255):i for i,w in enumerate(p) if ((w>>slo)&15)==2}
        delta=m['calendar_shift']['sel']-m['calendar_shift']['s']
        for k,edge in enumerate(keys):self.assertEqual(stores[k],edge+123+delta)

    def test_default_still_exposes_actual_burst_conflict(self):
        p,_=compile_program()
        self.assertEqual(min(b-a for a,b in zip(events(p,'head'),events(p,'head')[1:])),1)
        self.assertEqual(min(b-a for a,b in zip(events(p,'beat'),events(p,'beat')[1:])),1)

    def test_all_payload_commands_preserved(self):
        from collections import Counter
        a,_=compile_program();b,_=compile_program(query_period=4,key_period=4)
        # Independent control fields may share an instruction before/after retiming.
        # Compare every nonzero field value, preserving exact multiplicity.
        for field,(lo,width) in FIELDS.items():
            mask=(1<<width)-1
            self.assertEqual(Counter((w>>lo)&mask for w in a if (w>>lo)&mask),
                             Counter((w>>lo)&mask for w in b if (w>>lo)&mask),field)

    def test_invalid_service_period_refused(self):
        for k in (0,-1,1.5):
            with self.assertRaises(ValueError):compile_program(key_period=k)


if __name__=='__main__':unittest.main()
