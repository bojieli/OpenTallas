"""Explicit opt-in shared core clock inputs; no implicit fanout or latency credit."""
import math,re

_NAME=re.compile(r'^[A-Za-z_][A-Za-z0-9_$]*$')


def groups(P,tn):
    t=P.types[tn]; ck=t.get('clock',{}); gs=ck.get('core_groups',[])
    if not gs:return []
    if ck.get('core_taps')!='early':raise ValueError(f'{tn}: core_groups require explicit early core taps')
    taps={x['name']:x for x in ck.get('taps',[]) if x.get('kind')=='core'}
    cores={c['inst'] for c in t.get('hard_cores',[])}; used=set();ports=set();names=set()
    w,h=t['outline_um']
    for g in gs:
        for k in ('name','port','xy','members','insertion_ps','insertion_ff_ps','basis','source'):
            if k not in g:raise ValueError(f'{tn}: clock group missing {k}')
        if not _NAME.fullmatch(g['port']) or g['port'] in ports or g['port']=='clk' or re.fullmatch(r'clk_[ct]\d+',g['port']):raise ValueError(f'{tn}: invalid/duplicate/reserved group port')
        if g['name'] in names:raise ValueError(f'{tn}: duplicate group name')
        ports.add(g['port']);names.add(g['name'])
        x,y=g['xy']
        if not (0<=x<=w and 0<=y<=h):raise ValueError(f'{tn}: group input outside outline')
        if g['basis']!='parent_budget' or not isinstance(g['source'],str) or not g['source']:
            raise ValueError(f'{tn}: initial group API requires explicit parent_budget; measured release requires matching future SIGNED view contract')
        for k in ('insertion_ps','insertion_ff_ps'):
            v=g[k]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError(f'{tn}: explicit positive TT/FF group budget required')
        if not g['members']:raise ValueError(f'{tn}: empty group')
        local=set()
        for m in g['members']:
            if set(m)!={'inst','pin','tap'} or m['inst'] not in cores or not _NAME.fullmatch(m['pin']):raise ValueError(f'{tn}: exact existing instance/pin/tap required')
            ep=(m['inst'],m['pin'])
            if ep in used or ep in local:raise ValueError(f'{tn}: duplicate/overlapping grouped endpoint {ep}')
            local.add(ep)
            tap=taps.get(m['tap'])
            if tap is None or m['tap'] not in {m['inst'],m['inst']+'.'+m['pin']}:raise ValueError(f'{tn}: group member does not match existing core tap')
        used.update(local)
        for tap in {m['tap'] for m in g['members']}:
            # One original wildcard tap cannot be split between independent groups.
            if any(m['tap']==tap for z in gs if z is not g for m in z['members']):raise ValueError(f'{tn}: original core tap split across groups')
    return gs


def merge_taps(P,tn,ordinary):
    gs=groups(P,tn)
    if not gs:return ordinary
    removed={m['tap'] for g in gs for m in g['members']}
    out=[x for x in ordinary if x[3]['name'] not in removed]
    for g in gs:
        tp=dict(name=g['name'],kind='core',xy=g['xy'],insertion_ps=g['insertion_ps'],insertion_ff_ps=g['insertion_ff_ps'],note='Explicit shared group, parent budget only',core_group=g)
        out.append((g['port'],float(g['xy'][0]),float(g['xy'][1]),tp))
    return out


def network_manifest(P,tn):
    """Require complete explicit buffered network before any grouped kit generation."""
    result=[]
    for g in groups(P,tn):
        net=g.get('network')
        if not isinstance(net,dict) or set(net)!={'nodes','endpoints'} or not net['nodes']:raise ValueError(f'{tn}/{g["name"]}: complete physical network required before kit generation')
        seen={'@root'};nodes=[]
        for n in net['nodes']:
            if set(n)!={'name','parent','cell','ll_um','orient'} or not _NAME.fullmatch(n['name']) or n['name'] in seen or n['parent'] not in seen:raise ValueError(f'{tn}: unsafe/duplicate/out-of-order clock node')
            if not re.fullmatch(r'BUF[A-Za-z0-9_]+',n['cell']) or n['orient'] not in {'R0','MX','MY','R180'}:raise ValueError(f'{tn}: invalid clock node master/orientation')
            if len(n['ll_um'])!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in n['ll_um']):raise ValueError(f'{tn}: invalid physical node position')
            seen.add(n['name']);nodes.append(n)
        want={(m['inst'],m['pin']) for m in g['members']};got=set()
        for e in net['endpoints']:
            if set(e)!={'inst','pin','parent'} or e['parent'] not in seen-{'@root'} or (e['inst'],e['pin']) in got:raise ValueError(f'{tn}: invalid/duplicate endpoint wiring')
            got.add((e['inst'],e['pin']))
        if got!=want:raise ValueError(f'{tn}: physical endpoint membership differs from declared group')
        result.append(dict(g,network=dict(nodes=nodes,endpoints=net['endpoints']),release_qualified=False))
    return dict(schema='opentallas.core_clock_groups.v1',type=tn,groups=result,release_qualified=False)


def tcl_text(manifest):
    lines=['# Explicit grouped core clock network; other CP2 inputs are unchanged.', 'source /work/core_clock_groups.tcl']
    def q(x):
        x=str(x)
        if any(c in x for c in '{}\n\r'):raise ValueError('unsafe Tcl clock identifier')
        return '{'+x+'}'
    for g in manifest['groups']:
        members={(m['inst'],m['pin']):m for m in g['members']}
        nodes=' '.join('{'+ ' '.join(q(x) for x in [n['name'],n['parent'],n['cell'],*n['ll_um'],n['orient']]) +'}' for n in g['network']['nodes'])
        eps=' '.join('{'+ ' '.join(q(e[x]) for x in ('inst','pin','parent'))+' '+q(int(members[(e['inst'],e['pin'])]['tap']==e['inst'])) +'}' for e in g['network']['endpoints'])
        lines.append('::ot_ccg::setup [ord::get_db_block] '+q(g['port'])+' {'+nodes+'} {'+eps+'}')
    return '\n'.join(lines)+'\n'
