"""Real-view evidence and the opt-in IO-HOLD A parent obligation."""
import hashlib
import json
import re
from pathlib import Path


def plan_digest(raw):
    return hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def view_snapshot(directory):
    root = Path(directory)
    v, sp = root/'6_final.v', root/'6_final.spef'
    result = dict(kind='unknown', netlist=str(v), spef=str(sp), spef_present=sp.is_file())
    if not v.is_file():
        return result
    budget, bare, other = False, 0, 0
    with v.open(errors='replace') as f:
        for line in f:
            if any(x in line for x in ('OT_BHOLD_', 'OT_CLAT_', 'OPENTALLAS_BUDGET_STANDIN')):
                budget = True
            m = re.match(r'\s*(\w+)\s+(\w+)\s*\(', line)
            if m and m[1] not in {'module','input','output','wire','reg','assign'}:
                if m[1]=='DFFHQNx1_ASAP7_75t_R' and re.fullmatch(r'f\d+',m[2]): bare += 1
                else: other += 1
    result['kind'] = 'budget' if budget or bare and not other else 'real'
    result['netlist_sha256'] = digest(v)
    if sp.is_file(): result['spef_sha256'] = digest(sp)
    return result


def kit_policy(inputs):
    ctx = inputs.get('sdc_lint_ctx')
    if not ctx or not Path(ctx).is_file(): return None
    raw = json.loads(Path(ctx).read_text())
    ports = raw.get('hold_in_min_ports_ps') or {}
    if not ports: return None
    budget = Path(inputs.get('kit') or '')/'budget.json'
    meta = json.loads(budget.read_text()) if budget.is_file() else {}
    return dict(mode='sender_min', die=meta.get('die'), receiver_type=meta.get('type'),
                input_ports=sorted(ports), plan_sha256=(meta.get('io_hold') or {}).get('plan_sha256'), requirement='real parent FF hold and TT/FF related-pair CPPR',
                provisional_views_allowed=True)


def apply_obligation(record):
    policy = record.get('io_hold') or kit_policy(record.get('inputs') or {})
    if not policy: return record
    record['io_hold'] = policy
    local = record['verdict']
    record['local_verdict'] = local
    why, receipt = [], record.get('io_hold_parent_receipt')
    if not receipt:
        path = Path((record.get('inputs') or {}).get('kit') or '')/'io_hold_parent.json'
        if path.is_file():
            receipt = json.loads(path.read_text());record['io_hold_parent_receipt']=receipt
    if not receipt or receipt.get('schema')!='opentallas.io_hold_parent.v2' or receipt.get('verdict')!='PASS':
        why.append('matching real-parent PASS receipt missing')
    else:
        if not receipt.get('qualification',{}).get('complete'):
            why.append('parent evidence not qualified')
        if not policy.get('die') or receipt.get('plan')!=policy['die']:
            why.append('parent scope does not match the kit die')
        if not policy.get('plan_sha256') or receipt.get('plan_sha256')!=policy['plan_sha256']:
            why.append('parent plan differs from the generated kit contract')
        rows=[r for r in receipt.get('ports',[]) if r.get('dst_type')==policy.get('receiver_type')]
        covered={r.get('sv_bus',r.get('bus')) for r in rows if r.get('status')=='PASS'}
        if not set(policy['input_ports']) <= covered:
            why.append('parent does not cover every option-A input port')
        v=(record.get('inputs') or {}).get('final_v')
        actual=digest(v) if v and Path(v).is_file() else None
        if not actual or any(r.get('receiver_netlist_sha256')!=actual for r in rows) or not rows:
            why.append('parent receiver netlist differs from this routed kit')
        sp=(record.get('inputs') or {}).get('spef')
        rc=digest(sp) if sp and Path(sp).is_file() else None
        if not rc or any(r.get('receiver_spef_sha256')!=rc for r in rows):
            why.append('parent receiver parasitics differ from this routed kit')
    record['parent_qualification']=dict(status='NEEDS_PARENT' if why else 'PASS',problems=why,
        provisional_views_allowed=True, release_qualified=not why and local=='SIGNED')
    record['release_qualified'] = not why and local=='SIGNED'
    record.setdefault('checks',{})['io_hold_parent'] = dict(verdict='NOT RUN' if why else 'PASS', required=True, problems=why)
    if why:
        if local=='SIGNED':record['verdict']='LOCAL_PASS_NEEDS_PARENT'
        record['reasons'].append('io_hold_parent: NEEDS_PARENT; '+'; '.join(why))
    return record
