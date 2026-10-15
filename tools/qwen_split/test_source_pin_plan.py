import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_rom_fulldie import Master
from qwen_split import source_pin_plan as P


class RealSourcePinPlan(unittest.TestCase):
    def test_all_source_pins_fit_without_overlap(self):
        M = {n:Master(n,449.256,1442.856,7,'') for n in ('qfd_tile_nk','qfd_tile_nl')}
        M.update({f'qfd_port_tiles_{b}{s}':Master(f'qfd_port_tiles_{b}{s}',1036.776,2462.376,7,'') for b in range(3) for s in ('','_f1')})
        P.apply(M)
        with tempfile.TemporaryDirectory() as d:
            for n,q in M.items():
                evidence=P.export(q,Path(d))
                a=json.loads((Path(d)/(n+'.json')).read_text())
                self.assertEqual(evidence['overlapping_pin_pairs'],0)
                self.assertTrue(all(int(r['layer'][1:]) <= 7 for r in a['ports'].values()))
                if n.startswith('qfd_port_tiles'):
                    self.assertEqual(sum(p.startswith('ck') for p in a['ports']),49)
                    self.assertEqual(a['ports']['tc']['bits'],341)
                else:
                    self.assertEqual(a['ports']['tie_hi']['bits'],1)
                    self.assertEqual(a['ports']['tie_lo']['bits'],1)
                    self.assertEqual(a['ports']['tile_id']['bits'],16)
                    self.assertTrue(all(not a['ports'][p].get('interior') for p in ('t_out','tap','tile_id')))

    def test_historical_overlapping_tree_mutant_is_refused(self):
        M={'qfd_tile_nk':Master('qfd_tile_nk',449.256,1442.856,7,'')}
        P.apply(M)
        q=M['qfd_tile_nk']
        q.ports['n_a']=q.ports['t_out']
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'pin overlap'):
                P.export(q,Path(d))

    def test_missing_child_clock_evidence_is_refused(self):
        q=Master('qfd_tile_nk',449.256,1442.856,7,'')
        with self.assertRaises(KeyError):
            P.apply_tile(q,{'qfd_tile_nk':{'children':{}}})


if __name__=='__main__':
    unittest.main()
