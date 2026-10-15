import copy
import hashlib
import json
import unittest
import master_identity as M


class Repo:
    def __init__(self): self.files = {}
    def read(self, path): return self.files.get(path)


def row(name, status='not started (open)'):
    return dict(element=name, category=status, variants=[], jobs=1, live=0, failed=0, closed_jobs=0,
                dies=[], best={'job': name}, native=[{'verdict': 'FAIL'}])


class Identity(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.files['a.sv'] = 'module a(input wire clk); child u(.clk(clk)); endmodule'
        body = M.module_body(self.repo.read('a.sv'), 'a')
        self.proof = dict(element='a', path='a.sv', module='a',
                          body_sha256=hashlib.sha256(M.normalized(body).encode()).hexdigest())

    def test_composition_preserves_open_integration_and_all_evidence(self):
        r = row('a')
        independent, integration, receipt = M.classify([r], self.repo, dict(compositions=[self.proof]))
        self.assertEqual(independent, [])
        self.assertEqual(integration[0]['native'], r['native'])
        self.assertEqual(integration[0]['category'], r['category'])
        self.assertTrue(integration[0]['integration_status'].startswith('OPEN'))
        self.assertNotIn('qualification_scope', r)
        self.assertEqual(receipt['compositions'], 1)

    def test_changed_source_or_own_state_is_never_hidden(self):
        self.repo.files['a.sv'] = 'module a; reg q; always @(posedge clk) q <= d; endmodule'
        a, b, receipt = M.classify([row('a')], self.repo, dict(compositions=[self.proof]))
        self.assertEqual(len(a), 1); self.assertEqual(b, []); self.assertTrue(receipt['errors'])
        self.proof['body_sha256'] = hashlib.sha256(M.normalized(M.module_body(self.repo.read('a.sv'), 'a')).encode()).hexdigest()
        a, b, receipt = M.classify([row('a')], self.repo, dict(compositions=[self.proof]))
        self.assertEqual(len(a), 1); self.assertTrue(receipt['errors'])

    def replica_fixture(self):
        members = []
        for n in ('a', 'b'):
            path, kit = n + '.sv', 'kit_' + n
            self.repo.files[path] = 'module ' + n + '(input wire clk); child #(.W(147)) u(.clk(clk)); endmodule'
            self.repo.files[kit + '/spec.json'] = json.dumps(dict(top=n, name=kit, params={'W':147}, pins={'E':['q']}))
            for f in ('floorplan.json', 'clock.sdc', 'signoff.sdc', 'kit.env'):
                self.repo.files[kit + '/' + f] = json.dumps({'name': kit, 'top':n, 'pins':[1,2]}) if f.endswith('.json') else n + ' ' + kit + ' period833'
            members.append(dict(element=n, path=path, module=n, kit=kit))
        return dict(replica_groups=[dict(canonical='a', members=members)])

    def test_exact_replica_keeps_two_records_and_jobs_one_master(self):
        cfg = self.replica_fixture(); a, b, receipt = M.classify([row('a'),row('b','closed (TT era)')], self.repo, cfg)
        self.assertEqual(len(a), 1); self.assertEqual(a[0]['element'], 'a')
        self.assertEqual(a[0]['jobs'],2); self.assertEqual(len(a[0]['replica_records']),2)
        self.assertEqual(a[0]['best']['job'],'b'); self.assertEqual(receipt['alias_rows_removed'],1)
        self.assertEqual(a[0]['native'],[{'verdict':'FAIL'}])

    def test_parameters_pins_constraints_or_missing_proof_keep_distinct(self):
        for path in ('b.sv','kit_b/spec.json','kit_b/signoff.sdc','kit_b/floorplan.json'):
            cfg = self.replica_fixture(); self.repo.files[path] = self.repo.files[path].replace('147','188') if path=='b.sv' else self.repo.files[path].replace('833','900') if path.endswith('.sdc') else self.repo.files[path].replace('"q"','"x"') if path.endswith('spec.json') else self.repo.files[path].replace('[1, 2]','[1, 3]')
            a,b,r = M.classify([row('a'),row('b')],self.repo,cfg)
            self.assertEqual(len(a),2,path); self.assertTrue(r['errors'])
        cfg=self.replica_fixture();del self.repo.files['kit_b/clock.sdc']
        a,b,r=M.classify([row('a'),row('b')],self.repo,cfg);self.assertEqual(len(a),2)

    def test_reviewed_view_reuse_checks_every_source_view_and_original_verdict(self):
        digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
        self.repo.files['dep.sv'] = 'exact dependency'
        proof = dict(status='EXACT_IMPLEMENTATION_REUSE', old_master='a', master='b', params={'LAT':8},
            cycles=8, clock_roots=1, from_job='closedjob', TT_setup_ps=257.13, FF_hold_ps=25.23, DRC=0,
            transitive_dependencies_byte_equal={'dep.sv':digest('exact dependency')},
            routed_netlist_new_sha256=digest('module b; endmodule'))
        self.repo.files['proof.json'] = json.dumps(proof)
        records={}
        for filename in ['b.lef','b_tt.lib','b_ff.lib','b_ss.lib'] + ['e%d.log'%n for n in range(9)]:
            oldname=filename.replace('b.', 'a.').replace('b_', 'a_')
            old = 'a view' if filename.endswith(('.lef','.lib')) else 'same data'
            new = 'b view' if filename.endswith(('.lef','.lib')) else 'same data'
            self.repo.files['old/'+oldname]=old;self.repo.files['new/'+filename]=new
            records[filename]=dict(from_sha256=digest(old),sha256=digest(new),**{'from':oldname})
        self.repo.files['new/renamed_from.json']=json.dumps(dict(from_master='a',master='b',files=records))
        self.repo.files['new/b.v']='module b; endmodule'
        group=dict(members=[{'element':'a'},{'element':'b'}],view_reuse=dict(proof='proof.json',proof_sha256=digest(self.repo.files['proof.json']),old_view='old',new_view='new'))
        prior=row('a','closed (TT era)');prior['best']=dict(job='closedjob',tt=257.13,ff=25.23,drc=0)
        M.view_reuse_identity(self.repo,group,[prior,row('b')])
        self.repo.files['dep.sv']='changed dependency'
        with self.assertRaisesRegex(ValueError,'transitive'):
            M.view_reuse_identity(self.repo,group,[prior,row('b')])
        self.repo.files['dep.sv']='exact dependency';self.repo.files['new/b_tt.lib']='changed timing'
        with self.assertRaisesRegex(ValueError,'view bytes'):
            M.view_reuse_identity(self.repo,group,[prior,row('b')])
        prior['category']='needs redesign (no live job)'
        with self.assertRaisesRegex(ValueError,'CLOSED'):
            M.view_reuse_identity(self.repo,group,[prior,row('b')])

    def test_covered_internal_requires_every_current_parent_and_resolved_variant(self):
        self.repo.files['source.sv']='current source'
        parents={};runs=[]
        for name,width in [('SE',147),('NE',147),('NW',187),('SW',202)]:
            parents[name]=row(name,'closed (TT era)');parents[name]['best']['job']=name+'job'
            runs.append(dict(master=name,parent_job=name+'job',params={'W':width,'MUT':0},
                actual_netlist_modules=[name],generic_calendar_cell_instances=0,
                flattened_u_programme_references=3000,actual_1024x256_SRAM_instances=1,netlist_sha256='a'*64))
        proof=dict(schema='opentallas.covered_internal_module.v1',element='generic',
            current_source_sha256={'source.sv':hashlib.sha256(b'current source').hexdigest()},parent_runs=runs)
        text=json.dumps(proof);self.repo.files['coverage.json']=text
        entry=dict(proof='coverage.json',proof_sha256=hashlib.sha256(text.encode()).hexdigest())
        r=row('generic');r['dies']=[{'parents':['NE','NW','SE','SW']}]
        M.covered_internal_identity(self.repo,entry,r,parents)
        r['dies'][0]['parents'].append('other')
        with self.assertRaisesRegex(ValueError,'uncovered'):
            M.covered_internal_identity(self.repo,entry,r,parents)
        r['dies'][0]['parents'].pop();self.repo.files['source.sv']='new version'
        with self.assertRaisesRegex(ValueError,'source changed'):
            M.covered_internal_identity(self.repo,entry,r,parents)

    def test_candidate_abi_never_closes_current_incompatible_contract(self):
        r = row('a','closed (TT era)');r['best']['job']='candidate105'
        proof=dict(self.proof,candidate_job='candidate105',warning='current64 not covered by candidate105')
        a,b,receipt=M.classify([r],self.repo,dict(contract_mismatches=[proof]))
        self.assertEqual(a[0]['category'],'not started (open)')
        self.assertEqual(a[0]['candidate_component_record']['category'],'closed (TT era)')
        self.assertEqual(a[0]['candidate_component_record']['best']['job'],'candidate105')
        self.assertIsNone(a[0]['best']['job']);self.assertEqual(receipt['contract_mismatches'],['a'])
        self.assertEqual(r['category'],'closed (TT era)')
        r['best']['job']='current64'
        a,b,receipt=M.classify([r],self.repo,dict(contract_mismatches=[proof]))
        self.assertEqual(a[0]['category'],'closed (TT era)')


if __name__ == '__main__': unittest.main()
