"""Protocol fixtures over real pinned declarations; no provider initialization."""
import hashlib
import os
import ast
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from h4_c0_ds_comparison_backend import ReviewedReferenceWitness,bind_comparison,bind_kepler_continuation
from h4_c0_ds_fullgraph_inventory import load
from h4_c0_ds_runtime_bindings import canonical

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=Path(os.environ.get('H4_C0_REFERENCE_CONTRACT','/tmp/DS-independent-PC21-49-reference-20261002-r2/expected_outputs.json'))
MANIFEST=ROOT/'results/uarch/h4_c0_ds_prefix_golden_20261002/r1/actual_prefix_input_manifest.json.gz'
NATIVE=Path('/tmp/kepler-ds-r43-PC0-9-execution-20261002/bound_native.json.gz')
CONTRACT_SHA='eb89280ee307d89a29926ccbab05a467ccceb6ee96549792ecb857c1d126a2ee'
class Events(list):
    def summary(self):return dict(protocol_fixture_entries=len(self))
class BackendTests(unittest.TestCase):
    def args(self):
        n=load(NATIVE)
        return dict(reviewed_contracts={CONTRACT:CONTRACT_SHA},reference_input_manifest=MANIFEST,
            native=n,first_PC=21,last_PC=49,reviewed_native_content_sha256=hashlib.sha256(canonical(n)).hexdigest())
    def test_full_declared_scope_comparison_and_delegate_order(self):
        # Receipt generator is a protocol fixture, never actual operand evidence.
        events=[]
        class Provider:
            manifest=load(MANIFEST);journal_budget=None
            def publish(self,identity,fields,view):
                events.append('published')
                hashes={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in fields.items()}
                return dict(identity=identity,payload_sha256=hashes,pending_obligations=0,
                    events=[dict(event=name,identity=identity,sequence=i) for i,name in enumerate(['software_backing_visible','consumer_accept','validated_reverse_grant'])])
        with patch('h4_c0_ds_comparison_backend.DiskEvents',lambda _:Events()):
            p,w=bind_comparison(Provider(),enabled=True,**self.args())
        for row in load(CONTRACT)['expectations']:
            a=np.load(CONTRACT.parent/row['path'],allow_pickle=False)
            identity=dict(PC=row['PC'],version=row['version'],rank=row['rank'],generation=row['generation'],home_indices=[])
            p.publish(identity,{'data':a},{})
        result=w.finish();self.assertEqual(result['output_fields_compared'],3456)
        self.assertEqual(len(events),3456);self.assertFalse(result['hardware_qualified'])
    def test_wrong_reviewed_contract_and_missing_scope_refuse(self):
        provider=SimpleNamespace(manifest=load(MANIFEST),journal_budget=None)
        a=self.args();a['reviewed_contracts']={CONTRACT:'0'*64}
        with self.assertRaisesRegex(ValueError,'reviewed comparison'):ReviewedReferenceWitness(provider=provider,**a)
        a=self.args();a['last_PC']=50
        with self.assertRaisesRegex(ValueError,'complete scoped'):ReviewedReferenceWitness(provider=provider,**a)
    def test_entering_state_mutation_refused(self):
        m=load(MANIFEST);m['checkpoint_revision']='changed'
        with self.assertRaisesRegex(ValueError,'entering-state'):
            ReviewedReferenceWitness(provider=SimpleNamespace(manifest=m,journal_budget=None),**self.args())
    def test_current_instruction_mutation_latches_failure(self):
        provider=SimpleNamespace(manifest=load(MANIFEST),journal_budget=None)
        with patch('h4_c0_ds_comparison_backend.DiskEvents',lambda _:Events()):w=ReviewedReferenceWitness(provider=provider,**self.args())
        w.native['instructions'][21]['family']='changed'
        ident=dict(PC=21,version='unused',rank=0,generation=1)
        with self.assertRaisesRegex(ValueError,'instruction source mutated'):w.observe(ident,{}, {})
        with self.assertRaisesRegex(ValueError,'no retry'):w.observe(ident,{}, {})
    def test_unselected_source_mutation_refuses_finish(self):
        provider=SimpleNamespace(manifest=load(MANIFEST),journal_budget=None)
        with patch('h4_c0_ds_comparison_backend.DiskEvents',lambda _:Events()):w=ReviewedReferenceWitness(provider=provider,**self.args())
        w.native['instructions'][2000]['family']='changed'
        with self.assertRaisesRegex(ValueError,'complete source mutated'):w.finish()
    def test_kepler_default_off_identity(self):
        p=object();q,w=bind_kepler_continuation(p);self.assertIs(q,p);self.assertIsNone(w)
    def test_original_kepler_wrapper_publishes_once_and_routes_scopes(self):
        # Compile the pinned original wrapper class alone: protocol fixture,
        # no provider initializer, arithmetic, checkpoint install or GO.
        source=Path('/tmp/kepler-ds-r50-current-main-20261002/tools/ds_hbm_prefix_observed_outputs_r42.py')
        node=next(n for n in ast.parse(source.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Observed')
        module=types.ModuleType('_kepler_wrapper_protocol_fixture');module.__file__=str(source)
        sys.modules[module.__name__]=module;self.addCleanup(lambda:sys.modules.pop(module.__name__,None))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(source),'exec'),module.__dict__)
        calls=[]
        class Provider:
            def publish(self,*args):calls.append('actual-publisher-protocol-fixture');return 'receipt'
        base=Provider()
        class Prefix:
            provider=base;expected={(0,'v',0,1,'data'):None}
            def observe(self,*args):calls.append('prefix')
        class Later:
            first=21;last=49
            def observe(self,*args):calls.append('later')
        old=module.Observed(base,Prefix());later=Later()
        with patch('h4_c0_ds_comparison_backend.ReviewedReferenceWitness',lambda **_:later):
            new,w=bind_kepler_continuation(old,enabled=True)
        self.assertIs(type(new),type(old));self.assertIs(w,later)
        new.publish(dict(PC=0),{},{});new.publish(dict(PC=21),{},{})
        self.assertEqual(calls,['actual-publisher-protocol-fixture','prefix','actual-publisher-protocol-fixture','later'])
        with self.assertRaisesRegex(ValueError,'outside explicitly reviewed'):new.publish(dict(PC=15),{},{})
if __name__=='__main__':unittest.main()
