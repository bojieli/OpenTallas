"""Real expansion main -> real Yosys -> sidecar -> native binder regression.

Run on fleet; the fixture uses actual PV integer declarations/defaults and
intended profiles, with two-pin bodies (no arithmetic/physical qualification).
"""
import copy
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import kv_expand as E
import kv_expand_parameters as P
import importlib.util
_spec = importlib.util.spec_from_file_location('tested_kv_bound_netlist', Path(__file__).with_name('kv_bound_netlist.py'))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

ACTUAL = Path(os.environ.get('KV_PARAMETER_ACTUAL_ROOT', Path(__file__).resolve().parents[2]))
MODULES = {'ot_qwen_tp8_pv_slice_t': dict(RESET_PIN=1),
           'ot_qwen_tp8_pv_join_t': dict(RESET_PIN=1),
           'ot_qwen_tp8_pv_wide_ctl_tb': dict(RESET_PIN=1, TRUNK_D=54, FLAG_D=58, FIRST_INPUT_AGE=127)}


@unittest.skipUnless(os.environ.get("KV_PARAMETER_ACTUAL_ROOT"), "fleet fixture requires pinned actual source root")
class ExpansionParameters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'run'
        case = self.run / 'case_kv'
        libs = self.run / 'libs'
        case.mkdir(parents=True); libs.mkdir()
        self.rtl, self.views, self.profiles = {}, {}, {}
        children = []
        for i, (mod, overrides) in enumerate(MODULES.items()):
            src = ACTUAL / 'rtl/hdc/nearhbm' / ('ot_qwen_tp8_pv_wide_ctl_tb.sv' if mod.endswith('_tb') else 'ot_qwen_tp8_pv_wide_pair.sv')
            defaults = P.integer_defaults(src.read_text(), mod)
            file = 'rtl/' + mod + '.sv'
            (self.root / 'rtl').mkdir(exist_ok=True)
            declarations = ', '.join(f'parameter integer {k}={v}' for k, v in defaults.items())
            (self.root / file).write_text(f'module {mod} #({declarations})(input wire a,output wire y); assign y=a; endmodule\n')
            vd = 'views/' + mod
            d = self.root / vd; d.mkdir(parents=True)
            (d / (mod + '.lef')).write_text(f'MACRO {mod}\n SIZE 1 BY 1 ;\n  PIN a\n DIRECTION INPUT ;\n  END a\n  PIN y\n DIRECTION OUTPUT ;\n  END y\nEND {mod}\n')
            for c in ('tt', 'ff'):
                (d / (mod + '_' + c + '.lib')).write_text('library (fixture) {}\n')
            (d / 'insertion.json').write_text('{}\n')
            self.rtl[mod] = file; self.views[mod] = vd
            self.profiles[mod] = dict(parameters=dict(defaults, **overrides), identity=P.artifact_identity(self.root, vd, file))
            children.append(f'{mod} #(' + ','.join(f'.{k}({v})' for k,v in overrides.items()) + f') u{i} (.a(a),.y(y[{i}]));')
        (self.root / 'parent.sv').write_text('module parent(input wire a,output wire [2:0] y);\n'+'\n'.join(children)+'\nendmodule\n')
        (case / 'die.v').write_text('module die;\n wire [0:0] n_a;\n wire [2:0] n_y;\n frame f (.a(n_a),.y(n_y));\n keep k (.a(n_a));\nendmodule\n')
        (case / 'die.v.params.json').write_text(json.dumps({'k': {'LAT': 7}}))
        (case / 'place.tcl').write_text('ot_mts::place [$_blk findInst f] 0 0 R0\not_mts::place [$_blk findInst k] 10 0 R0\n')
        (case / 'elements.lef').write_text('MACRO frame\n SIZE 6 BY 2 ;\nEND frame\n')
        (libs / 'views.json').write_text('{"views":{}}')
        self.profile_path = self.root / 'profiles.json'
        self.write_profiles()
        self.patches = [patch.object(E,'ROOT',self.root), patch.object(B,'ROOT',self.root),
                        patch.object(E,'VIEWS',self.views), patch.object(E,'RTL',self.rtl),
                        patch.object(E,'frames',lambda: {'frame':dict(plan=lambda c,w,h:(int(c[1:])*2,0,'R0'),straps=lambda i:{})}),
                        patch.object(E.K,'_set_geometry',lambda *a,**k:None),
                        patch.object(E.K,'BINDINGS',{'frame':dict(module='parent',file='parent.sv',ports={'a':['a'],'y':['y']})})]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def write_profiles(self):
        self.profile_path.write_text(json.dumps(self.profiles))

    def expand(self, diagnostic=True):
        args=['--run',str(self.run),'--only','frame','--parameter-profiles',str(self.profile_path)]
        if diagnostic: args += ['--diagnostic-parameter-profiles']
        return E.main(args)

    def bind(self, diagnostic=True):
        args=[str(self.run/'case_kv/die.v'),'--expanded',str(self.run/'expand.json'),'--out-dir',str(self.root/'bound')]
        if diagnostic: args+=['--diagnostic-parameter-profiles']
        with patch.object(B.PB,'rtl_index',return_value=({},{})):
            return B.main(args)

    def test_real_main_yosys_to_native(self):
        self.assertEqual(self.expand(),0)
        side=json.loads((self.run/'case_kv/die.v.params.json').read_text())
        self.assertEqual(side['k'],{'LAT':7})
        for i,(mod,params) in enumerate(MODULES.items()):
            for k,v in params.items(): self.assertEqual(side[f'f__u{i}'][k],"32'sb"+format(v,'032b'))
        self.bind()
        text=(self.root/'bound/die_bound.v').read_text()
        self.assertIn(".TRUNK_D(32'sb"+format(54,'032b')+')',text)
        self.assertIn(".FLAG_D(32'sb"+format(58,'032b')+')',text)
        with self.assertRaisesRegex(ValueError,'qualification missing'): self.bind(False)
        side['f__u0']['RESET_PIN']="32'sb"+'0'*32
        (self.run/'case_kv/die.v.params.json').write_text(json.dumps(side))
        with self.assertRaisesRegex(ValueError,'conflicting parameters'): self.bind()

    def test_missing_profile_atomic(self):
        del self.profiles['ot_qwen_tp8_pv_slice_t']; self.write_profiles()
        original=(self.run/'case_kv/die.v').read_bytes()
        with self.assertRaisesRegex(ValueError,'missing selected'): self.expand()
        self.assertEqual((self.run/'case_kv/die.v').read_bytes(),original)

    def test_each_changed_profile(self):
        for k in ('RESET_PIN','TRUNK_D','FLAG_D'):
            with self.subTest(k=k):
                p=self.profiles['ot_qwen_tp8_pv_wide_ctl_tb']['parameters']; p[k]+=1; self.write_profiles()
                with self.assertRaisesRegex(ValueError,'profile/source/view mismatch'): self.expand()
                p[k]-=1

    def test_strict_missing_qualification(self):
        with self.assertRaisesRegex(ValueError,'qualification missing'): self.expand(False)

    def test_signed_profile_conflict(self):
        self.profiles['ot_qwen_tp8_pv_wide_ctl_tb']['parameters']['TRUNK_D']=-54
        self.write_profiles()
        with self.assertRaisesRegex(ValueError,'profile/source/view mismatch'): self.expand()

    def test_unknown_bits_and_signed(self):
        with self.assertRaisesRegex(ValueError,'known 32-bit'): P.evaluated({'P':'0'*31+'x'},{'P':0},'m')
        v,l=P.evaluated({'P':'1'*32},{'P':0},'m')
        self.assertEqual(v['P'],-1); self.assertEqual(l['P'],"32'sb"+'1'*32)
        with self.assertRaisesRegex(ValueError,'unsupported parameter'): P.integer_defaults('module m #(parameter logic [3:0] P=0)(input a);','m')

    def test_stale_child_and_duplicate_instance(self):
        p=self.run/'case_kv/die.v.params.json'; p.write_text(json.dumps({'f__u0':{'RESET_PIN':0}}))
        with self.assertRaisesRegex(ValueError,'stale child'): self.expand()
        p.write_text('{}')
        d=self.run/'case_kv/die.v'; d.write_text(d.read_text().replace(' keep k',' keep f__u0'))
        with self.assertRaisesRegex(ValueError,'duplicate instance'): self.expand()

    def test_native_artifact_mutation(self):
        self.expand()
        p=self.root/self.views['ot_qwen_tp8_pv_slice_t']/'ot_qwen_tp8_pv_slice_t_tt.lib'
        p.write_text(p.read_text()+'// changed\n')
        with self.assertRaisesRegex(ValueError,'source/view artifact changed'): self.bind()

    def test_native_missing_instance(self):
        self.expand()
        p=self.run/'case_kv/die.v'
        p.write_text(p.read_text().replace(' f__u0 ', ' foreign__u0 '))
        with self.assertRaisesRegex(ValueError,'instance/master missing'): self.bind()

    def test_source_view_mutation(self):
        p=self.root/self.rtl['ot_qwen_tp8_pv_slice_t']; p.write_text(p.read_text()+'// changed\n')
        with self.assertRaisesRegex(ValueError,'profile/source/view mismatch'): self.expand()

    def test_forged_qualified_report_refused(self):
        self.expand()
        p=self.run/'expand.json'; r=json.loads(p.read_text())
        for row in r['parameter_instances'].values(): row['profile']['native_qualified']=True
        p.write_text(json.dumps(r))
        with self.assertRaises(ValueError): self.bind(False)

    def test_entire_or_single_ledger_removal_refused(self):
        self.expand()
        p=self.run/'expand.json'; original=json.loads(p.read_text())
        for field in ('all', 'one', 'all_and_leaf_binding'):
            with self.subTest(field=field):
                r=copy.deepcopy(original)
                if field == 'one':
                    del r['parameter_instances']['f__u0']
                else:
                    r.pop('parameter_instances')
                if field == 'all_and_leaf_binding':
                    r['leaves']={}
                    r.pop('frames',None)
                p.write_text(json.dumps(r))
                with self.assertRaisesRegex(ValueError,'ledger incomplete'):
                    self.bind()

    def test_genuinely_parameterless_legacy_leaf_compatible(self):
        self.expand()
        report=json.loads((self.run/'expand.json').read_text())
        side=json.loads((self.run/'case_kv/die.v.params.json').read_text())
        mod='ot_qwen_tp8_pv_slice_t'; inst='f__u0'
        (self.root/self.rtl[mod]).write_text(f'module {mod}(input wire a,output wire y); assign y=a; endmodule\n')
        report['parameter_instances'].pop(inst); side.pop(inst)
        (self.run/'expand.json').write_text(json.dumps(report))
        (self.run/'case_kv/die.v.params.json').write_text(json.dumps(side))
        self.bind()

    def test_dynamic_indexed_leaf_cannot_vanish_with_report(self):
        self.expand()
        p=self.run/'expand.json'; report=json.loads(p.read_text())
        report.pop('parameter_instances'); report['leaves']={}; report.pop('frames',None)
        p.write_text(json.dumps(report))
        index={}
        for mod, file in self.rtl.items():
            for module in B.PB.parse_modules((self.root/file).read_text(),str(self.root/file)):
                index[module.name]=module
        args=[str(self.run/'case_kv/die.v'),'--expanded',str(p),'--out-dir',str(self.root/'bound'),
              '--diagnostic-parameter-profiles']
        with patch.object(E,'RTL',{}), patch.object(B.PB,'rtl_index',return_value=(index,{})):
            with self.assertRaisesRegex(ValueError,'ledger incomplete'):
                B.main(args)

    def test_dynamic_leaf_also_in_native_bindings_requires_ledger(self):
        self.expand()
        p=self.run/'expand.json'; report=json.loads(p.read_text())
        report.pop('parameter_instances'); report['leaves']={}; report.pop('frames',None)
        p.write_text(json.dumps(report))
        index={}
        for mod,file in self.rtl.items():
            for module in B.PB.parse_modules((self.root/file).read_text(),str(self.root/file)):
                index[module.name]=module
        configured=dict(E.K.BINDINGS)
        for mod,file in self.rtl.items():
            configured[mod]=dict(module=mod,file=file,ports={'a':['a'],'y':['y']})
        args=[str(self.run/'case_kv/die.v'),'--expanded',str(p),'--out-dir',str(self.root/'bound'),
              '--diagnostic-parameter-profiles']
        with patch.object(E,'RTL',{}), patch.object(E.K,'BINDINGS',configured), \
             patch.object(B.PB,'rtl_index',return_value=(index,{})):
            with self.assertRaisesRegex(ValueError,'ledger incomplete'):
                B.main(args)

    def test_genuinely_nonexpanded_native_binding_compatible(self):
        mod='ot_qwen_tp8_pv_slice_t'
        d=self.run/'case_kv/die.v'
        d.write_text(d.read_text().replace(' keep k',f' {mod} direct (.a(n_a),.y(n_y[0]));\n keep k'))
        self.expand()
        index={}
        for module,file in self.rtl.items():
            for entry in B.PB.parse_modules((self.root/file).read_text(),str(self.root/file)):
                index[entry.name]=entry
        configured=dict(E.K.BINDINGS)
        configured[mod]=dict(module=mod,file=self.rtl[mod],ports={'a':['a'],'y':['y']})
        args=[str(d),'--expanded',str(self.run/'expand.json'),'--out-dir',str(self.root/'bound'),
              '--diagnostic-parameter-profiles']
        with patch.object(E.K,'BINDINGS',configured), patch.object(B.PB,'rtl_index',return_value=(index,{})):
            B.main(args)

if __name__=='__main__': unittest.main(verbosity=2)
