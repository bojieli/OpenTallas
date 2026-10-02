from pathlib import Path
import resource,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import experiment_unlimited_fsize_policy as P
class Policy(unittest.TestCase):
    def test_only_fsize_property_changes_no_cap_relaxation(self):
        x={'LimitFSIZE':512*2**20,'MemoryMax':64*2**30,'MemorySwapMax':0,'TasksMax':48,
           'CPUAffinity':'8-23','RuntimeMaxSec':900,'KillMode':'control-group','LimitCORE':0}
        y=P.systemd_properties(x)
        self.assertEqual(y['LimitFSIZE'],'infinity')
        self.assertEqual({k:v for k,v in y.items() if k!='LimitFSIZE'},
                         {k:v for k,v in x.items() if k!='LimitFSIZE'})
        self.assertEqual(x['LimitFSIZE'],512*2**20)
    def test_service_and_kernel_both_soft_hard_checked(self):
        s={'LimitFSIZE':'infinity','LimitFSIZESoft':'infinity'}
        self.assertEqual(P.check_service_and_process(s,(-1,-1))['file_size_limit'],'unlimited')
        for lim in [(512,-1),(-1,512),(512,512)]:
            with self.assertRaises(ValueError):P.check_service_and_process(s,lim)
        for k in s:
            t=dict(s);t[k]='536870912'
            with self.assertRaises(ValueError):P.check_service_and_process(t,(-1,-1))
    def test_prlimit_container_and_service_bypass_controls(self):
        for argv in [['prlimit','--fsize=536870912','--','g++'],['prlimit','--fsize','512'],
          ['docker','run','--ulimit','fsize=1024:1024'],['systemd-run','--property=LimitFSIZE=512'],
          ['ulimit','-f','100']]:
            with self.assertRaises(ValueError):P.check_exec_argv(argv)
        self.assertTrue(P.check_exec_argv(['prlimit','--as=123','--','g++']))
        self.assertTrue(P.check_exec_argv(['systemd-run','--property=LimitFSIZE=infinity']))
        self.assertTrue(P.check_exec_argv(['docker','run','--ulimit','fsize=-1:-1']))
        with self.assertRaises(ValueError):P.check_exec_argv(['prlimit','--fsize=unlimited:512'])
    def test_aggregate_budget_allows_single_large_build_artifact(self):
        x=P.aggregate_disk_budget(12*2**30,100*2**30,24*2**30,5*2**30)
        self.assertIsNone(x['per_file_cap'])
        self.assertEqual(x['enforcement'],'sampled aggregate accounting; overshoot possible')
        with self.assertRaises(ValueError):P.aggregate_disk_budget(12*2**30,100*2**30,24*2**30,13*2**30)
        with self.assertRaises(ValueError):P.aggregate_disk_budget(12*2**30,35*2**30,24*2**30,0)
    def test_no_process_limit_mutation(self):
        before=resource.getrlimit(resource.RLIMIT_FSIZE)
        P.check_service_and_process({'LimitFSIZE':'infinity','LimitFSIZESoft':'infinity'},(-1,-1))
        self.assertEqual(before,resource.getrlimit(resource.RLIMIT_FSIZE))
if __name__=='__main__':unittest.main()
