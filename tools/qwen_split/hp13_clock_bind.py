"""Typed source-clock ownership, resolved only after regional partitioning."""
import os


def apply(model, buses, instances, tt_ports):
    if os.environ.get('OT_QWEN_HP13_CLOCKS', '0') != '1': return
    if any(tt_ports.get(p) != (1, 'input') for p in ('ck_core', 'ck_hr')):
        raise ValueError('HP13 actual source clock inputs differ')
    if any('tt_ctlm' in g.split(',') for g in os.environ.get('OT_SPLIT_CK_COROOT', '').split(';')):
        raise ValueError('HP13 legacy first-clock TT co-root is forbidden')
    by = {i.name:i for i in instances}
    targets = {'ck_core':('native59','ck'), 'ck_hr':('dvs_W5','ck')}
    if any(i not in by for i,p in targets.values()):
        raise ValueError('HP13 actual receiving clock instance is absent')
    if any(i=='tt_ctlm' for b in buses if b[1]=='clock_trunk' for i,p in b[3]):
        raise ValueError('HP13 clock input already connected before explicit construction')
    # These typed symbols contain no clock driver and cannot reach accepted RTL.
    # FE uses the source port identity; final regional construction removes them.
    symbols = {}
    for p in targets:
        bid='hp13_symbol_'+p
        buses.append((bid,'clock_trunk',1,[('tt_ctlm',p)]))
        symbols[p]=bid
    model['hp13_clock_bind']=dict(status='SYMBOLIC_OWNER_ONLY', physical_phase_status='UNMEASURED',
        intended_relation=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0),
        targets={p:list(e) for p,e in targets.items()}, symbols=symbols)
    model['hp13_deferred_follow']={('tt_ctlm',p):e for p,e in targets.items()}
    print('HP13_CLOCK_SYMBOLS',model['hp13_clock_bind'],flush=True)


def data_clock_owner(model, inst, port):
    """An ABI data endpoint needs a source-bound capture/producer clock law."""
    if inst != 'tt_ctlm' or 'hp13_clock_bind' not in model:
        return None
    import hashlib, json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    proof = model.get('hp13_data_clock_proof')
    if proof is None:
        path = root / 'results/arch/hp13_corepub39_1021/DATA_CLOCK_OWNERS.json'
        if not path.is_file():
            raise ValueError('HP13 data endpoint has no source-bound clock inventory: '+str((inst,port)))
        master = next(i.master for i in model['insts'] if i.name == inst)
        rows = [r for r in json.loads(path.read_text()) if r['master'] == master]
        if len(rows) != 1:
            raise ValueError('HP13 data clock inventory selected master is unresolved: '+master)
        proof = rows[0]
        if hashlib.sha256((root / proof['rtl']).read_bytes()).hexdigest() != proof['rtl_sha256']:
            raise ValueError('HP13 data clock inventory selected source differs')
        for dependency in proof.get('source_dependencies', []):
            if hashlib.sha256((root / dependency['rtl']).read_bytes()).hexdigest() != dependency['sha256']:
                raise ValueError('HP13 data clock supporting source differs: '+dependency['rtl'])
        model['hp13_data_clock_proof'] = proof
        model['hp13_clock_bind']['data_clock_inventory'] = dict(
            path=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            selected_master=master, rtl_sha256=proof['rtl_sha256'], supporting_sources_verified=True)
    row = proof['ports'].get(port, {})
    clock_port = row.get('clock_port')
    if row.get('status') != 'PROVEN' or clock_port not in ('ck_core', 'ck_hr') or not row.get('basis'):
        raise ValueError('HP13 data endpoint clock is unresolved: '+str((inst,port,row)))
    model.setdefault('hp13_data_clock_uses', {})[port] = dict(clock_port=clock_port, basis=row['basis'])
    return inst, clock_port


def defer_data(model, follower, endpoint, lane):
    owner = data_clock_owner(model, *endpoint)
    if owner is None:
        return False
    model['hp13_deferred_follow'][follower] = owner
    model.setdefault('hp13_deferred_data', {})[follower] = dict(endpoint=list(endpoint), owner=list(owner), lane=lane)
    return True


def defer_fault(model, follower, owner, clock_index):
    if owner!='tt_ctlm' or 'hp13_clock_bind' not in model: return False
    bid=model['buses'][clock_index][0]
    matches=[p for p,b in model['hp13_clock_bind']['symbols'].items() if b==bid]
    if len(matches)!=1:
        raise ValueError('HP13 fault node has no source-proven clock port: '+str((follower,bid)))
    model['hp13_deferred_follow'][follower]=('tt_ctlm',matches[0])
    return True


RELAY_PRIMS = ('qfd_rlyh0_', 'qfd_landh0_', 'qfd_landh_', 'qfd_rlyr0_', 'qfd_rlyrl_')


def defer_fault_relay(model, follower, endpoint, lane):
    """SQC-QDIE4 10-22 (r45 bind: 6 fault-lane stations with ck/ck_s unconnected): a forwarded-lane hop 0 / landing whose
    end is a fault primitive with a DEFERRED HP13 owner follows that primitive's deferred clock (finalize chases it to
    the source-proven tt_ctlm port), instead of a legacy follow that the regional construction drops with the symbol."""
    if 'hp13_clock_bind' not in model or os.environ.get('OT_QWEN_HP13_FAULT_RELAY_FOLLOW', '1') != '1':
        return False
    owner = (endpoint[0], 'ck')
    if owner not in model['hp13_deferred_follow']:
        return False
    model['hp13_deferred_follow'][follower] = owner
    model.setdefault('hp13_deferred_fault_relay', {})[follower] = dict(endpoint=list(endpoint), owner=list(owner), lane=lane)
    return True


def finalize(model, per, record, by):
    info=model.get('hp13_clock_bind')
    if not info:return
    mapping=model['hp13_deferred_follow']; resolved={}
    def terminal(e,seen=()):
        if e in seen:raise ValueError('HP13 deferred clock ownership cycle')
        return terminal(mapping[e],seen+(e,)) if e in mapping else e
    locations={}
    for k,eps in per.items():
        for e in eps: locations.setdefault(e,[]).append(k)
    terminals={terminal(e) for e in mapping}
    for e in terminals:
        if len(locations.get(e,[]))!=1:
            raise ValueError('HP13 final actual receiving root is not unique: '+str((e,locations.get(e))))
    # Verify the selected functional clock families at the unique-root stage.
    domains={i:by[i].domain for i,p in terminals}
    if any(not isinstance(d,str) or not d for d in domains.values()) or len(set(domains.values()))!=1:
        raise ValueError('HP13 selected related functional clock families disagree: '+str(domains))
    legacy=model.setdefault('ck_follow',{}); explicit=model.setdefault('ck_follow_port',{})
    for f in mapping:
        e=terminal(f);k=locations[e][0]
        if f[0] not in by:raise ValueError('HP13 follower actual instance absent: '+str(f))
        if f in model.get('hp13_deferred_data', {}):
            row=model['hp13_deferred_data'][f]
            if data_clock_owner(model, *row['endpoint']) != mapping[f] or not by[f[0]].master.startswith(('qfd_rlyh0_', 'qfd_landh0_', 'qfd_landh_', 'qfd_rlyr0_', 'qfd_rlyrl_')):
                raise ValueError('HP13 data follower source/primitive differs: '+str(f))
        elif f in model.get('hp13_deferred_fault_relay', {}):
            o=mapping[f]
            if not by[f[0]].master.startswith(RELAY_PRIMS) or o not in mapping or o[0] not in by or not by[o[0]].master.startswith('qfd_fault_or_n'):
                raise ValueError('HP13 fault-lane follower is not a relay of a deferred fault primitive: '+str((f,o)))
        elif f[0]!='tt_ctlm' and not by[f[0]].master.startswith('qfd_fault_or_n'):
            raise ValueError('HP13 deferred follower is not a source-proven fault primitive: '+str(f))
        if len(locations.get(f,[]))>1:raise ValueError('HP13 follower has multiple actual regions: '+str(f))
        if f not in locations:per[k].append(f);locations[f]=[k]
        legacy[f]=e[0];explicit[f]=e
        resolved[str(f)]=dict(source_owner=list(mapping[f]),terminal=list(e),region=k)
        if f in model.get('hp13_deferred_data', {}):
            resolved[str(f)].update(model['hp13_deferred_data'][f])
    from qwen_split.clock_follow_port import apply as resolve
    resolve(model,per,record)
    info.update(status='REGIONAL_ENDPOINTS_RESOLVED',domains=domains,followers=resolved)


def audit_final(model):
    info=model.get('hp13_clock_bind')
    if not info:return
    if info['status'] not in ('REGIONAL_ENDPOINTS_RESOLVED', 'ACTUAL_CLOCK_NETS_RESOLVED'):
        raise ValueError('HP13 clock ownership never resolved')
    symbols=set(info['symbols'].values())
    if any(b[0] in symbols for b in model['buses']):raise ValueError('HP13 semantic symbol escaped final construction')
    clock={}
    for bid,kind,width,eps in model['buses']:
        if kind!='clock_trunk':continue
        for e in eps[1:]:clock.setdefault(e,[]).append((bid,eps[0]))
    receipt={}
    for p,target in info['targets'].items():
        rows=clock.get(('tt_ctlm',p),[]);other=clock.get(tuple(target),[])
        if len(rows)!=1 or rows!=other:raise ValueError('HP13 final source/receiver clock binding differs: '+p)
        receipt[p]=dict(bus=rows[0][0],driver=list(rows[0][1]),receiver=target)
    for f,row in model['hp13_deferred_follow'].items():
        got=clock.get(f,[])
        if len(got)!=1 or got!=clock.get(row,[]):
            raise ValueError('HP13 final follower differs from its source-proven owner clock: '+str(f))
    if clock.get(('embed_prov','ck'),[]) != clock.get(('native59','ck'),[]):
        raise ValueError('HP13 final native/embedding core roots differ')
    if model.get('hp13_cf_clock'):
        model['hp13_cf_clock'].update(status='ACTUAL_CLOCK_NET_RESOLVED_PHYSICAL_PHASE_UNMEASURED',
            actual_clock=receipt['ck_hr'])
    info.update(status='ACTUAL_CLOCK_NETS_RESOLVED',actual_pins=receipt,
                data_port_owners=model.get('hp13_data_clock_uses', {}))
    print('HP13_CLOCK_BIND_FINAL',info,flush=True)
