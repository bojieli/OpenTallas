"""Fleet-only real-source relay alias regression (no native qualification).

After the alias/default helper fixes are integrated, run on the fleet with:
  KV_PARAMETER_ACTUAL_ROOT=/absolute/frozen/source \\
  KV_ALIAS_ARTIFACT_DIR=/absolute/evidence \\
  python3 -m unittest discover -s tools/qwen_kv_die -p test_kv_expand_alias.py -v

Requires Yosys and the complete selected physical views. The one-relay parent
is a connectivity fixture; its child RTL and every selected view byte come
from ACTUAL. No arithmetic, reset timing, or physical closure is claimed.
There is deliberately no strict positive and no manufactured native receipt.
"""
import contextlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import kv_expand as E
import kv_expand_parameters as P
import kv_bound_netlist as B
import kv_static_die as S

ACTUAL = Path(os.environ.get('KV_PARAMETER_ACTUAL_ROOT', E.ROOT)).resolve()
CORE = 'qkd_astk_rly_296'
LANDED = CORE + '_fl'
CORE_RTL = 'rtl/qwen_sys/split_20261014/qkd_astk_phys.sv'
LANDED_RTL = 'rtl/lib/face_land/qkd_astk_rly_296_fl.sv'
SOURCES = (CORE_RTL, LANDED_RTL, 'rtl/lib/ot_rst_relay.sv', 'rtl/lib/ot_pin_land.sv')
ZERO = "32'sb" + '0' * 32


@contextlib.contextmanager
def cwd(path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


@unittest.skipUnless(os.environ.get('KV_PARAMETER_ACTUAL_ROOT'),
                     'requires pinned actual source root and fleet Yosys')
class RealRelayAlias(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        self.case = self.run / 'case_kv'
        self.case.mkdir(parents=True)
        (self.run / 'libs').mkdir()
        # Resolve the production selection through its real selection function.
        with patch.object(S, 'FACE_LAND_SEL', {'astk_rly_296'}), patch.object(S, 'ROOT', ACTUAL):
            self.view = S.face_land_require_closed(ACTUAL)['astk_rly_296']
            self.assertEqual(S.face_land_rtl('astk_rly_296'), LANDED_RTL)
        self.core_view = 'physical/ref_tile/qkd_astk_rly_296/views/' + CORE
        for rel in SOURCES:
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ACTUAL / rel, dst)
        for rel in (self.view, self.core_view):
            shutil.copytree(ACTUAL / rel, self.root / rel)
        self.source_inventory = self.inventory(self.root, ('rtl', self.view, self.core_view))
        for rel, sha in self.source_inventory.items():
            self.assertEqual(sha, P.sha(ACTUAL / rel), rel)
        self.assertEqual(P.integer_defaults((self.root / CORE_RTL).read_text(), CORE), {})
        self.assertEqual(P.integer_defaults((self.root / LANDED_RTL).read_text(), LANDED), {'MUT': 0})
        _, _, size, ports = E.lef_macro(self.root / self.view / (LANDED + '.lef'))
        self.assertEqual(set(ports), {'ck', 'rst_n', 'a', 'b'})
        self.assertEqual(ports['a']['bits'], set(range(296)))
        self.assertEqual(ports['b']['bits'], set(range(296)))
        _, _, _, original_ports = E.lef_macro(self.root / self.core_view / (CORE + '.lef'))
        self.assertEqual(original_ports, ports)
        self.parent_ports = ports
        declarations = []
        for name, row in sorted(ports.items()):
            bits = row['bits'] - {None}
            width = f'[{max(bits)}:0] ' if bits else ''
            declarations.append(f"{row['dir']} wire {width}{name}")
        self.parent_template = ('module alias_parent (' + ', '.join(declarations) + ');\n'
                                + CORE + ' {override} u_relay ('
                                + ', '.join(f'.{p}({p})' for p in sorted(ports)) + ');\nendmodule\n')
        self.parent = self.root / 'alias_parent.sv'
        self.write_parent()
        wires, conns = [], []
        for name, row in sorted(ports.items()):
            bits = row['bits'] - {None}
            width = max(bits) + 1 if bits else 1
            wires.append(f'  wire [{width-1}:0] n_{name};')
            conns.append(f'.{name}(n_{name})')
        (self.case / 'die.v').write_text('module die;\n' + '\n'.join(wires)
                                       + '\n  alias_frame f (' + ', '.join(conns) + ');\nendmodule\n')
        (self.case / 'die.v.params.json').write_text('{}\n')
        (self.case / 'place.tcl').write_text('ot_mts::place [$_blk findInst f] 0 0 R0\n# ot_mts::place insertion marker\n')
        (self.case / 'elements.lef').write_text(f'MACRO alias_frame\n SIZE {size[0]} BY {size[1]} ;\nEND alias_frame\n')
        (self.run / 'libs/views.json').write_text('{"views":{}}\n')
        self.profiles = {LANDED: dict(parameters={'MUT': 0},
                                     identity=P.artifact_identity(self.root, self.view, LANDED_RTL))}
        self.profile_path = self.root / 'profiles.json'
        self.write_profiles()
        self.rtl = {CORE: CORE_RTL, LANDED: LANDED_RTL}
        patches = [patch.dict(os.environ, {'OT_KV_STATIC': '0', 'OT_KV_PARAM_DIAG': '0'}),
                   patch.object(E, 'ROOT', self.root), patch.object(B, 'ROOT', self.root),
                   patch.object(E, 'VIEWS', {CORE: self.core_view, LANDED: self.view}),
                   patch.object(E, 'RTL', self.rtl), patch.object(E, 'ALIAS', {CORE: LANDED}),
                   patch.object(E, 'frames', lambda: {'alias_frame': dict(
                       plan=lambda c,w,h: (0,0,'R0'), straps=lambda i: {})}),
                   patch.object(E.K, '_set_geometry', lambda *a, **k: None),
                   patch.object(E.K, 'BINDINGS', {'alias_frame': dict(
                       module='alias_parent', file='alias_parent.sv',
                       ports={p: [p] for p in ports})})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        # Runs after each test but before deleting its temporary fixture.
        self.addCleanup(self.save_inventory)

    @staticmethod
    def inventory(root, paths):
        return {str(p.relative_to(root)): P.sha(p) for rel in paths
                for p in sorted((root / rel).rglob('*')) if p.is_file()}

    def save_inventory(self):
        manifest = dict(schema='opentallas.real_alias_fixture.v1', test=self.id(),
                        actual_root=str(ACTUAL), qualification='DIAGNOSTIC_ONLY',
                        sources=self.source_inventory,
                        current_sources=self.inventory(self.root, ('rtl', self.view, self.core_view)),
                        selection_spec_sha256=P.sha(ACTUAL / 'physical/ref_tile/qkd_astk_rly_296/spec.json'),
                        outputs=self.inventory(self.root, ('run', 'bound')))
        dest = os.environ.get('KV_ALIAS_ARTIFACT_DIR')
        if dest:
            path = Path(dest) / self._testMethodName
            path.mkdir(parents=True, exist_ok=True)
            (path / 'inventory.json').write_text(json.dumps(manifest, indent=2) + '\n')
            for rel in ('run/expand.json', 'run/case_kv/die.v', 'run/case_kv/die.v.preexp',
                        'run/case_kv/die.v.params.json', 'bound/die_bound.v', 'bound/bound_netlist.json'):
                src = self.root / rel
                if src.exists():
                    target = path / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
        else:
            print(json.dumps(manifest, sort_keys=True))

    def write_parent(self, override=''):
        self.parent.write_text(self.parent_template.replace('{override}', override))

    def write_profiles(self):
        self.profile_path.write_text(json.dumps(self.profiles))

    def expand(self, diagnostic=True):
        args = ['--run', str(self.run), '--only', 'alias_frame',
                '--parameter-profiles', str(self.profile_path)]
        if diagnostic:
            args.append('--diagnostic-parameter-profiles')
        with patch.object(E, 'elaborate', wraps=E.elaborate) as real:
            result = E.main(args)
            self.assertEqual(real.call_count, 1)
        return result

    def bind(self, diagnostic=True):
        args = [str(self.case / 'die.v'), '--expanded', str(self.run / 'expand.json'),
                '--out-dir', str(self.root / 'bound')]
        if diagnostic:
            args.append('--diagnostic-parameter-profiles')
        # Real rtl_index scans only the copied, complete RTL inputs.
        with cwd(self.root):
            return B.main(args)

    def edit_json(self, relative, edit):
        path = self.run / relative
        obj = json.loads(path.read_text())
        edit(obj)
        path.write_text(json.dumps(obj))

    def test_actual_alias_diagnostic_positive(self):
        self.assertEqual(self.expand(), 0)
        r = json.loads((self.run / 'expand.json').read_text())
        row = r['parameter_instances']['f__u_relay']
        self.assertEqual(row['module'], LANDED)
        self.assertEqual(row['literals'], {'MUT': ZERO})
        self.assertFalse(row['profile']['native_qualified'])
        self.assertIsNone(row['profile']['frozen_receipt'])
        self.assertEqual(r['leaves'][LANDED]['rtl'], LANDED_RTL)
        self.bind()
        text = (self.root / 'bound/die_bound.v').read_text()
        self.assertIn(LANDED + ' #(.MUT(' + ZERO + '))', text)
        self.assertIn('f__u_relay', text)
        with self.assertRaisesRegex(ValueError, 'qualification missing'):
            self.bind(False)

    def test_strict_missing_receipt_refuses_atomically(self):
        before = (self.case / 'die.v').read_bytes()
        with self.assertRaisesRegex(ValueError, 'qualification missing'):
            self.expand(False)
        self.assertEqual((self.case / 'die.v').read_bytes(), before)

    def test_missing_profile_refuses(self):
        self.profiles.clear()
        self.write_profiles()
        with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
            self.expand()
        with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
            self.expand(False)

    def test_missing_ledger_refuses(self):
        self.expand()
        self.edit_json('expand.json', lambda r: r.pop('parameter_instances'))
        with self.assertRaisesRegex(ValueError, 'ledger incomplete'):
            self.bind()

    def test_missing_sidecar_refuses(self):
        self.expand()
        (self.case / 'die.v.params.json').unlink()
        with self.assertRaisesRegex(ValueError, 'sidecar missing/conflicting'):
            self.bind()

    def test_changed_master_refuses(self):
        self.expand()
        p = self.case / 'die.v'
        p.write_text(p.read_text().replace(LANDED + ' f__u_relay', CORE + ' f__u_relay'))
        with self.assertRaisesRegex(ValueError, 'instance/master missing or changed'):
            self.bind()

    def test_changed_mut_refuses(self):
        self.expand()
        self.edit_json('case_kv/die.v.params.json', lambda r: r['f__u_relay'].update(MUT="32'sb" + '0'*31 + '1'))
        with self.assertRaisesRegex(ValueError, 'sidecar missing/conflicting'):
            self.bind()

    def test_mut_profile_refuses(self):
        self.profiles[LANDED]['parameters']['MUT'] = 1
        self.write_profiles()
        with self.assertRaisesRegex(ValueError, 'profile/source/view mismatch'):
            self.expand()

    def test_stale_rtl_refuses(self):
        self.expand()
        p = self.root / LANDED_RTL
        p.write_text(p.read_text() + '\n// fixture mutation\n')
        with self.assertRaisesRegex(ValueError, 'source/view artifact changed'):
            self.bind()

    def test_stale_view_refuses(self):
        self.expand()
        p = self.root / self.view / (LANDED + '_tt.lib')
        p.write_text(p.read_text() + '\n/* fixture mutation */\n')
        with self.assertRaisesRegex(ValueError, 'source/view artifact changed'):
            self.bind()

    def test_absent_module_refuses(self):
        p = self.root / LANDED_RTL
        p.write_text(p.read_text().replace('module ' + LANDED + ' ', 'module missing_landed '))
        with self.assertRaisesRegex(ValueError, 'requested module absent'):
            self.expand()

    def test_inherited_alias_override_refuses(self):
        self.write_parent('#(.MUT(0))')
        with self.assertRaisesRegex(ValueError, 'explicit compatible parameter mapping required'):
            self.expand()


if __name__ == '__main__':
    unittest.main()
