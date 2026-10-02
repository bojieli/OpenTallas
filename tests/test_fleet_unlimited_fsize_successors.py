from pathlib import Path
import ast,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import run_hbm_qwen_runtime_unlimited_fsize_prepare as R
import prepare_hbm_qwen_runtime_unlimited_fsize_prepare as P
import experiment_unlimited_fsize_exec as E

class Successors(unittest.TestCase):
    def test_future_Q_caps_remove_only_perfile_with_fresh_schema(self):
        plan=json.loads((ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002/successor_source_plan_final.json').read_text())
        caps=P.caps_for('Qwen')
        self.assertNotIn('per_file_bytes',caps)
        self.assertEqual(caps['file_size_limit'],'unlimited')
        for k,v in plan['Q_caps_preserved_except_removed_per_file'].items():self.assertEqual(caps[k],v)
        self.assertNotEqual(P.GO_SCHEMA,'opentallas.H1.Qwen-runtime-r11.GO.v1')

    def test_future_Q_limit_validation_retains_memswap_affinity_wall(self):
        caps=P.caps_for('Qwen');info={'LimitFSIZE':'infinity','LimitFSIZESoft':'infinity','OOMPolicy':'stop','RuntimeMaxUSec':str(caps['whole_wall_s'])+'s'}
        R.validate_limits('fresh.service','/fresh.service',str(caps['memory_bytes']),'0',caps['cpus'],info)
        for k,v in [('LimitFSIZE','3221225472'),('LimitFSIZESoft','3221225472'),('OOMPolicy','continue'),('RuntimeMaxUSec','1s')]:
            bad=dict(info);bad[k]=v
            with self.subTest(k=k):
                with self.assertRaises(ValueError):R.validate_limits('fresh.service','/fresh.service',str(caps['memory_bytes']),'0',caps['cpus'],bad)
        with self.assertRaises(ValueError):R.validate_limits('fresh.service','/fresh.service',str(caps['memory_bytes']),'1',caps['cpus'],info)
        with self.assertRaises(ValueError):R.validate_limits('fresh.service','/fresh.service',str(caps['memory_bytes']),'0',[8],info)

    def test_old_GO_schema_and_unreviewed_resource_refused(self):
        with self.assertRaises(ValueError):R.validate_go({'schema':'opentallas.H1.Qwen-runtime-r11.GO.v1'},Path('/unused'),'old')
        with self.assertRaisesRegex(ValueError,'resource admission'):P.prepare_target('Qwen')

    def test_future_copy_provenance_and_source_bytes_bound(self):
        plan=json.loads((ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002/successor_source_plan_final.json').read_text())
        for name,d in plan['future_paths'].items():
            path=ROOT/name if name.startswith('tools/') else ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002/launchers'/name
            ast.parse(path.read_text())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),d['future_sha256'])
        text=(ROOT/'tools/hbm_qwen_binary_reuse_unlimited_fsize_prepare.py').read_text()
        self.assertIn("oldgo['runner_caps']!=p['runner_caps']",text)
        self.assertIn("exclusive fresh binary destination required",text)
        self.assertIn("qualified original build worker must remain clean and frozen",text)

    def test_remote_future_guard_retains_holds_and_live_ledger(self):
        base=ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002/launchers'
        text=(base/'remote_gate_unlimited_guarded.py').read_text()
        self.assertIn("vm.get('disabled') or vm.get('admission_hold_owner')=='user'",text)
        self.assertIn("R=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002')",text)
        self.assertIn("plan.get('file_size_policy')!='unlimited'",text)
        self.assertIn('tools/experiment_unlimited_fsize_exec.py',text)
        launch=(base/'remote_gate_unlimited.base.py').read_text()
        self.assertIn('--ulimit fsize=-1:-1',launch)
        self.assertIn('prlimit --fsize=unlimited:unlimited',launch)
        self.assertIn('experiment_unlimited_fsize_exec.py',launch)

    def test_kernel_entry_rejects_finite_inheritance_and_exec_overrides(self):
        self.assertEqual(E.prepare_argv(['--','g++','-c','foo.cc'],(-1,-1)),['g++','-c','foo.cc'])
        for lim in [(1,1),(-1,1),(1,-1)]:
            with self.assertRaises(ValueError):E.prepare_argv(['--','g++'],lim)
        with self.assertRaises(ValueError):E.prepare_argv(['--','prlimit','--fsize=100','g++'],(-1,-1))
        with self.assertRaises(ValueError):E.prepare_argv(['g++'],(-1,-1))

    def test_remote_receipt_and_retirement_no_unqualified_free_host(self):
        p=ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002'
        d=json.loads((p/'fleet_admission_screens.json').read_text())
        for held in d['PVE2_PVE3_registry_holds'].values():self.assertTrue(held['disabled']);self.assertEqual(held['admission_hold_owner'],'user')
        for x in d['hosts']['ot-pve1']['candidate_screens_at_probe_time']:self.assertFalse(x['admit'])
        v=d['hosts']['155.103.253.226']['candidate_screens_at_probe_time']
        self.assertTrue(next(x for x in v if x['request_GiB']==64)['admit'])
        self.assertFalse(next(x for x in v if x['request_GiB']==94)['admit'])
        s=json.loads((p/'source_retention.json').read_text())
        self.assertEqual(s['builds_removed'],0)
        for root in s['roots']:
            if root.get('HEAD'):self.assertTrue(root['committed_source_retained_in_refs']);self.assertFalse(root['status'])
            self.assertFalse(root['retirement_allowed'])
    def test_VM48_resource_screen_is_not_lease_or_launch(self):
        p=ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002'
        d=json.loads((p/'Hubble_VM48_admission_model.json').read_text())
        self.assertTrue(d['screens_GiB_at_probe_time']['80']['admit'])
        for g in ['88','94']:
            self.assertFalse(d['screens_GiB_at_probe_time'][g]['admit'])
            self.assertIn('LIVE_RAM_RESERVE',d['screens_GiB_at_probe_time'][g]['reasons'])
        self.assertFalse(d['launch_authorized']);self.assertTrue(d['screen_is_not_reservation'])
        self.assertEqual(d['leases_acquired'],0)
        self.assertTrue(d['pids_cap_48_cannot_be_assumed_sufficient_for_48_CXX_workers'])

    def test_GCC11_container_tools_match_but_libc_not_reuse_qualified(self):
        p=ROOT/'results/uarch/fleet_unlimited_fsize_milestone_20261002'
        d=json.loads((p/'Hubble_VM48_container_lease_probe.json').read_text())
        a=[json.loads(x) for x in d['local_tool_probe']['stdout'].splitlines()]
        b=[json.loads(x) for x in d['container_tool_probe']['stdout'].splitlines()]
        for name in ['compiler','cc1plus','linker','make','libstdc++.so']:
            self.assertEqual(a[0][name]['sha256'],b[0][name]['sha256'])
        self.assertNotEqual(a[1]['libc']['sha256'],b[1]['libc']['sha256'])
        self.assertEqual(d['experiment_launches'],0);self.assertEqual(d['design_compilations'],0)
        h=json.loads((p/'Hubble_VM48_header_comparison.json').read_text())['comparison']
        for root in ['/usr/include/c++/11','/usr/include/x86_64-linux-gnu/c++/11']:
            self.assertEqual(h[root]['local_tree_sha256'],h[root]['container_tree_sha256'])
        self.assertTrue(h['/usr/include']['local_only'])

if __name__=='__main__':unittest.main()
