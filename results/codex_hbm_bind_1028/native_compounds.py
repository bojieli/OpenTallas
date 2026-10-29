"""Generate exact native SU lane/bank and SFU lane/map cut specifications.

Usage: native_compounds.py ASBUILT PLAN OUT_DIR
The output is a source candidate. Existing geometry is located by exact instance
names; this does not qualify a different physical kit or a latency profile.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E,bind_compose as C
abpath,planpath,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
F=E.flatten(json.loads(abpath.read_text()),'hbm_current_native_top');plan=json.loads(planpath.read_text())
slots={}
for part in plan['partitions']:
    for h in plan['partition_types'][part['type']].get('hard_cores',[]):
        slots[(part['name'][:2],h['inst'])]=(part['name'],h)
cells={c.path:c for c in F.cells};groups=[]
for role in ('NW','NE'):
    for g in range(4):
        pre=f'su_{role}{g}';buckets=collections.defaultdict(list)
        for n in range(32):
            lane=f'{pre}.u_slice.g_lane[{n}].g_pr.u_lane';bank=f'{pre}.u_slice.g_bank[{n}].u_bank'
            lc=cells[lane];assert lc.module=='ot_hbm_su_static_lane_pinreg'
            kind=int(lc.params.get('KIND','0'));assert kind in (0,1,2), (lane,kind)
            if kind!=2:
                assert lc.ports['side_y']==['0']*32,(lane,'nonzero SIDE')
                # Separately qualified exact zero-SIDE boundary variant.
                lc.module=lc.ytype='ot_hnx_su_pinreg_noside';lc.ports.pop('side_y');lc.dirs.pop('side_y')
            if kind==1:label='lane_exp_l' if n==15 else f'lane_exp{n}'
            else:
                plain=n-16 if g<2 else n;start=4*(plain//4)
                label=f'lanes_plain{start}_{start+3}' if g<2 else f'lanes{start}_{start+3}'
            buckets[label].append((n,bank,lane))
        for label,parts in buckets.items():
            inst=f'u_su_Q{g}_{label}';partition,slot=slots[(role,inst)]
            members=[]
            for j,(_,bank,lane) in enumerate(parts):members.extend([(bank,'bank'),(lane,'lane')])
            groups.append(dict(path=pre+'.__cut_'+label,partition=partition,inst=inst,slot=slot,members=members,family='su_exp' if label.startswith('lane_exp') else 'su_plain4'))
        path=f'{pre}.u_slice.g_pretree.u_pt';inst=f'u_su_Q{g}_pretree';partition,slot=slots[(role,inst)]
        groups.append(dict(path=pre+'.__cut_pretree',partition=partition,inst=inst,slot=slot,members=[(path,'pretree')],family='su_pretree'))
    for n in range(16):
        pre=f'sfucore_{role}.u_core.u_engine.u_arithmetic.u_grid.g_lane[{n}]';inst=f'u_sfucore_Q_lane{n}';partition,slot=slots[(role,inst)]
        groups.append(dict(path=f'sfucore_{role}.__cut_lane{n}',partition=partition,inst=inst,slot=slot,members=[(pre+'.g_mono.u_map','map'),(pre+'.u_sfu','lane')],family='sfu_lane'))
outside=collections.defaultdict(set)
for c in F.cells:
    for bs in c.ports.values():
        for b in bs:
            if isinstance(b,int):outside[b].add(c.path)
topnets={b for _,bs in F.top_ports.values() for b in bs if isinstance(b,int)}
# Absorb only actual FF output bits with exclusive native-cut consumers.
# Mixed aggregate Yosys FF vectors are partitioned explicitly; every residual
# bit remains in parent glue. No combinational cone or shared output is moved.
consumers=collections.defaultdict(set)
for c in F.cells:
    for pn,bs in c.ports.items():
        if c.dirs[pn]=='input':
            for b in bs:
                if isinstance(b,int):consumers[b].add(c.path)
owner={p:gi for gi,g in enumerate(groups) for p,_ in g['members']}
primitive_splits=[];glue_groups=collections.defaultdict(list)
for c in F.cells:
    if c.kind!='glue' or c.ytype not in ('$dff','$adff') or not re.match(r'su_(NW|NE)[0-3]\.u_slice\.',c.path):continue
    buckets=collections.defaultdict(list)
    for i,b in enumerate(c.ports['Q']):
        loads=consumers[b]-{c.path} if isinstance(b,int) else set()
        gs={owner.get(p)for p in loads}
        gi=next(iter(gs))if b not in topnets and loads and len(gs)==1 and None not in gs else None
        buckets[gi].append(i)
    if set(buckets)=={None}:continue
    fragments=[]
    for gi,indices in sorted(buckets.items(),key=lambda kv:-1 if kv[0] is None else kv[0]):
        path=c.path if gi is None or len(buckets)==1 else c.path+'.__native_cut_'+str(gi)
        fragments.append(dict(path=path,bits=indices))
        if gi is not None:glue_groups[gi].append(path)
    if len(buckets)>1:primitive_splits.append(dict(member=c.path,fragments=fragments))
from bind_primitive_split import split_cells
F.cells,primitive_receipt=split_cells(F.cells,primitive_splits,E.Cell)
cells={c.path:c for c in F.cells}
for gi,paths in glue_groups.items():
    groups[gi]['members'].extend((p,'cmd'+str(j))for j,p in enumerate(paths))
# Recompute incidence after exact FF fragmentation.
outside=collections.defaultdict(set)
for c in F.cells:
    for bs in c.ports.values():
        for b in bs:
            if isinstance(b,int):outside[b].add(c.path)
mapping={};cores=[];records=[]
for gi,g in enumerate(groups):
    ms={p for p,_ in g['members']};drivers=collections.Counter(b for p,_ in g['members'] for pn,bs in cells[p].ports.items() if cells[p].dirs[pn]=='output' for b in bs if isinstance(b,int))
    boundary={b for p,_ in g['members'] for bs in cells[p].ports.values() for b in bs if isinstance(b,int) and (outside[b]-ms or b in topnets)}
    ports=collections.OrderedDict();positions={};params={}
    for path,role in g['members']:
        c=cells[path];params[path]=dict(c.params)
        for pn,bs in c.ports.items():
            direction=c.dirs[pn];name=role+'_'+pn
            # Preserve the existing bank clock equality exactly, rather than
            # creating three physical clocks for a single native bank input.
            if role=='bank' and pn in ('clk_rd','clk_ws'):
                assert bs==c.ports['clk'];name='bank_clk'
            entries=[]
            for i,b in enumerate(bs):
                is_id=name in ('lane_lane_id','map_lane_j')
                expose=(is_id or isinstance(b,int) and b in boundary and (direction=='output' or not drivers[b]))
                if not expose:continue
                anchor=dict(member=path,port=pn,bit=i)
                # A bank's clk/rd/ws pins are exactly the same original net.
                if name=='bank_clk' and pn!='clk':
                    indices=positions[(path,'clk')];ports[name]['bits'][indices[i]].append(anchor)
                else:entries.append((i,anchor,b))
            if entries:
                p=ports.setdefault(name,dict(dir=direction,bits=[]));assert p['dir']==direction
                indices={}
                for i,anchor,b in entries:
                    indices[i]=len(p['bits']);p['bits'].append([anchor])
                positions[(path,pn)]=indices
    # One exact native net needs one public input bit, while every original
    # endpoint remains an explicit alias anchor. Never coalesce by name/value.
    # Position-ID constants stay separate explicit inputs as before.
    input_aliases={}
    for name in list(ports):
        p=ports[name]
        if p['dir']!='input' or name in ('lane_lane_id','map_lane_j'):continue
        unique=[]
        for anchors in p['bits']:
            a=anchors[0];b=cells[a['member']].ports[a['port']][a['bit']]
            if isinstance(b,int) and b in input_aliases:input_aliases[b].extend(anchors)
            else:
                unique.append(anchors)
                if isinstance(b,int):input_aliases[b]=anchors
        if unique:p['bits']=unique
        else:del ports[name]
    for name,p in ports.items():
        if name in ('lane_lane_id','map_lane_j'):
            values=[cells[a[0]['member']].ports[a[0]['port']][a[0]['bit']] for a in p['bits']]
            assert all(v in ('0','1') for v in values)
            params[name+'_position_id']=dict(width=len(values),value=sum((b=='1')<<i for i,b in enumerate(values)))
    mod=f'ot_hnx_{g["family"]}_candidate_{gi}'
    cores.append(dict(inst=g['path'],module=mod,members=[p for p,_ in g['members']],ports=ports))
    mapping[g['path']]=[g['partition'],g['inst']]
    for j,(p,role) in enumerate(g['members']):mapping[p]=[g['partition'],g['inst']+'.'+role+str(j)]
    records.append(dict(source_path=g['path'],partition=g['partition'],plan_inst=g['inst'],family=g['family'],previous_module=g['slot']['module'],source_params=params,ports={n:dict(direction=p['dir'],width=len(p['bits'])) for n,p in ports.items()},status='SOURCE_CANDIDATE_PHYSICAL_REQUALIFICATION_REQUIRED'))
class Rules:
    def part_of(self,path):return mapping[path][0] if path in mapping else None
sources,receipt=C.compose(F,Rules(),dict(allow_glue=True,cores=cores),E.Cell)
# Share masters only when the complete generated native structure is identical;
# source position IDs are explicit public ports and are not baked into types.
masters={};rename={}
for mod,text in sources:
    normalized=text.replace('module '+mod+' (','module TEMPLATE (',1)
    digest=hashlib.sha256(normalized.encode()).hexdigest()[:12]
    new=mod.rsplit('_candidate_',1)[0]+'__'+digest
    rename[mod]=new;masters.setdefault(new,text.replace('module '+mod+' (','module '+new+' (',1))
for core,row in zip(cores,records):core['module']=row['module']=rename[core['module']]
(out/'compose.json').write_text(json.dumps(dict(allow_glue=True,primitive_splits=primitive_splits,cores=cores),separators=(',',':'))+'\n')
(out/'map.json').write_text(json.dumps(dict(parts=mapping),indent=1)+'\n')
(out/'masters.sv').write_text('`default_nettype none\n'+'\n'.join(masters.values())+'`default_nettype wire\n')
(out/'packet.json').write_text(json.dumps(dict(cores=records,masters=list(masters),source_terminal_equality=receipt['terminal_equality'],primitive_splits=primitive_receipt,absorbed_glue_cells=sum(map(len,glue_groups.values())),added_cycles=0,note='Exact actual native members. New cut ports/masters must replace old extracted aliases and receive physical qualification; no old-kit equivalence claim.'),indent=2)+'\n')
print('native compounds',len(cores),'masters',len(masters),'terminal equality',receipt['terminal_equality'])
