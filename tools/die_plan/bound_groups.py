"""Explicit exact post-bind groups; project real resets before grouping their RTL.

This never waives a missing hard-core reset. Every original member/module/pin
must match once, all delivery taps retain the published cycle and START role,
and materialization must connect the new group to that exact scheduled net.
"""
import json
import re


class BoundGroupError(ValueError):
    pass


def reset_members(cells, members, rel_of, target, hc, tree, leaf_tap):
    contract=hc.get('bound_group')
    if contract is None:
        return None
    if contract.get('kind')!='exact_post_bind_group' or contract.get('reset_pin')!=target['pin'] or len(contract.get('members',[]))!=5:
        raise BoundGroupError('invalid explicit five-member reset group '+hc['inst'])
    expected=contract['members']
    if len({x['inst'] for x in expected})!=5:
        raise BoundGroupError('duplicate group member')
    depth={r['q']:r['depth'] for r in tree['relays']}
    source=f"rst_n_t{leaf_tap}";dest=f"rst_n_t{target['tap']}"
    if source not in depth or depth.get(source)!=depth.get(dest):
        raise BoundGroupError(f'{hc["inst"]}: group reset changes published release depth {source}->{dest}')
    roles=tree.get('tap_roles',{})
    if roles.get(leaf_tap,'mission')!=roles.get(target['tap'],'mission'):
        raise BoundGroupError(f'{hc["inst"]}: group reset changes START role')
    out=[]
    for item in expected:
        found=[i for i in members if rel_of(i)==item['inst']]
        if len(found)!=1:
            raise BoundGroupError(f'{hc["inst"]}: exact member {item["inst"]} count{len(found)}')
        i=found[0];c=cells[i];pin=item['reset_pin']
        if c.module!=item['module'] or c.dirs.get(pin)!='input' or len(c.ports.get(pin,[]))!=1:
            raise BoundGroupError(f'{hc["inst"]}: member module/reset contract differs {item["inst"]}')
        out.append((i,pin))
    return out


def _code(s):
    return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))


def materialize(binder, tn, frame):
    from pathlib import Path
    import reset_tree as RT
    import qc_su_lane_cut as C
    t=binder.types[tn];groups=[h for h in t.get('hard_cores',[]) if h.get('bound_group')]
    if not groups:
        return []
    P=binder.wavefront_plan()
    if P is None:
        raise BoundGroupError('explicit post-bind groups require published wavefront reset')
    tree=RT.for_type(P,t.get('split_of',tn));targets={x['inst']:x for x in tree.get('core_resets',[])}
    text=frame.read_text();products=[];records=[]
    for hc in groups:
        c=hc['bound_group'];target=targets.get(hc['inst'])
        if target is None:
            raise BoundGroupError('group has no planned reset target '+hc['inst'])
        lane=int(re.fullmatch(r'u_lane(\d+)',hc['inst'])[1])
        rtl,new,report=C.cut(text,lane,hc['module'],memory_alignment=c['memory_alignment'])
        actual={(x['instance'].replace('u_u_','u_',1),x['module']) for x in report['leaves']}
        expected={(x['inst'],x['module']) for x in c['members']}
        net=f"rst_n_t{target['tap']}"
        if actual!=expected or report['reset_source']!=net:
            raise BoundGroupError(f'{hc["inst"]}: final member/reset projection differs, got{report["reset_source"]} expected{net}')
        reference=Path(binder.base)/'rtl/physical'/(hc['module']+'.sv')
        if not reference.is_file() or _code(reference.read_text())!=_code(rtl):
            raise BoundGroupError(f'{hc["inst"]}: grouped source differs from committed actual module')
        out=frame.parent/(hc['module']+'.sv')
        if out.exists() and _code(out.read_text())!=_code(rtl):
            raise BoundGroupError('group module has inconsistent source across types '+hc['module'])
        out.write_text(rtl);products.append(out);text=new
        records.append(dict(inst=hc['inst'],module=hc['module'],reset_net=net,member_count=5,added_cycles=0,source_matches_committed=True))
    binder.__dict__.setdefault('bound_group_records',{})[tn]=records
    frame.write_text(text)
    (frame.parent/(frame.stem+'.bound_groups.json')).write_text(json.dumps(dict(groups=records),indent=1)+'\n')
    return products


def scope_for_member(t, rel):
    found=[h['inst'] for h in t.get('hard_cores',[]) if any(m['inst']==rel for m in h.get('bound_group',{}).get('members',[]))]
    if len(found)>1:
        raise BoundGroupError('member occurs in multiple explicit groups '+rel)
    return found[0]+'.' if found else ''
