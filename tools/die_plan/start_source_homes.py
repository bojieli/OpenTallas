#!/usr/bin/env python3
"""Propose actual mapped START cell row homes; no placement/clock qualification.

Whole actual source cells, including local reset gates and kept loads, are packed.
Actual native functional cell occupancy is not available and remains a hard hold.
"""
import argparse,collections,json,math,sys
from pathlib import Path
import schema as S
import die_trial as DT
from start_data_emit import box,overlaps,pin,distance


def propose(assembly,inventory,library,old_meta,new_contract,plan):
    cells=inventory['all_cells']; stages={s['id']:s for s in assembly['stages']}; owner={}; drivers={}
    for n,c in cells.items():
        for p,bits in c['connections'].items():
            if p in ('Y','QN','SN','CON'):
                for bit in bits: drivers[bit]=n
        for sid in stages:
            if n.startswith(('u_st_'+sid+'.','u_rst_'+sid+'.')):owner[n]=sid;break
    # Assign anonymous mapped output inverters to the actual QN source FF.
    for n,c in cells.items():
        if c['type'].startswith('INVx'):
            q=drivers.get(c['connections']['A'][0])
            if q in owner and cells[q]['type'].startswith('DFF'):owner[n]=owner[q]
    def cone(bit,sid,seen):
        n=drivers.get(bit)
        if not n or n in seen:return
        seen.add(n)
        if n in owner:return
        owner[n]=sid
        for p,bs in cells[n]['connections'].items():
            if p not in ('Y','QN','SN','CON','CLK'):
                for b in bs:cone(b,sid,seen)
    for n,c in cells.items():
        if c['type'].startswith('DFF'):
            for b in c['connections']['D']:cone(b,owner[n],set())
    # Native port buffers follow their real upstream source, not a synthetic leaf.
    for _ in range(10):
        changed=0
        for n,c in cells.items():
            if n in owner:continue
            os={owner[drivers[b]]for p,bs in c['connections'].items()if p not in ('Y','QN','SN','CON','CLK')for b in bs if drivers.get(b)in owner}
            if len(os)==1:owner[n]=next(iter(os));changed+=1
        if not changed:break
    root=next(s['id']for s in stages.values()if s['root'])
    unassigned=[n for n in cells if n not in owner]
    # Only a direct global raw-input buffer may lack a state-derived owner.
    for n in unassigned:
        if not cells[n]['type'].startswith('BUF'):raise ValueError(('unowned mapped logic',n,cells[n]['type']))
        owner[n]=root
    groups=collections.defaultdict(list)
    for n,sid in owner.items():groups[sid].append(n)
    site=DT.SiteMap(plan); placed=[]; homes={}; holds=[]; groupstats=[]
    old=old_meta['node_xy_um']; new=new_contract['clock_nodes']
    def xy(s):
        path=s['region'][3:]
        if path in new:return new[path]['xy'],'MODEL new clock vertex; source binding unqualified'
        if path in old:return old[path],'immutable old clock source coordinate; START load new'
        raise ValueError(('clock coordinate unavailable',s['region']))
    # Reserve conservative space around every represented stage clock node.
    clockpoints=dict(old)
    clockpoints.update({p:n['xy']for p,n in new.items()})
    clockboxes=[(x-2.16,y-.54,x+2.16,y+.54)for x,y in clockpoints.values()]
    clockidx=collections.defaultdict(list)
    for b in clockboxes:
        for ix in range(math.floor(b[0]/16),math.floor(b[2]/16)+1):
            for iy in range(math.floor(b[1]/16),math.floor(b[3]/16)+1):clockidx[ix,iy].append(b)
    def clockhits(r):
        return [b for ix in range(math.floor(r[0]/16),math.floor(r[2]/16)+1)for iy in range(math.floor(r[1]/16),math.floor(r[3]/16)+1)for b in clockidx[ix,iy]]
    def packed(sid,x,y):
        remaining=set(groups[sid]); bundles=[]
        for n in sorted(remaining):
            c=cells[n]
            if not c['type'].startswith('DFF'):continue
            q=c['connections']['QN'][0]
            gates=sorted(k for k in remaining if cells[k]['type'].startswith('INVx')and cells[k]['connections']['A']==[q])
            bundles.append([n]+gates);remaining.difference_update([n]+gates)
        bundles += [[n]for n in sorted(remaining)]
        result=[];row=0;xx=x
        for bundle in bundles:
            width=sum(library[cells[n]['type']]['size_um'][0]for n in bundle)
            if xx+width>x+8.64+1e-6:row+=1;xx=x
            if row>=3:return None
            for n in bundle:
                m=cells[n]['type']; yy=y+row*.27
                orient='R0'if round(yy/.27)%2==0 else'MX'
                c=dict(instance=n,master=m,xy_um=[round(xx,6),round(yy,6)],orient=orient)
                r=box(c,library)
                if not all(site.legal(p)for p in [(r[0],r[1]),(r[2],r[1]),(r[0],r[3]),(r[2],r[3])]):return None
                if any(overlaps(r,o)for o in clockhits(r)+placed):return None
                result.append(c);xx+=library[m]['size_um'][0]
        return result
    for sid in sorted(stages,key=lambda i:(len(stages[i]['region']),stages[i]['region'])):
        s=stages[sid];(cx,cy),kind=xy(s);candidates=[]
        x0=round((cx-4.32)/.054)*.054;y0=round((cy+1.08)/.27)*.27
        for dx in range(-12,13):
            for dy in range(-16,17):
                x=x0+dx*.54;y=y0+dy*.27
                candidates.append((abs(x+4.32-cx)+abs(y+.405-cy),x,y))
        found=None
        for cost,x,y in sorted(candidates):
            found=packed(sid,x,y)
            if found is not None:break
        if found is None:
            holds.append(dict(region=s['region'],reason='no 8.64x.81 actual-cell row tile under current declared obstacles'));continue
        for c in found:homes[c['instance']]=c;placed.append(box(c,library))
        groupstats.append(dict(region=s['region'],clock_xy_um=[cx,cy],clock_source=kind,cell_count=len(found),rect_um=[x,y,x+8.64,y+.81],
                               max_cell_to_clock_um=max(distance(c['xy_um'],[cx,cy])for c in found)))
    records=[]
    for z in inventory['source_records']:
        z=dict(z)
        if z.get('instance')in homes and z.get('ff_instance')in homes:
            c=homes[z['instance']];f=homes[z['ff_instance']]
            z.update(xy_um=c['xy_um'],orient=c['orient'],ff_xy_um=f['xy_um'],qn_pin_um=pin(f,'QN',library),input_pin_um=pin(c,'A',library),output_pin_um=pin(c,'Y',library))
            z['qn_to_inv_um']=distance(z['qn_pin_um'],z['input_pin_um'])
            z['output_sinks_homes']=[]
            for sink in z['all_output_sinks']:
                t=dict(sink)
                if sink['kind']=='iterm'and sink['instance']in homes:
                    t['pin_um']=pin(homes[sink['instance']],sink['pin'],library)
                    t['direct_point_distance_um']=distance(z['output_pin_um'],t['pin_um'])
                z['output_sinks_homes'].append(t)
        records.append(z)
    return dict(schema='ot_start_source_homes/1',physical_qualified=False,placed_source_cells=len(homes),expected_source_cells=len(cells),
                cells=homes,groups=groupstats,source_records=records,unallocated_groups=holds,
                holds=['proposed cells only: native functional standard cell occupancy absent','new clock vertices are model guides, not actual revised clock source',
                       'actual native reader/interface loads and local common clock tree unqualified','pin-to-pin routed geometry and tapcell/PG/retention/STA not qualified'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('assembly','inventory','library','old_meta','new_contract','plan'):p.add_argument('--'+n.replace('_','-'),required=True)
    p.add_argument('--out',required=True);a=p.parse_args();load=lambda f:json.loads(Path(f).read_text())
    d=propose(load(a.assembly),load(a.inventory),load(a.library)['cell_library'],load(a.old_meta),load(a.new_contract),S.Plan(S.load(a.plan)))
    Path(a.out).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:d[k]for k in ('placed_source_cells','expected_source_cells','unallocated_groups','physical_qualified')}))

if __name__=='__main__':main()
