import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_rom_fulldie import Master
from qwen_split import source_pin_plan as P


class RealSourcePinPlan(unittest.TestCase):
    def test_quarter_band_plan_has_every_real_output_and_same_child_clocks(self):
        q=Master('qfd_sp_band_lanes',881.28,1131.84,7,'')
        P.apply_band(q)
        with tempfile.TemporaryDirectory() as d:
            result=P.export(q,Path(d))
            a=json.loads((Path(d)/(q.name+'.json')).read_text())
        self.assertEqual(result['ports'],31)
        self.assertEqual(result['overlapping_pin_pairs'],0)
        self.assertEqual(a['ports']['pw']['bits'],513)
        self.assertEqual(a['ports']['f']['bits'],1)
        self.assertEqual(a['ports']['f_up']['bits'],4)
        self.assertEqual(sum(p.startswith('ck') for p in a['ports']),17)
        for k in range(4):self.assertEqual(a['ports'][f'pw_l{k}']['bits'],129)
        old=json.loads((P.ROOT/'results/arch/qwen_split_compute_1014/c15_preflight/qfd_sp_band_lanes.json').read_text())
        for p in ('ck','rst_n','b0','lnk'):
            self.assertEqual(a['ports'][p]['range_um'],old['ports'][p]['range_um'])
        for k in range(16):
            self.assertEqual(a['ports'][f'ck_l{k}']['positions_xy_um'],old['ports'][f'ck_l{k}']['positions_xy_um'])

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

    def test_mirrored_children_retain_actual_clock_centres(self):
        M={'qfd_tile_nk':Master('qfd_tile_nk',449.28,1442.88,7,'')}
        P.apply(M)
        q=M['qfd_tile_nk']
        self.assertEqual(q.ports['ck_lsl0'][2], 'M5')
        self.assertEqual(q.ports['ck_lsl0'][3], [(103.74,391.308)])
        self.assertEqual(q.ports['ck_rp0'][3], [(22.524,1082.796)])
        self.assertEqual(q.ports['ck_rp1'][3], [(22.524,1233.996)])
        self.assertEqual(q.ports['ck_rp2'][3], [(22.524,1385.196)])

    def test_dvm_clock_order_is_the_real_rtl_north_then_south_order(self):
        M={n:Master(n,64.8,1434.24,7,'') for n in ('qfd_xcol_e','qfd_xcol_w')}
        M['qfd_xcst_n']=Master('qfd_xcst_n',52.68,103.656,3,'')
        P.apply_dvm_clocks(M)
        for n in ('qfd_xcol_e','qfd_xcol_w'):
            q=M[n]
            self.assertEqual(q.ports['ck0'][3],[(.06,754.812)])
            self.assertEqual(q.ports['ck1'][3],[(.06,950.412)])
            self.assertEqual(q.ports['ck5'][3],[(.06,483.828)])
            self.assertEqual(q.ports['ck8'][3],[(.06,75.588)])
        self.assertEqual(M['qfd_xcst_n'].ports['ck'][2:4],('M3',[(52.065,103.637)]))

    def test_every_entry_pin_sits_on_its_layer_track(self):
        # C18 smoke 2026-10-15: off-track child clock entries left qfd_tile_nk/nl and qfd_xcol_e/w with no
        # legal placement origin (check_macro_track_alignment); every xy entry must be on a preferred track.
        M={n:Master(n,449.28,1442.88,7,'') for n in ('qfd_tile_nk','qfd_tile_nl')}
        M.update({n:Master(n,64.8,1434.24,7,'') for n in ('qfd_xcol_e','qfd_xcol_w')})
        M['qfd_xcst_n']=Master('qfd_xcst_n',52.68,103.656,3,'')
        P.apply(M); P.apply_dvm_clocks(M)
        n=0
        for q in M.values():
            for p,s_ in q.ports.items():
                if s_[0]!='xy':
                    continue
                ax,off,pitch=P.TRACK[s_[2]]
                z=s_[3][0][ax]
                self.assertAlmostEqual(((z-off)/pitch)%1.0 if ((z-off)/pitch)%1.0<.5 else ((z-off)/pitch)%1.0-1.0,0.0,places=6,msg=(q.name,p,z))
                n+=1
        self.assertGreater(n,30)

    def test_off_track_mutant_is_detected(self):
        self.assertNotEqual(P.on_track('M5',(22.506,1.0))[0],22.506)
        self.assertEqual(P.on_track('M5',(22.524,1.0))[0],22.524)

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
