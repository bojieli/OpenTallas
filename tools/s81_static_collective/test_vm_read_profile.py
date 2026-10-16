"""Static VM lead binding: advance reads without moving computation or done."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('resetpins_image',Path(__file__).parent/'resetpins/controller_image.py')
image=importlib.util.module_from_spec(spec);spec.loader.exec_module(image)


class VmReadProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests={}
        with tempfile.TemporaryDirectory() as tmp:
            for lead in (14,18):
                out=Path(tmp)/str(lead)
                subprocess.run([sys.executable,str(ROOT/'tools/s81_static_collective/build_slab_fixture.py'),
                                '--out',str(out),'--vm-read-edges',str(lead)],check=True,capture_output=True)
                cls.requests[lead]=json.loads((out/'request.json').read_text())

    def test_only_read_reservations_advance(self):
        old,new=self.requests[14],self.requests[18]
        self.assertEqual(len(old['read_reservations']),len(new['read_reservations']))
        for a,b in zip(old['read_reservations'],new['read_reservations']):
            self.assertEqual(a['edge']-4,b['edge'])
            self.assertEqual((a['row'],a['consumer']),(b['row'],b['consumer']))
        for a,b in zip(old['cycles'],new['cycles']):
            a,b=copy.deepcopy(a),copy.deepcopy(b)
            for c in (a,b):
                c['controls'].pop('read_slot');c['controls'].pop('read_row')
            self.assertEqual(a,b)

    def test_wrong_profile_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'unbound physical latency profile'):
            image.compile_image(self.requests[18],ROOT)

    def test_wrong_reservation_detected(self):
        bad=copy.deepcopy(self.requests[18]);bad['read_reservations'][0]['edge']+=1
        with self.assertRaises(ValueError):
            image.compile_image(bad,ROOT,latency_profile=bad['latencies'])

    def test_cannot_change_unrelated_latencies(self):
        bad=copy.deepcopy(self.requests[18]);bad['latencies']['issue_to_gather_edges']+=1
        with self.assertRaisesRegex(ValueError,'unsupported non-VM latency change'):
            image.compile_image(bad,ROOT,latency_profile=bad['latencies'])


if __name__=='__main__':unittest.main()
