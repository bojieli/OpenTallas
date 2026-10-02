"""Finite shared-resource calendars and atomic collective readiness rendezvous."""
from collections import deque
from fractions import Fraction

PERIOD={'streaming':Fraction(5,6),'serial':Fraction(10,9)}

def price(specs, resources, rendezvous):
    groups={nid:nid for nid in specs};members={}
    for gid,nodes in rendezvous.items():
        if gid in specs:
            raise ValueError('rendezvous ID aliases an event')
        if not isinstance(nodes,list) or len(nodes)!=4 or len(set(nodes))!=4:
            raise ValueError('collective rendezvous requires four distinct rank participants')
        if any(n not in specs or groups[n]!=n for n in nodes):
            raise ValueError('unknown/duplicate rendezvous participant')
        bases={n.rsplit('.R',1)[0] for n in nodes};ranks={n.rsplit('.R',1)[1] for n in nodes}
        if len(bases)!=1 or ranks!={'0','1','2','3'} or any(specs[n]['unit']!=6 for n in nodes):
            raise ValueError('rendezvous must bind same original collective on TP4')
        for n in nodes:groups[n]=gid
        members[gid]=nodes
    for nid in specs:
        if specs[nid]['unit']==6 and groups[nid]==nid:
            raise ValueError('peer collective readiness unbound')
        members.setdefault(groups[nid],[])
        if nid not in members[groups[nid]]:members[groups[nid]].append(nid)
    for rid,r in resources.items():
        if r.get('scope') not in ('global','rank') or r.get('domain') not in PERIOD:
            raise ValueError('explicit resource scope/domain required: '+rid)
        if not r.get('ownership') or not r.get('source_receipts'):
            raise ValueError('resource owner/source identity required: '+rid)
        for key in ('issue_interval_cycles','minimum_issue_cycles'):
            if not isinstance(r[key],int) or isinstance(r[key],bool) or r[key]<1:
                raise ValueError('positive finite resource II floor')
        if r['issue_interval_cycles']<r['minimum_issue_cycles']:
            raise ValueError('resource II below source issue floor')
        if 'capacity_bits_per_cycle' in r and (not isinstance(r['capacity_bits_per_cycle'],int) or r['capacity_bits_per_cycle']<1):
            raise ValueError('positive finite channel capacity')
    edges={g:{} for g in members};reservations={};prior_provider={}
    def edge(src,dst,delay):
        if src==dst:raise ValueError('peer accept/completion cycle inside rendezvous; use prior readiness events')
        edges[dst][src]=max(edges[dst].get(src,Fraction(0)),delay)
    for nid,s in specs.items():
        b=s['binding'];c=b['calendar'];p=s['period'];g=groups[nid]
        if not b.get('resource_coverage_receipts') or not b.get('resource_claims'):
            raise ValueError('actual bank/channel/engine resource coverage unbound: '+nid)
        for dep in s['dependencies']:
            edge(groups[dep],g,specs[dep]['binding']['calendar']['complete_cycles']*specs[dep]['period'])
        accepts=c.get('acceptance_dependencies',[])
        if len(set(accepts))!=len(accepts) or any(d not in specs for d in accepts):
            raise ValueError('unknown acceptance readiness dependency')
        for dep in ([s['previous']] if s['previous'] else [])+accepts:
            edge(groups[dep],g,specs[dep]['binding']['calendar']['accept_cycles']*specs[dep]['period'])
        key=(nid.rsplit('.R',1)[1],b['provider'])
        if key in prior_provider:
            old=prior_provider[key]
            edge(groups[old],g,specs[old]['binding']['calendar']['issue_interval_cycles']*specs[old]['period'])
        prior_provider[key]=nid
        seen=set();ingress=False
        for claim in b['resource_claims']:
            rid=claim['resource']
            if rid in seen or rid not in resources:raise ValueError('duplicate/unknown resource claim')
            seen.add(rid);r=resources[rid]
            if not isinstance(claim['order'],int) or isinstance(claim['order'],bool) or claim['order']<0:
                raise ValueError('explicit finite reservation order')
            if claim['release'] not in ('issue','complete'):raise ValueError('reservation release contract')
            bits=claim['demand_bits']
            if not isinstance(bits,int) or isinstance(bits,bool) or bits<0:raise ValueError('finite transfer demand')
            if r.get('kind')=='collective_ingress':
                if r['scope']!='global' or 'capacity_bits_per_cycle' not in r:
                    raise ValueError('collective ingress requires global finite bandwidth')
                ingress=True
                if bits<s['collective_input_bits']:raise ValueError('collective transfer underpriced below actual descriptor input')
            instance=(rid,nid.rsplit('.R',1)[1] if r['scope']=='rank' else 'global')
            res=reservations.setdefault(instance,{})
            order=claim['order']
            if order in res and (res[order]['group']!=g or res[order]['release']!=claim['release']):
                raise ValueError('reservation order aliases independent requests')
            entry=res.setdefault(order,{'group':g,'nodes':[],'release':claim['release'],'bits':0})
            entry['nodes'].append(nid);entry['bits']+=bits
        if s['unit']==6 and not ingress:
            raise ValueError('collective shared ingress/channel demand omitted')
    resource_receipts=[]
    for (rid,instance),ordered in reservations.items():
        r=resources[rid];p=PERIOD[r['domain']];prior=None
        for order,entry in sorted(ordered.items()):
            cycles=r['issue_interval_cycles']
            if 'capacity_bits_per_cycle' in r:
                cycles=max(cycles,(entry['bits']+r['capacity_bits_per_cycle']-1)//r['capacity_bits_per_cycle'])
            hold=cycles*p
            if entry['release']=='complete':
                hold=max([hold]+[specs[n]['binding']['calendar']['complete_cycles']*specs[n]['period'] for n in entry['nodes']])
            if prior:edge(prior['group'],entry['group'],prior['hold'])
            entry['hold']=hold;prior=entry
            # Also bound this reservation's own completion by its finite transfer.
            if any(specs[n]['binding']['calendar']['complete_cycles']*specs[n]['period']<cycles*p for n in entry['nodes']):
                raise ValueError('calendar completion below shared channel/II demand')
            resource_receipts.append({'resource':rid,'instance':instance,'order':order,'group':entry['group'],
                'members':entry['nodes'],'total_demand_bits':entry['bits'],'reservation_hold_ns':float(hold)})
    pending={g:len(d) for g,d in edges.items()};users={g:[] for g in members}
    for g,deps in edges.items():
        for dep in deps:users[dep].append(g)
    ready=deque(g for g in members if pending[g]==0);starts={}
    while ready:
        g=ready.popleft();starts[g]=max([Fraction(0)]+[starts[d]+cost for d,cost in edges[g].items()])
        for user in users[g]:
            pending[user]-=1
            if pending[user]==0:ready.append(user)
    if len(starts)!=len(members):raise ValueError('cyclic resource/readiness calendar')
    completed={}
    for nid,s in specs.items():
        start=starts[groups[nid]];c=s['binding']['calendar'];p=s['period']
        completed[nid]=(start,start+c['accept_cycles']*p,start+c['complete_cycles']*p)
    return completed,resource_receipts
