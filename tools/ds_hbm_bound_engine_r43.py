"""Explicit bound-address admission; retains pinned peer arithmetic unchanged."""
import gzip,hashlib,json
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,peer
from ds_hbm_storage_home_binding_r41 import bind_storage,canonical
R=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002'

def validate_lineage(provider,*,original_native_artifact_path,bound_native_artifact_path):
    pin=json.loads((R/'bound_artifact_pin.json').read_bytes())
    original_raw=Path(original_native_artifact_path).read_bytes()
    if hashlib.sha256(original_raw).hexdigest()!=pin['original_native_sha256']:raise ValueError('exact original c65 native required')
    original=json.loads(gzip.decompress(original_raw))
    home_raw=(ROOT/pin['original_homes_artifact']).read_bytes()
    if hashlib.sha256(home_raw).hexdigest()!=pin['original_homes_sha256']:raise ValueError('original source homes pin')
    original_homes=json.loads(gzip.decompress(home_raw))['homes']
    expected,homes,_,proof=bind_storage(original,original_homes,provider.manifest)
    artifact=Path(bound_native_artifact_path).read_bytes();actual_sha=hashlib.sha256(artifact).hexdigest()
    if actual_sha!=pin['bound_native_sha256']:raise ValueError('exact generated bound native artifact hash')
    bound=json.loads(gzip.decompress(artifact))
    if canonical(bound)!=canonical(expected):raise ValueError('bound artifact differs from complete home-only regeneration')
    if canonical(provider.native)!=canonical(bound):raise ValueError('complete provider native differs from bound artifact')
    if canonical(provider.homes)!=canonical(homes):raise ValueError('complete provider homes differ from exact allocated directory')
    return dict(status='PASS_EXACT_BOUND_NATIVE_LINEAGE',original_native_artifact_sha256=pin['original_native_sha256'],bound_native_artifact_sha256=actual_sha,bound_native_content_sha256=hashlib.sha256(canonical(bound)).hexdigest(),only_home_indices_changed=proof['arithmetic_unchanged'],complete_allocated_home_records=len(homes),bound_artifact_path=str(Path(bound_native_artifact_path).resolve()),full_token_GO=False,hardware_qualified=False)

def bound_tiled_class():
    original=peer('h4_c0_ds_tiled_continuation')
    class BoundTiled(original.TiledContinuation):
        def __init__(self,provider,*,native_artifact_path,original_native_artifact_path):
            self.lineage=validate_lineage(provider,original_native_artifact_path=original_native_artifact_path,bound_native_artifact_path=native_artifact_path)
            self.provider=provider;self.plan=original.GroupOperandTiles()
            self.bridge=original.SourceViews(provider,native_content_sha256=self.lineage['bound_native_content_sha256'])
            # Preserve every original group template/provider/writer/rank check.
            for pc,parent in self.plan.parents.items():
                ops=[o for o in provider.native['instructions'] if o['pc']==pc];tid=parent['new_template']
                if len(ops)!=1 or tid not in self.plan.templates or provider.native['templates'].get(tid)!=self.plan.templates[tid]:raise ValueError('actual current arithmetic template mismatch')
                op=ops[0]
                if (op['provider_bindings']!=parent['provider_bindings'] or op['writes']!=parent['writes'] or [(r['rank'],r['template']) for r in op['rank_bindings']]!=[(r['rank'],r['template']) for r in parent['actual_rank_template_bindings']]):raise ValueError('actual current PC/rank/version bindings mismatch')
            self.failed=False;self.completed=set();self.receiver=original.operand_receiver()
        def run(self,*args,**kwargs):
            # The source-owned arithmetic, transport, release and refusal body is
            # inherited unchanged. Record the actual admitted artifact identity.
            result=super().run(*args,**kwargs)
            result['original_native_artifact_sha256']=self.lineage['original_native_artifact_sha256']
            result['native_artifact_sha256']=self.lineage['bound_native_artifact_sha256']
            result['bound_native_content_sha256']=self.lineage['bound_native_content_sha256']
            return result
    return BoundTiled

def engine_class(prefix):
    sagan=peer('h3_deepseek_full_token_driver')
    # Retain the exact R39 Sagan execution snapshot and run/execute_operation.
    from ds_hbm_source_prefix_r39 import sagan as native_execution
    source=native_execution()
    tiled=bound_tiled_class()
    class Engine(prefix):
        def __init__(self,native,dispatch,provider,revision,generation,homes,*,native_artifact_path,dispatch_artifact_path,original_native_artifact_path):
            raw=Path(dispatch_artifact_path).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source.DISPATCH or source.canonical(json.loads(gzip.decompress(raw)))!=source.canonical(dispatch):raise ValueError('exact corrected native dispatch artifact required')
            self.expected_outputs=None
            sagan.TokenDriver.__init__(self,native,dispatch,provider,revision,generation,homes)
            self.groups=tiled(provider,native_artifact_path=native_artifact_path,original_native_artifact_path=original_native_artifact_path)
            self.native_calls=source.CallJournal(provider.journal_budget,'C0_actual_native_group_call')
            self.journal=source.CallJournal(provider.journal_budget,'C0_actual_native_numeric_call')
    return Engine
