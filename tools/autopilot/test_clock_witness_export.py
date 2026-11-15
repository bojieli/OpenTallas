"""A view copy retains real witness files and refuses changed native/ETM inputs."""
import datetime
import json
from pathlib import Path
import shutil
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
from test_child_clock_witness import NativeWitness
import autopilot as AP
import export_view as EV


class RetainedView(unittest.TestCase):
    def setUp(self):
        self.native = NativeWitness()
        self.native.setUp()
        self.addCleanup(self.native.doCleanups)
        self.native.record()
        self.root, self.base, self.witness = self.native.root, self.native.base, self.native.out
        self.kit = self.root / 'kit'
        views = self.kit / 'views'; views.mkdir(parents=True)
        (self.kit / 'freeze.json').write_text(json.dumps({'module':'leaf','outline_um':[10,10],'pins_canon_sha256':'a'*64}))
        (views / 'leaf.lef').write_text('MACRO leaf\nEND leaf\n')
        for c in ['tt','ff']:
            shutil.copyfile(self.witness / f'leaf_{c}.lib', views / f'leaf_{c}.lib')
        self.signoff = self.kit / 'signoff'; self.signoff.mkdir()
        (self.signoff / 'signoff.json').write_text(json.dumps({'verdict':'SIGNED','generated':datetime.datetime.now().astimezone().isoformat(),'corners':{}}))

    def probe(self):
        return EV.run_probe(AP.PROBE_VIEW_READ, {'kit':str(self.kit),'base':str(self.base),'signoff_dir':str(self.signoff),'clock_witness_dir':str(self.witness)})

    def test_copy_preserves_payload_and_exact_etm_binding_without_qualification(self):
        result = EV.export(self.kit, self.signoff/'signoff.json', self.root/'published', 's81', base=str(self.base), clock_witness_dir=self.witness)
        self.assertTrue(result['complete'])
        self.assertEqual(result['child_clock_witness']['status'], 'RETAINED')
        self.assertEqual(result['child_clock_witness']['qualification'], 'NOT_ASSERTED')
        view = Path(result['view'])
        self.assertEqual((view/'child_clock_tt_pairs.tsv').read_bytes(), (self.witness/'child_clock_tt_pairs.tsv').read_bytes())
        self.assertEqual(result['child_clock_witness']['view_lib_sha256']['ff'], EV.sha256(view/'leaf_ff.lib'))

    def test_changed_native_netlist_refuses_graph_copy(self):
        (self.base/'6_final.v').write_text('different native source')
        result = self.probe()
        self.assertEqual(result['clock_witness']['status'], 'FAILED')
        self.assertNotIn('child_clock_witness.json', result['files'])

    def test_sampled_pairs_cannot_stand_in_for_full_graph_payload(self):
        p = self.witness/'child_clock_witness.json'
        doc=json.loads(p.read_text()); doc['corners']['tt']['files'].pop('child_clock_tt_pairs.tsv')
        p.write_text(json.dumps(doc))
        self.assertEqual(self.probe()['clock_witness']['status'], 'FAILED')

    def test_changed_view_liberty_does_not_inherit_retained_clock_binding(self):
        (self.kit/'views/leaf_ff.lib').write_text('different child timing model')
        result = EV.export(self.kit, self.signoff/'signoff.json', self.root/'published', 's81', base=str(self.base), clock_witness_dir=self.witness)
        self.assertEqual(result['child_clock_witness']['status'], 'FAILED')
        self.assertTrue(result['complete'])  # original view/signoff decisions unchanged


if __name__ == '__main__':
    unittest.main()
