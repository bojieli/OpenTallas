"""Place four real upper-tree leaves and connect their exact lane slices.

No parent logic or extra pin stage is inserted. Synthetic endpoint names only
partition wires: the netlist and LEF writers join them onto real RTL port bits.
"""
from pathlib import Path
import copy
import os

MASTER = 'ot_qfd_band_upper'
PARAMS = dict(NL=4, NB=3, LNK=0, DLY=1, TREE_LAT=7, TCUT=7, LG=12, RPIN=1)
VIEW = 'physical/ref_tile/qfd_tt_up4_tp8/views/ot_qfd_band_upper'


def joins():
    leaf = {}
    band = {'tt_uv': ('tt', [1536,1537])}
    for b in range(3):
        leaf[f'pw_b{b}'] = ('pw', list(range(128*b,128*(b+1))))
        leaf[f'pv_b{b}'] = ('pw_v',[b])
        leaf[f'lf_b{b}'] = ('lf',[b])
    for l in range(4):
        band[f'pw_l{l}_d'] = (f'pw_l{l}',list(range(128)))
        band[f'pw_l{l}_v'] = (f'pw_l{l}',[128])
        band[f'f_up_l{l}'] = ('f_up',[l])
        band[f'tt_l{l}'] = ('tt',[128*l+j+512*k for k in range(3) for j in range(128)])
    return {MASTER:leaf,'qfd_sp_band_lanes':band,
            'qfd_tt_ctlm':{f'uf_l{l}':('uf',[l]) for l in range(4)},
            'qfd_tt_ctlm_static_s':{f'uf_l{l}':('uf',[l]) for l in range(4)}}


def apply(v, m):
    by={i.name:i for i in m['insts']}
    parent=by['tt_up4_0']
    proposal=None
    if os.environ.get('OT_SPLIT_REPACK')=='1':
        from qwen_split.placement_repack import apply as repack
        proposal=repack(v,m)
    leaves=[]
    anchor=copy.copy(parent)
    anchor.name='up4_sel_station';anchor.master='qfd_rly_26_NE_9x9'
    anchor.x=round(parent.x+153.36,4);anchor.y=round(parent.y+95.04,4)
    anchor.w=anchor.h=8.64;anchor.orient='R0';anchor.kind='relay'
    for l in range(4):
        i=copy.copy(parent)
        i.name=f'tt_up4_leaf{l}';i.master=MASTER
        i.w,i.h=64.8,205.2
        if proposal:
            p=proposal['candidate_leaves'][l]
            i.x,i.y=p['x'],p['y']
        else:
            i.x=round(parent.x+l*(64.8+19.44),4);i.y=parent.y
        i.orient='R0'
        leaves.append(i)
    if not proposal and leaves[-1].x+leaves[-1].w>parent.x+parent.w+.001:
        raise ValueError('four direct upper leaves do not fit the accepted slot')
    anchors=[anchor]
    if proposal:
        # Three small physical selector stations form a two-level local tree.
        # The vertical leaf stack spans>490um; no long unrelayed fanout hides
        # behind a common control net. Each child tree spans two leaves only.
        for j,gap_leaf in enumerate((1,0,2)):
            a=anchor if j==0 else copy.copy(anchor)
            a.name='up4_sel_station' if j==0 else f'up4_sel_branch{j-1}'
            a.x=round(leaves[0].x+28.08,4)
            a.y=round(leaves[gap_leaf].y+205.2+5.4,4)
            if j:anchors.append(a)
    m['insts']=[i for i in m['insts'] if i.name!=parent.name]+leaves+anchors
    B=[];seen=set()
    for bid,cl,n,es in m['buses']:
        if not any(i==parent.name for i,p in es):
            B.append((bid,cl,n,es));continue
        seen.add(bid)
        if bid.startswith('pword_'):
            b=int(bid.split('_')[1]);src=es[0]
            if src!=(f'sp_band_lanes_{b}','pw') or n!=513:
                raise ValueError(f'{bid}: unexpected source packing {n}/{es}')
            for l in range(4):
                B.append((f'{bid}_l{l}',cl,128,[(src[0],f'pw_l{l}_d'),(leaves[l].name,f'pw_b{b}')]))
                B.append((f'{bid}_v{l}',cl,1,[(src[0],f'pw_l{l}_v'),(leaves[l].name,f'pv_b{b}')]))
        elif bid.startswith('tt_lf'):
            b=int(bid.removeprefix('tt_lf'))
            for l in range(4):
                B.append((f'{bid}_l{l}',cl,1,[(es[0][0],f'f_up_l{l}'),(leaves[l].name,f'lf_b{b}')]))
        elif bid=='tt_ty':
            if n!=1538 or es[-1]!=('sp_band_lanes_0','tt'):
                raise ValueError('unexpected upper return packing')
            for l in range(4):
                B.append((f'tt_ty_l{l}',cl,384,[(leaves[l].name,'tt_ty'),('sp_band_lanes_0',f'tt_l{l}')]))
            B.append(('tt_ty_uv',cl,2,[(leaves[0].name,'uv'),('sp_band_lanes_0','tt_uv')]))
        elif bid=='o4_upf':
            for l in range(4):
                B.append((f'o4_upf_l{l}',cl,1,[(leaves[l].name,'fault'),('tt_ctlm',f'uf_l{l}')]))
        elif bid=='o4_sel':
            B.append((bid,cl,n,[es[0],(anchor.name,'a')]))
            if proposal:
                B.append(('up4_sel_split',cl,n,[(anchor.name,'b')]+[(a.name,'a') for a in anchors[1:]]))
                for k,a in enumerate(anchors[1:]):
                    B.append((f'up4_sel_local{k}',cl,n,[(a.name,'b')]+[(i.name,'sel') for i in leaves[2*k:2*k+2]]))
            else:
                B.append(('up4_sel_local',cl,n,[(anchor.name,'b')]+[(i.name,'sel') for i in leaves]))
        elif cl in ('clock_trunk','reset'):
            # Reuse the actual delivered root/release tree, with one entry per
            # hardened leaf; the retired pin-stage clock disappears entirely.
            E=[]
            for i,p in es:
                E.extend([(q.name,'clk' if cl=='clock_trunk' else 'rst_n') for q in leaves] if i==parent.name else [(i,p)])
            if cl=='clock_trunk':
                E.extend((a.name,'ck') for a in anchors)
            B.append((bid,cl,n,E))
        else:
            raise ValueError(f'unclassified upper-parent connection {bid}/{cl}: {es}')
    required={f'pword_{b}' for b in range(3)}|{f'tt_lf{b}' for b in range(3)}|{'tt_ty','o4_upf','o4_sel'}
    if not required<=seen:
        raise ValueError(f'missing upper parent buses: {required-seen}')
    m['buses']=B
    m['port_split'][MASTER]={'sel':[('sel_e',13),('tv_e',13)],'uv':[('tt_use',1),('tt_v',1)]}
    j=m.setdefault('port_join',{})
    for name,parts in joins().items():
        j.setdefault(name,{}).update(parts)
    m.setdefault('master_params',{})[MASTER]=dict(PARAMS)
    # Equal path ages are a real compiler contract, not an assumed fanout.
    for b in range(3):
        m.setdefault('relay_equal_groups',{})[f'up4_pword_{b}']=[f'pword_{b}_l{l}' for l in range(4)]+[f'pword_{b}_v{l}' for l in range(4)]
    m.setdefault('relay_equal_groups',{})['up4_return']=[f'tt_ty_l{l}' for l in range(4)]+['tt_ty_uv']
    m['direct_up4']=dict(master=MASTER,view=VIEW,params=PARAMS,
        leaves=[dict(name=i.name,x=i.x,y=i.y,w=i.w,h=i.h) for i in leaves],
        added_data_edges=0,retired_parent_pin_edges=2,
        control_stations=[dict(name=a.name,x=a.x,y=a.y,master=a.master) for a in anchors],
        control_fanout_edges=2 if proposal else 1,
        fault_contract='four independent leaf faults into actual controller uf[3:0]',
        timing_qualification='requires exact native view, routed joins and fixed equal relay ages')
    return m['direct_up4']


def partition_master(q, join_map, rects):
    """Split the real face pins into synthetic wire fragments without moving them."""
    points={}
    original={}
    for name,layer,r in rects:
        base,_,bit=name.partition('[')
        k=int(bit[:-1]) if bit else 0
        points[(base,k)]=(layer,((r[0]+r[2])/2,(r[1]+r[3])/2))
        original[(base,k)]=(layer,tuple(r))
    remove={p for real,_ in join_map.values() for p in [real]}
    keep={p:s for p,s in q.ports.items() if p not in remove}
    q.ports=keep;q.order=[p for p in q.order if p in keep]
    for alias,(real,indexes) in join_map.items():
        data=[points[(real,k)] for k in indexes]
        if len({L for L,_ in data})!=1:
            raise ValueError(f'{q.name}.{alias}: fragment spans incompatible pin layers')
        q.ports[alias]=('xy',len(data),data[0][0],[xy for _,xy in data],1)
        # XY remains the net/reach endpoint, but is insufficient to reconstruct
        # a face rectangle. Shortening it around its centre leaves the pin
        # inset under the parent's OBS (C21s DRT-0073 on joined face ports).
        if not hasattr(q,'assigned_fragment_rects'):
            q.assigned_fragment_rects={}
        q.assigned_fragment_rects[alias]=[original[(real,k)] for k in indexes]
        q.order.append(alias)


def install_leaf_master(M, model, Master, view):
    """Use the real closed leaf pin plan; fail if the physical view is absent."""
    if not model.get('direct_up4'):
        return
    if view is None:
        raise ValueError('direct upper-tree leaf requires its published real LEF')
    w,h,P=view
    if (w,h)!=(64.8,205.2):
        raise ValueError(f'upper-tree leaf changed outline: {w}/{h}')
    q=Master(MASTER,w,h,5,'Direct real CLOSED four-lane upper-tree leaf; independent clock entry')
    parts={p:(p,list(range(n))) for p,n in [('pw',384),('pw_v',3),('lf',3),('tt_ty',384),('clk',1),('rst_n',1),('fault',1)]}
    for p in ('pw','pw_v','lf'):
        parts.pop(p)
    parts.update(joins()[MASTER])
    parts.update(sel=('__sel__',list(range(26))),uv=('__uv__',list(range(2))))
    for alias,(real,indexes) in parts.items():
        if real=='__sel__':
            names=[f'sel_e[{j}]' for j in range(13)]+[f'tv_e[{j}]' for j in range(13)]
        elif real=='__uv__':
            names=['tt_use','tt_v']
        else:
            names=[real if real in P and len(indexes)==1 else f'{real}[{k}]' for k in indexes]
        data=[P[n] for n in names]
        if len({p[:2] for p in data})!=1:
            raise ValueError(f'{MASTER}.{alias}: pin fragment spans faces/layers')
        f,L,_=data[0]
        q.ports[alias]=('pins',len(data),f,L,[pos for _,_,pos in data],1)
        q.order.append(alias)
    M[MASTER]=q
    a=Master('qfd_rly_26_NE_9x9',8.64,8.64,3,'Real26-bit registered local selector fanout; one compiled control edge')
    a.face('a',26,'N','M5',4.32,2)
    a.face('b',26,'E','M4',4.32,2)
    a.face('ck',1,'S','M5',2.16,1)
    M[a.name]=a


def equal_age_pads(stages, groups, existing=None):
    """Exact extra registered stages for wire-fragment groups, never a waiver."""
    pads=dict(existing or {})
    for group,names in groups.items():
        have=[n for n in names if n in stages]
        if not have:
            continue  # a completely removed historical group is not this die
        if len(have)!=len(names):
            raise ValueError(f'{group}: incomplete fixed-age physical group')
        target=max(stages[n]+pads.get(n,0) for n in names)
        for n in names:
            if stages[n]<target:
                pads[n]=target-stages[n]
    return pads
