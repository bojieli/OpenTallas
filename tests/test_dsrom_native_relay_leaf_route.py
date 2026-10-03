import gzip,json,sys,unittest,shlex
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_native_relay_leaf_route as R

class NativeLeaf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads(gzip.decompress((R.BASE/'inputs/leaf.json.gz').read_bytes()))
        cls.m=R.construct(cls.p)
    def test_full_fanout(self):
        self.assertEqual(len(self.m['branches']),8)
        self.assertEqual(len(self.m['cells']),17)
    def test_unique_sites(self):
        self.assertEqual(len({tuple(c['bbox_DBU']) for c in self.m['cells']}),17)
    def test_both_native_contacts(self):
        for b in self.m['branches']:
            self.assertLessEqual(b['first_C_fF'],b['first_limit_fF']+1e-12)
            self.assertLessEqual(b['last_C_fF'],b['last_limit_fF']+1e-12)
    def test_truncated_not_admitted(self):
        p=dict(self.p,tasks=self.p['tasks'][:7])
        with self.assertRaises(ValueError): R.construct(p)
    def test_missing_sites_not_admitted(self):
        p=dict(self.p,sites=self.p['sites'][:1])
        with self.assertRaises(ValueError): R.construct(p)
    def test_scope_not_parent(self):
        self.assertFalse(self.m['full_parent_build_admitted'])
        self.assertFalse(self.m['reset_construction_covered'])
        self.assertEqual(self.m['extra_architectural_cycles'],0)
    def test_pinned_driver_recipe(self):
        import run_abi3_physical as driver
        script=(R.ROOT/'physical/dsrom_native_relay_20261003/launch_epyc.sh').read_text()
        args=shlex.split(next(l for l in script.splitlines() if l.startswith('python3 tools/')))[2:]
        cleaned=[];i=0
        while i<len(args):
            if args[i]=='--macro-track-gate':i+=1
            elif args[i] in ('--persistent-workdir','--launch-receipt'):i+=2
            else:cleaned.append(args[i]);i+=1
        parsed=driver.build_parser().parse_args(cleaned)
        self.assertEqual(parsed.orfs_corner,'WC')
        self.assertEqual(parsed.clock_uncertainty_hold_ns,.025)

if __name__=='__main__':unittest.main()
