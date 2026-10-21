#!/usr/bin/env python3
"""Regression controls for coherent migration, packed final lanes and actual CP grants."""
import copy
import json
import unittest
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parents[1]))
import l15_smb_relative as L
from d4g_gen2e_grants_smbcp import apply as grant
from hbm_die_v15.grant_slot_bind import resolve_slot

ROOT = HERE.parents[2]
F = ROOT / 'results/arch/hbm_die_d4g/smb_l15_1019/legacy_triplet_fixture.json'


class Migration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = json.loads(F.read_text())
        cls.new, cls.rep = L.apply(cls.old)

    def test_real_triplets_and_unresolved_producer(self):
        self.assertEqual(len(self.rep['unresolved_ids']), 16*sum(p.startswith('ids') for p in self.new['instances']['svg_SW0']['ports']))
        self.assertFalse(self.rep['release_ready'])
        self.assertEqual(self.new['instances']['cp_svg_SW0']['slot'], 'cp_svg_SW0')
        self.assertEqual(self.new['instances']['svg_SW0']['ports']['program_cfg_addr']['bits'], 11)
        self.assertEqual(self.new['instances']['svg_SW0']['ports']['run_count']['bits'], 9)

    def test_reapplication_byte_equivalent(self):
        again, rep = L.apply(self.new)
        self.assertEqual(again, self.new)
        self.assertFalse(rep['migrated'])

    def test_partial_triplet_refused(self):
        c = copy.deepcopy(self.old)
        c['instances']['cp_svg_SW0'] = copy.deepcopy(self.new['instances']['cp_svg_SW0'])
        with self.assertRaisesRegex(ValueError, 'PARTIAL_MIGRATION'):
            L.apply(c)

    def test_legacy_header_widening_refused(self):
        c = copy.deepcopy(self.old)
        c['instances']['cp_svg_SW0']['ports']['a_addr']['bits'] = 11
        with self.assertRaisesRegex(ValueError, 'PARTIAL_MIGRATION'):
            L.apply(c)

    def test_legacy_postrelay_requires_regeneration(self):
        c = copy.deepcopy(self.old)
        e = next(e for e in c['edges'] if e['source'][:2] == ['cp_svg_SW0', 'a_addr'])
        e['sink'] = ['old_narrow_lane', 'd', 0, 10]
        with self.assertRaisesRegex(ValueError, 'STALE_NARROW_RELAY_CHAIN'):
            L.apply(c)

    def test_final_missing_highbit_refused(self):
        c = copy.deepcopy(self.new)
        e = next(e for e in c['edges'] if e['source'][:2] == ['cp_svg_SW0', 'a_addr'])
        e['bits'] = 10; e['source'][3] = 10; e['sink'][3] = 10
        with self.assertRaisesRegex(ValueError, 'FINAL_LANE_WIDTH_MISMATCH'):
            L.apply(c)

    def test_real_packed_relay_path_accepted(self):
        c = copy.deepcopy(self.new)
        e = next(e for e in c['edges'] if e['source'][:2] == ['cp_svg_SW0', 'a_addr'])
        original_sink = e['sink']; e['sink'] = ['cp_lane', 'd', 7, 18]
        c['instances']['cp_lane'] = dict(master='hbfd_rly_48_EW', ports={
            'd': dict(direction='input', bits=48), 'q': dict(direction='output', bits=48)})
        c['edges'].append(L.edge(['cp_lane', 'q', 7, 18], original_sink, 'final_cp_lane'))
        again, rep = L.apply(c)
        self.assertEqual(again, c)
        self.assertGreater(rep['bit_paths_verified'], 0)

    def test_l17_cohort_parameter_retained(self):
        c = copy.deepcopy(self.new)
        for n, v in c['instances'].items():
            if n.startswith('svg_'):
                v['params']['ID_COHORT'] = 1
        if 'ID_COHORT' in (L.ROOT / L.SOURCES[L.SVG]).read_text():
            again, _ = L.apply(c)
            self.assertEqual(again, c)
        else:
            with self.assertRaisesRegex(ValueError, 'PARTIAL_MIGRATION'):
                L.apply(c)

    def test_explicit_grant_beats_alias_and_covers_faces(self):
        faces = L.rtl_ports()[L.CP]
        g = dict(slots=[])
        pl = {n: dict(m='ot_static_cmd_target', x=200+i*100, y=200, w=60.48, h=60.48, o='R0')
              for i,n in enumerate(sorted(n for n in self.new['instances'] if n.startswith('cp_svg_')))}
        pl['fixed_neighbour'] = dict(x=0,y=0,w=100,h=100,o='R0')
        g, rep = grant(g, self.new, dict(placement=pl))
        self.assertEqual(len(g['slots']), 16)
        self.assertEqual(sum(rep['face_bits'].values()), 895)
        self.assertEqual(set(rep['faces']), set(faces))
        self.assertLess(rep['pin_density_max'], 6)
        again, _ = grant(copy.deepcopy(g), self.new, dict(placement=pl))
        self.assertEqual(again, g)
        slots = {s['name']: s for s in g['slots']}
        self.assertEqual(resolve_slot('cp_svg_SW0', self.new['instances']['cp_svg_SW0'], slots, {}), 'cp_svg_SW0')


if __name__ == '__main__':
    unittest.main()
