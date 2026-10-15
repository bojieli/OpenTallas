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


if __name__ == '__main__': unittest.main()
