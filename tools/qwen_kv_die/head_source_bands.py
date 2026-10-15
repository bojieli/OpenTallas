"""Producer-local N3 physical reservations before fresh die relay allocation.

This is an explicit plan-only candidate. Reservations are not fake hard macros,
and cannot be emitted as a die case before all physical/composition gates pass.
"""
import hashlib
import json
from pathlib import Path
import head_ingress_request as ingress


def reserve(m, F):
    if any(i.master.startswith('qkd_rly') for i in m['insts']):
        raise ValueError('source bands must precede ALL relay/reset allocation')
    if sum(i.master == 'qkd_rhead' for i in m['insts']) != 128:
        raise ValueError('N3 reservation requires actual128-head production shape')
    rows = [dict(name=i.name, master=i.master, x=i.x, y=i.y, w=i.w,
                 h=i.h, orient=i.orient) for i in m['insts']]
    changes = ingress.move_source_bands(rows)
    by = {i.name: i for i in m['insts']}
    for row in rows:
        it = by[row['name']]
        it.y, it.h = row['y'], row['h']
    _, _, homes, worst = ingress.capture_homes(rows)
    m['placement_keepouts'] = [F.Inst(h['name'], 'N3_CAPTURE_RESERVATION',
        *h['xy'], *h['size_um'], h['orient'], kind='reservation', region='attn')
        for h in homes]
    # Lane planning must follow the enlarged complete connected groups.
    m['geo']['grp_y'] = {st: (lo-237.6, hi+237.6)
                         for st, (lo, hi) in m['geo']['grp_y'].items()}
    m['head_source_bands'] = dict(adopted=False, qualified=False,
        status='PLAN_ONLY_N3_PHYSICAL_AND_COMPOSITION_GATES_REQUIRED',
        old_relays_reused=0, allocation='all buses and reset trees regenerated after band movement',
        die_outline_change_um=[0, 0], changes=changes, capture_reservations=homes,
        producer_to_candidate_pin_max_um=max(worst),
        missing=['actual535 hard view and native insertion/TT/FF/DRC',
                 'all128 native matched-bit chunk-to-T1-to-T2 gather homes',
                 'actual N3 RTL bindings and compensated clock/reset distribution',
                 'full8192 ECTL/head exact composition and observed failing mutants',
                 'static compiler extra edge and measured layer/token cost',
                 'fine cuts and real-view die GRT/STA'])


def write_failure(m, K, out, reason):
    """Preserve the rejected actual allocation; never emit a passing plan/case."""
    out.mkdir(parents=True, exist_ok=True)
    keepouts = m['placement_keepouts']
    def hit(a, b):
        return (min(a.x+a.w,b.x+b.w)-max(a.x,b.x) > .001 and
                min(a.y+a.h,b.y+b.h)-max(a.y,b.y) > .001)
    clashes = [(a.name,b.name) for a in keepouts for b in m['insts'] if hit(a,b)]
    rec = dict(schema='opentallas.qwen-n3-rejected-allocation.v1',
        qualified=False, adopted=False, status='REFUSED_UNREPAIRED_PIN_HOPS',
        reason=reason, source_sha256={str(p.relative_to(K.ROOT)):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__), Path(K.__file__), Path(ingress.__file__))},
        die_um=[m['die']['w'],m['die']['h']], geometry=K.check(m),
        capture_reservations=len(keepouts), capture_frame_collisions=clashes,
        pin_reach=K.pin_reach(m,K.masters(m,1)),
        relay_instances=sum(i.master.startswith('qkd_rly') for i in m['insts']),
        buses=m['buses'], assigned_ports=m.get('assigned_ports'),
        tree_depth=m.get('tree_depth'), head_source_bands=m['head_source_bands'])
    (out/'rejected_allocation.json').write_text(json.dumps(rec,indent=1)+'\n')
    (out/'rejected_insts.json').write_text(json.dumps([i.d() for i in m['insts']])+'\n')
    print(json.dumps({k:rec[k] for k in ('status','geometry','capture_reservations',
          'relay_instances','capture_frame_collisions')}))


def lifecycle(m, K):
    """Count actual regenerated FF edges, including later pin repair stages."""
    by={i.name:i for i in m['insts']}
    prefixes=('rst_die','rst_hbm','rst_host','rst_link','hboot',
              'hfwd_epoch','hfwd_link_rst_n')
    clocked={i for _,cls,_,eps in m['buses'] if cls=='clock_trunk' for i,_ in eps}
    depths={};missing=[]
    for prefix in prefixes:
        graph={};incoming=set()
        for bid,cls,_,eps in m['buses']:
            if not bid.startswith(prefix) or cls=='clock_trunk':continue
            driver=eps[0][0]
            graph.setdefault(driver,set()).update(i for i,_ in eps[1:])
            incoming.update(i for i,_ in eps[1:])
        from collections import deque
        nodes=set(graph)|incoming
        indegree={i:0 for i in nodes}
        for loads in graph.values():
            for dest in loads:indegree[dest]+=1
        ready=deque(i for i in nodes if not indegree[i])
        distance={i:0 for i in ready};visited=0
        while ready:
            node=ready.popleft();visited+=1
            for dest in graph.get(node,()):
                relay=by[dest].master.startswith('qkd_rly')
                distance[dest]=max(distance.get(dest,0),distance[node]+int(relay))
                if relay and dest not in clocked:missing.append(dest)
                indegree[dest]-=1
                if not indegree[dest]:ready.append(dest)
        if visited!=len(nodes):raise ValueError('reset/forwarding graph cycle: '+prefix)
        depths[prefix]=max(distance.values(),default=0)
    if missing:raise ValueError('unclocked regenerated reset/forwarding relays: '+str(missing[:5]))
    if max(depths.values(),default=0)>=K.RELAY_FLUSH:
        raise ValueError(f'N3 regenerated reset/forwarding depth{depths} reaches flush{K.RELAY_FLUSH}')
    m['head_source_bands']['pin_repair']=m.get('pin_repair')
    m['head_source_bands']['replan_stopped']=m.get('geo',{}).get('replan_stopped')
    m['head_source_bands']['lifecycle']=dict(depths=depths,relay_flush=K.RELAY_FLUSH,
        all_reset_forwarding_relays_clocked=True,normal_forwarding_calendar_qualified=False,
        obligation='Actual epoch/reset forwarding added edges must be consumed by peer static calendar and recovery/reset proof before adoption')
