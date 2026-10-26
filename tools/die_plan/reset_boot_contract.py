"""Bind/compiler guard for published reset releases, including local BOOT deltas.

No START edge or role is inferred. A reset-only physical plan remains reset-only.
"""
import argparse,hashlib,json
from pathlib import Path


def plan_fingerprint(plan):
    # asbuilt is the source-binding selection; it does not change physical reset.
    return hashlib.sha256(json.dumps({k:v for k,v in plan.items() if k not in ('asbuilt','reset_boot_contract')},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def compile_contract(plan,before,after,delta):
    if after.get('unreachable') or after.get('long_hops') or not delta['after_valid']:
        raise ValueError('final actual reset wavefront must be reachable/legal')
    if set(after['parts']) != {p['name'] for p in plan['partitions']}:
        raise ValueError('final wavefront must cover actual selected plan')
    observed={}
    for p,a in after['parts'].items():
        b=before['parts'][p]
        if a['release']!=b['release'] or a.get('source')!=b.get('source'):
            observed[p]=dict(before=b['release'],after=a['release'],delta=a['release']-b['release'],source_before=b.get('source'),source_after=a.get('source'))
    if observed!=delta['changed_parts']:raise ValueError('BOOT ledger does not match actual before/after wavefront')
    if after['max_release']!=delta['after_max_release'] or before['max_release']!=delta['before_max_release']:
        raise ValueError('max release mismatch')
    mode=plan.get('reset',{}).get('start')
    if (mode=='broadcast') != (after.get('start',{}).get('mode')=='broadcast'):
        raise ValueError('actual START profile mismatch')
    return dict(schema='opentallas.reset_boot_contract.v1',physical_plan_fingerprint=plan_fingerprint(plan),
        baseline_valid=delta['before_valid'],final_reset_valid=True,baseline_max_release=before['max_release'],final_max_release=after['max_release'],
        changed_parts=observed,parts=after['parts'],start_mode=mode,die_START_edge=None,
        START_status='UNRESOLVED external producer/edge' if mode=='broadcast' else 'ABSENT in actual selected physical profile; no START propagation claim',
        added_register_stages=delta['added_register_stages'],added_production_cycles=delta['added_production_cycles'],
        production_cycle_evidence='physical delta preserves actual latency/lanes/ports/parts/budgets/dieclock/global reset; local BOOT changes retained',
        compiler_ready=False,readiness_gaps=['selected source binding and compiler bookings must consume this exact contract','real START source/edge and explicit mission/bootstrap roles remain required'],
        admission='Existing reset-only controls release at published R[p]. Future START-broadcast mission controls require max(R[p], S+R[p]); never infer S from unchanged global maximum.')


def check_plan(plan,contract):
    if contract.get('schema')!='opentallas.reset_boot_contract.v1':raise ValueError('unsupported reset/BOOT contract')
    if plan_fingerprint(plan)!=contract['physical_plan_fingerprint']:raise ValueError('selected physical plan differs from published reset/BOOT contract; regenerate offsets/ledger before rebind')
    if set(contract['parts'])!={p['name'] for p in plan['partitions']}:raise ValueError('reset/BOOT contract missing actual partitions')
    return contract


def check_binding(plan,base):
    ab=plan.get('asbuilt') or {}
    ref=plan.get('reset_boot_contract') or ab.get('reset_boot_contract')
    if not ref:return None
    if plan.get('reset_boot_contract') != ref or ab.get('reset_boot_contract') != ref:
        raise ValueError('plan and current asbuilt manifest must select the same reset/BOOT contract')
    if not isinstance(ref,dict) or set(ref)!={'file','sha256'}:
        raise ValueError('reset/BOOT contract requires file and sha256')
    path=Path(ref['file']);path=path if path.is_absolute() else Path(base)/path
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=ref['sha256']:
        raise ValueError('published reset/BOOT contract changed')
    return check_plan(plan,json.loads(data))


def adopt_contract(plan,manifest,reference):
    """Explicit caller-owned plan+manifest adoption; plan_inputs stages the proof."""
    plan['reset_boot_contract']=reference
    manifest['reset_boot_contract']=reference
    return plan,manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','before','after','delta'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=compile_contract(*[json.loads(getattr(a,n).read_text()) for n in ('plan','before','after','delta')])
    check_plan(json.loads(a.plan.read_text()),result)
    a.out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(dict(out=str(a.out),changed_parts=len(result['changed_parts']),max_release=result['final_max_release'],START=result['START_status'])))
if __name__=='__main__':main()
