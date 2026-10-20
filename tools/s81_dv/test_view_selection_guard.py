"""Synthetic fixture tests only: these bytes never qualify an actual macro."""
import copy
import json
import unittest
import view_selection_guard as G


class GuardTests(unittest.TestCase):
    def fixture(self, kind='routed_hardmacro'):
        self.blobs = {}; self.commit = '1' * 40
        def put(path, obj):
            raw = obj if isinstance(obj, bytes) else json.dumps(obj, sort_keys=True).encode()
            self.blobs[self.commit, path] = raw
            return dict(commit=self.commit, path=path, sha256=G.sha(raw))
        self.put = put; self.read = lambda c, p: self.blobs.get((c, p))
        self.chosen = {'fixture_only': dict(commit=self.commit, directory='physical/ref_tile/fixture/views/fixture_only')}
        directory = self.chosen['fixture_only']['directory']
        arts = {key: put(directory + '/fixture_only' + suffix, key.encode()) for key, suffix in [('lef', '.lef'), ('lib_tt', '_tt.lib'), ('lib_ff', '_ff.lib'), ('lib_ss', '_ss.lib')]}
        extra = ['source_inventory', 'params', 'ports', 'clock_age_contract']
        extra += ['route_odb', 'route_v', 'route_spef', 'route_sdc', 'abstract', 'insertion'] if kind == 'routed_hardmacro' else ['model', 'pg_pin_calibration']
        arts.update({k: put('fixture/' + k, k.encode()) for k in extra})
        contracts = {k: put('fixture/contract_' + k, k.encode()) for k in ['source', 'params', 'ports', 'clock_age']}
        ent = dict(master='fixture_only', proof_kind=kind, selection=self.chosen['fixture_only'], artifacts=arts, contracts=contracts)
        self.ev = dict(schema='opentallas.s81_native_qualification.v1', master='fixture_only', proof_kind=kind, status='PASS', complete=True, artifacts=arts, contracts=contracts, checks={k: dict(status='PASS', complete=True, checked=1, errors=0) for k in ['pg', 'grid', 'reach', 'roles', 'clock', 'phase', 'ports', 'parameters', 'source', 'age']}, corners={c: dict(status='PASS', complete=True, clock_rise_ps=1, clock_fall_ps=2, clock_rise_spread_ps=0, clock_fall_spread_ps=0) for c in ['tt', 'ff', 'ss']})
        ent['native_receipt'] = put('fixture/native.json', self.ev)
        self.context = {'fixture_only_GEN_input': 'a' * 64}; self.holds = dict(schema='opentallas.s81_component_holds.v1', denials=[])
        self.manifest = dict(schema='opentallas.s81_release_views.v1', context=self.context, holds_sha256=G.content_sha(self.holds), masters={'fixture_only': ent})
        self.approve()

    def approve(self):
        self.approval = self.put('fixture/ROOT_APPROVAL.json', dict(schema='opentallas.s81_root_selection_approval.v1', owner='ROOT', status='APPROVED', scope='exact-source-view-selection', manifest_sha256=G.content_sha(self.manifest), context=self.context))

    def qualify(self):
        return G.qualify(self.manifest, self.holds, self.approval, self.context, self.chosen, self.read)

    def refreshed_ev(self):
        self.manifest['masters']['fixture_only']['native_receipt'] = self.put('fixture/native.json', self.ev)
        self.approve()

    def test_positive_all_types(self):
        for kind in ['routed_hardmacro', 'sram_model', 'primitive_model']:
            self.fixture(kind); self.assertEqual(self.qualify()['status'], 'ROOT_APPROVED_EXACT_SELECTION_ONLY')

    def test_causals(self):
        mutations = {
            'wrong_artifact': lambda: self.blobs.__setitem__((self.commit, self.manifest['masters']['fixture_only']['artifacts']['lef']['path']), b'changed'),
            'missing_master': lambda: self.manifest['masters'].clear(),
            'unknown_type': lambda: self.manifest['masters']['fixture_only'].__setitem__('proof_kind', 'CLOSED'),
            'root_missing': lambda: self.blobs.pop((self.commit, self.approval['path'])),
            'root_context_changed': lambda: self.context.__setitem__('fixture_only_GEN_input', 'b' * 64),
            'missing_route': lambda: self.manifest['masters']['fixture_only']['artifacts'].pop('route_odb'),
            'source_changed': lambda: self.chosen['fixture_only'].__setitem__('commit', '2' * 40),
            'alias_ref': lambda: self.manifest['masters']['fixture_only']['artifacts']['lef'].__setitem__('commit', 'main'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.fixture(); mutate()
                with self.assertRaises((G.SelectionRefused, ValueError, KeyError)): self.qualify()

    def test_rehashed_native_failures(self):
        for field in ['pg', 'grid', 'reach', 'roles', 'clock', 'phase', 'ports', 'parameters', 'source', 'age']:
            self.fixture(); self.ev['checks'][field]['errors'] = 1; self.refreshed_ev()
            with self.assertRaises(G.SelectionRefused): self.qualify()
        for mutate in [lambda e: e['checks'].pop('clock'), lambda e: e['checks']['pg'].__setitem__('checked', 0), lambda e: e['corners'].pop('ss'), lambda e: e['corners']['tt'].__setitem__('clock_fall_ps', float('nan')), lambda e: e.__setitem__('status', 'CLOSED'), lambda e: e['contracts'].__setitem__('source', {})]:
            self.fixture(); mutate(self.ev); self.refreshed_ev()
            with self.assertRaises(G.SelectionRefused): self.qualify()

    def test_holds_bind_identity_and_allow_new_independent_identity(self):
        for kind in ['artifact_sha256', 'source_commit']:
            self.fixture(); den = dict(kind=kind, reason='fixture rejected native evidence')
            den.update(dict(sha256=self.manifest['masters']['fixture_only']['artifacts']['lef']['sha256']) if kind=='artifact_sha256' else dict(master='fixture_only', commit=self.commit))
            self.holds['denials'] = [den]; self.manifest['holds_sha256'] = G.content_sha(self.holds); self.approve()
            with self.assertRaises(G.SelectionRefused): self.qualify()
            if kind=='artifact_sha256': den['sha256'] = '9' * 64
            else: den['commit'] = '9' * 40
            self.manifest['holds_sha256'] = G.content_sha(self.holds); self.approve(); self.qualify()


if __name__ == '__main__':
    unittest.main()
