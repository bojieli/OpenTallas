"""ROOT review: eight guarded candidate cases, including real archived TT/FF STA.
No spec or kit in production opts in. Full source-pinned CAPC fixture is optional
in sparse checkout; malformed guards are exercised without this fixture too.
"""
import copy
import hashlib
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT
import registered_cluster_budget as B

ROOT = RT.ROOT
RECEIPT = ROOT / 'results/uarch/s81_capc_nativep1_1019/registered_candidate_receipt.json'

@unittest.skipUnless(RECEIPT.is_file(), 'actual CAPC native STA fixture absent in sparse checkout')
class RegisteredCluster(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / 'tools/ref_tile/specs_s81slice/s81sl_capc_p1.json').read_text())
        self.spec.update(hold_budget='die', inhold=False, outhold=False,
                         registered_boundary_contract='all-data-pins',
                         registered_cluster_candidate=dict(path=str(RECEIPT.relative_to(ROOT)),
                         sha256=hashlib.sha256(RECEIPT.read_bytes()).hexdigest()))
        self.spec['route']['io_hold_margin_ns'] = .03
    def reject(self, mutate):
        s = copy.deepcopy(self.spec); mutate(s)
        with self.assertRaises((RT.SpecError, ValueError)):
            RT.check_hold_budget(s)
    def altered_receipt(self, mutate):
        r=json.loads(RECEIPT.read_text());mutate(r)
        with tempfile.NamedTemporaryFile(dir=RECEIPT.parent, suffix='.json') as f:
            f.write(json.dumps(r).encode());f.flush()
            self.reject(lambda s:s.update(registered_cluster_candidate=dict(
                path=str(Path(f.name).relative_to(ROOT)),sha256=hashlib.sha256(Path(f.name).read_bytes()).hexdigest())))
    def altered_lib(self, transform):
        r=json.loads(RECEIPT.read_text())
        original=(ROOT/r['ff_lib']['path']).read_text()
        changed=transform(original)
        self.assertNotEqual(original, changed)
        with tempfile.NamedTemporaryFile(dir=RECEIPT.parent, suffix='.lib') as f:
            f.write(changed.encode());f.flush()
            changed_hash=hashlib.sha256(Path(f.name).read_bytes()).hexdigest()
            binding=json.loads((ROOT/r['native_binding']['path']).read_text())
            for item in binding['files']:
                if item['path'].endswith('/native_probe_ff.lib'):item['sha256']=changed_hash
            with tempfile.NamedTemporaryFile(dir=RECEIPT.parent, suffix='.json') as bf:
                bf.write(json.dumps(binding).encode());bf.flush()
                def amend(r):
                    r['ff_lib']=dict(path=str(Path(f.name).relative_to(ROOT)),sha256=changed_hash)
                    r['native_binding']=dict(path=str(Path(bf.name).relative_to(ROOT)),sha256=hashlib.sha256(Path(bf.name).read_bytes()).hexdigest())
                self.altered_receipt(amend)
    def altered_gate(self, transform):
        r=json.loads(RECEIPT.read_text()); g=json.loads((ROOT/r['gate']['path']).read_text());transform(g)
        with tempfile.NamedTemporaryFile(dir=RECEIPT.parent, suffix='.json') as f:
            f.write(json.dumps(g).encode());f.flush()
            self.altered_receipt(lambda r:r.update(gate=dict(path=str(Path(f.name).relative_to(ROOT)),
                sha256=hashlib.sha256(Path(f.name).read_bytes()).hexdigest())))
    def dropped_both_models(self):
        r=json.loads(RECEIPT.read_text())
        binding=json.loads((ROOT/r['native_binding']['path']).read_text())
        with tempfile.TemporaryDirectory(dir=RECEIPT.parent) as tmp:
            tmp=Path(tmp)
            for corner in ('tt','ff'):
                t=(ROOT/r[corner+'_lib']['path']).read_text()
                match=re.search(r'pin\s*\(\s*"?cw_n_v\[0\]"?\s*\)\s*\{',t)
                self.assertIsNotNone(match)
                level=1;end=match.end()
                while level:
                    level+=(t[end]=='{')-(t[end]=='}');end+=1
                path=tmp/(corner+'.lib');path.write_text(t[:match.start()]+t[end:])
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                r[corner+'_lib']=dict(path=str(path.relative_to(ROOT)),sha256=digest)
                for item in binding['files']:
                    if item['path'].endswith('/native_probe_'+corner+'.lib'):item['sha256']=digest
            path=tmp/'binding.json';path.write_text(json.dumps(binding))
            r['native_binding']=dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            path=tmp/'receipt.json';path.write_text(json.dumps(r))
            self.reject(lambda s:s.update(registered_cluster_candidate=dict(path=str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
    def test_01_actual_sta_admits_candidate_not_native_pass(self):
        RT.check_hold_budget(self.spec)
        census=B.check(self.spec, ROOT)
        self.assertEqual(len(census['ff']),1173)
        self.assertGreater(max(p['out'] for p in census['tt'].values() if p['dir']=='output'),220)
        self.assertGreaterEqual(min(p['lmin'] for p in census['ff'].values() if p['dir']=='output'),25)
    def test_02_missing_or_stale_source_refuses(self):
        self.reject(lambda s:s['registered_cluster_candidate'].update(sha256='0'*64))
        self.altered_receipt(lambda r:r['sources'][0].update(sha256='0'*64))
        self.altered_receipt(lambda r:r.update(source_commit='0'*40))
    def test_03_no_registration_or_excluded_or_changed_parameter_refuses(self):
        self.reject(lambda s:s.update(registered_boundary_contract=None))
        self.reject(lambda s:s.update(pin_regs={'enable':True,'exclude':'cfg.*'}))
        self.reject(lambda s:s['params'].update(PINPIPE=0))
        # Updating both requested identity and receipt cannot launder a stale gate model.
        self.spec['params']['PINPIPE']=0
        self.altered_receipt(lambda r:r['identity']['params'].update(PINPIPE=0))
        self.spec['params']['PINPIPE']=1
        self.spec['children'][0]['view']='unproved-child'
        self.altered_receipt(lambda r:r['identity']['children'][0].update(view='unproved-child'))
    def test_04_missing_tt_or_ff_or_comb_census_refuses(self):
        self.dropped_both_models()
        self.altered_receipt(lambda r:r.pop('tt_lib'))
        self.altered_receipt(lambda r:r.pop('ff_lib'))
        self.altered_receipt(lambda r:r.pop('insertion'))
        with tempfile.NamedTemporaryFile(dir=RECEIPT.parent, suffix='.sv') as source:
            source.write(b'module bad(input VDD, input clk, output logic q); always @(posedge clk) q<=VDD; endmodule')
            source.flush()
            ports=B.source_ports(dict(top='bad',sources=[str(Path(source.name).relative_to(ROOT))]),ROOT)
            self.assertIn('VDD',ports)
            with self.assertRaisesRegex(ValueError,'unconstrained source data port'):
                B.remove_supply_pins({'VDD':{}},{'pins':{'VDD':{'arcs':[]}}},ports)
        self.assertNotIn('VDD', B.source_ports(self.spec, ROOT))
        self.assertNotIn('VSS', B.source_ports(self.spec, ROOT))
        self.altered_lib(lambda t:re.sub(r'(timing_type\s*:\s*)rising_edge', r'\1combinational', t, count=1))
        self.altered_lib(lambda t:re.sub(r'(cell_rise\s*\([^)]*\)\s*\{[^{}]*?values\()\"[^\"]*\"', lambda m:m.group(1)+'"-1000"', t))
    def test_05_clock_root_or_child_reference_refuses(self):
        self.reject(lambda s:s.update(child_clock_ref='pin'))
        self.reject(lambda s:s.update(clock_ports=['clk','other']))
        self.reject(lambda s:s['children'][0].update(view='unproved-child'))
        self.altered_gate(lambda g:g['clock']['clock_measurements'][0].pop('ff'))
        self.altered_gate(lambda g:g['clock']['clock_measurements'][0]['tt']['child_flop'].pop('refs'))
    def test_06_hold_margin_or_pad_refuses(self):
        self.reject(lambda s:s['route'].update(io_hold_margin_ns=.029))
        self.reject(lambda s:s.update(inhold=True))
        self.reject(lambda s:s.update(outhold=True))
    def test_07_missing_reset_proof_refuses(self):
        self.altered_receipt(lambda r:r.update(reset_stages=1))
        self.altered_receipt(lambda r:r.pop('reset_stage_cells'))
        self.altered_gate(lambda g:g['reset_landing'].update(waived=True))
        self.altered_gate(lambda g:g['reset_landing']['ports'][0].update(sinks=3))
    def test_08_missing_or_relaxed_parent_budget_refuses(self):
        self.altered_receipt(lambda r:r.pop('parent_boundary_budget'))
        for key,value in [('hold_uncertainty_ps',0),('setup_uncertainty_ps',0),('neighbor_skew_max_ps',90),('C_ps',20),('entry_compensation_ps',{})]:
            self.altered_receipt(lambda r:r['parent_boundary_budget'].update({key:value}))

if __name__=='__main__':unittest.main()
