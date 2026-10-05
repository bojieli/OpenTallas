#!/usr/bin/env python3
"""Fixed-count first-hop repair, with explicit unresolved downstream routes."""
import argparse,bisect,gzip,hashlib,json,math,re
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
import dsrom_capture_clock_selected_union as C
import dsrom_capture_selected_bank_escape as E
B=E
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_clock_branch_reallocation_20261003'
def tech():
 for r in json.loads((BASE/'inputs/origins.json').read_text()):
  if hashlib.sha256((BASE/'inputs'/r['copy']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Tech origin drift')
 g=json.loads((BASE/'inputs/grid.json').read_text());s=gzip.decompress((BASE/'inputs/tech.lef.gz').read_bytes()).decode()
 if 'DIRECTION HORIZONTAL' not in re.search(r'LAYER M2\n(.*?)END M2',s,re.S)[1] or 'DIRECTION VERTICAL' not in re.search(r'LAYER M3\n(.*?)END M3',s,re.S)[1]:raise ValueError('Directional grid changed')
 return g

def via(g,name,x,y,net):
 return [dict(net=net,layer=r['layer'],bbox_DBU=[x+r['bbox'][0],y+r['bbox'][1],x+r['bbox'][2],y+r['bbox'][3]],via=name) for r in g['tech_via_definitions'][name]]

def m3_phase(g):
 rows=next(r['X'] for r in g['grids'] if r['layer']=='M3')
 if len(rows)!=1:raise ValueError('M3 phase ambiguous')
 return rows[0][0]%rows[0][2],rows[0][2]

def local_escape(c,pin,g,lef):
 # Exactly one fixed construction, not a route sweep: middle of literal
 # vertical A or Y pin, M2 horizontal to nearest M3 phase, local M3 landing.
 x,y=c['bbox_DBU'][:2];px=27 if pin=='A' else 348;py=135
 a=via(g,'VIA12',x+px,y+py,c.get('instance',c.get('proposed_site_ID'))+'.'+pin)
 m1=next(r['bbox_DBU'] for r in a if r['layer']=='M1')
 if not any(B.contained(m1,B.transform(s,c)) for s in B.shapes(lef,pin)):raise ValueError('M1 landing outside literal pin')
 offset,pitch=m3_phase(g);vx=offset+math.floor((x+px-offset)/pitch+0.5)*pitch
 net=a[0]['net'];v23=via(g,'VIA23',vx,y+py,net)
 # >=38x18 M2 rectangle covers both landing polygons and minimum area666.
 lo=min(x+px-14,vx-14);hi=max(x+px+14,vx+14)
 if hi-lo<38:lo-=5;hi+=5
 stub=dict(net=net,layer='M2',bbox_DBU=[lo,y+py-9,hi,y+py+9])
 if (hi-lo)*18<666:raise ValueError('M2 minimum area')
 return dict(cell=c.get('instance',c.get('proposed_site_ID')),pin=pin,pin_orientation=c['orientation'],actual_net_assignment=None,shapes=a+[stub]+v23,M3_track_phase_extended_not_live_DEF=True,M1_literal_landing_contained=True,port_route_above_M3_not_bound=True)

def pg_feed(name,box,rails,g,clearance_left_DBU):
 # Two independent M3 trunks in existing left gap; horizontal M1 rail
 # extensions with local VIA12+VIA23 patches outside all cell bodies.
 off,pitch=m3_phase(g);right=off+math.floor((box[0]-72-off)/pitch)*pitch;left=right-2*pitch
 if left-14<clearance_left_DBU:raise ValueError('PG feed exceeds named left gap')
 xs={'VDD':left,'VSS':right};shapes=[]
 for r in rails:
  b=r['bbox_DBU'];y=(b[1]+b[3])//2;net=name+'.'+r['net'];x=xs[r['net']]
  if y%270:raise ValueError('Source row phase not covered by M2 phase0')
  shapes.append(dict(net=net,layer='M1',bbox_DBU=[x-9,y-9,b[0]+18,y+9],role='rail_extension'))
  shapes+=via(g,'VIA12',x,y,net)+via(g,'VIA23',x,y,net)
 for n,x in xs.items():
  yy=[(r['bbox_DBU'][1]+r['bbox_DBU'][3])//2 for r in rails if r['net']==n]
  shapes.append(dict(net=name+'.'+n,layer='M3',bbox_DBU=[x-9,min(yy)-14,x+9,max(yy)+14],role='local_feed_trunk'))
 return dict(name=name,existing_left_gap_DBU=box[0]-clearance_left_DBU,proposed_left_extent_DBU=left-14,local_rail_taps=len(rails),VIA12_instances=len(rails),VIA23_instances=len(rails),required_external_supply_terminals=[name+'.VDD',name+'.VSS'],upstream_supply_current_EM_voltage_drop=None,global_PG_OBS_overlap_unproven=True,shapes=shapes)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def candidates(box,existing,shard,common=False):
    rows={y:[] for y in range(box[1]+270,box[3]-269,540)}
    for cell in existing:
        b=cell['bbox_DBU']
        for y in (b[1],b[1]-270):
            if y in rows and overlap(b,[box[0],y,box[2],y+270]):rows[y].append((max(box[0],b[0]),min(box[2],b[2])))
    out=[]
    for y,occ in rows.items():
        cur=box[0]
        for a,b in sorted(occ)+[(box[2],box[2])]:
            x=math.ceil(cur/54)*54
            while x+378<=a:
                out.append(dict(proposed_site_ID=f's{shard}.{"common" if common else "raw"}.{x}.{y}',master='BUFx4_ASAP7_75t_R',bbox_DBU=[x,y,x+378,y+270],orientation='MX',home='common' if common else 'raw'))
                x+=378
            cur=max(cur,b)
    return out

def gap(a,A,b,B):return max(0,b-A,a-B)
def access(source,site,apins,rc):
    x,y,_,Y=site['bbox_DBU'];best=math.inf
    for r in source:
        a,b,A,B=r['bbox_DBU']
        for p in apins:
            pa,pb,pA,pB=p['bbox_DBU'] if isinstance(p,dict) else p
            # MX reflection, literal A rectangles, not centre-only distances.
            v=(gap(a,A,x+pa,x+pA)*rc['M8']+gap(b,B,Y-pB,Y-pb)*rc['M9'])/1000
            best=min(best,v)
    return best

def build(outdir):
    origins=json.loads((BASE/'inputs/origins.json').read_text())
    for r in origins:
        if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('Arch input drift')
    arch_access=json.loads((BASE/'inputs/arch_access.json').read_text());d=C.inputs();arch=d['model.json']
    old=json.loads((C.BASE/'model.json').read_text());rc=old['restricted_route_family_RC_fF_per_um']
    hd,_=C.H.H.inputs();lef=hd['cell_LEF.json']['BUFx4_ASAP7_75t_R'];apins=E.shapes(lef,'A')
    cases={};grid=tech();outdir.mkdir(parents=True,exist_ok=True)
    for s in (0,1):
        raw=arch['physical_shards'][str(s)];cells=d[f'shard{s}_cells.jsonl.gz'];nets={n['name']:n for n in d[f'shard{s}_clock_nets.jsonl.gz']}
        branch_path=C.BASE/f'shard{s}_clock_branches.json.gz'
        if sha(branch_path)!=old['per_shard_raw_clock_correction_proposals'][s]['branch_sha256']:raise ValueError('Source branch drift')
        branches=json.loads(gzip.decompress(branch_path.read_bytes()))
        rawsites=candidates(raw['raw_slot_bbox_DBU'],cells,s);common=candidates(raw['shifted_control_bbox_DBU'],cells,s,True)
        # Common is not asserted empty of UNPLACED control logic. Reserve these
        # sites explicitly against the future common owner, not free-space credit.
        cuts={(b['net'],b['destination']) for b in arch_access['shards'][str(s)]['raw_only_first_hop_cut_witnesses']}
        pools={'raw':rawsites,'common':common};trees={h:cKDTree(np.array([[v['bbox_DBU'][0]+27,v['bbox_DBU'][1]+135] for v in vs])*[rc['M8'],rc['M9']]) for h,vs in pools.items()}
        used={'raw':set(),'common':set()};assigned=[];failed=[]
        active=[b for b in branches if b['proposed_relay_BUF']]
        # Most constrained source branches first, stable net/destination order.
        active.sort(key=lambda b:(0 if (b['net'],b['destination']) in cuts else 1,b['first_driver_total_wire_budget_fF']/2/b['source_fanout'],b['net'],b['destination']))
        # Exact maximum-cardinality one-to-one matching over every literal-pin
        # legal candidate in the bounded neighbourhood, not greedy site stealing.
        allsites=rawsites+common;offset={'raw':0,'common':len(rawsites)}
        edges=[];indptr=[0];values=[]
        for branch in active:
            n=nets[branch['net']];budget=branch['first_driver_total_wire_budget_fF']/2/branch['source_fanout'];sx,sy=n['source']['point_DBU'];opts=[]
            homes=['common'] if (branch['net'],branch['destination']) in cuts else ['raw','common']
            for h in homes:
                # All source Y and BUF A shapes lie within 378DBU x270DBU
                # of the point. The triangle bound includes every legal shape.
                radius=budget*1000+2*(378*rc['M8']+270*rc['M9'])
                indices=trees[h].query_ball_point([sx*rc['M8'],sy*rc['M9']],radius,p=1)
                for j in indices:
                    v=pools[h][j];ax=v['bbox_DBU'][0]+27;ay=v['bbox_DBU'][1]+135
                    cap=(abs(sx-ax)*rc['M8']+abs(sy-ay)*rc['M9'])/1000
                    if cap<=budget+1e-12:opts.append((0 if h=='raw' else 1,cap,offset[h]+j))
            for _,cap,j in sorted(opts):edges.append(j);values.append(1)
            indptr.append(len(edges))
        graph=csr_matrix((np.array(values,dtype=np.int8),np.array(edges),np.array(indptr)),shape=(len(active),len(allsites)))
        matched=maximum_bipartite_matching(graph,perm_type='column')
        for i,j in enumerate(matched):
            branch=active[i];n=nets[branch['net']];budget=branch['first_driver_total_wire_budget_fF']/2/branch['source_fanout']
            if j<0:
                failed.append({'net':branch['net'],'destination':branch['destination'],'metal_budget_fF':budget,'legal_site_candidates':indptr[i+1]-indptr[i],'reason':'Unmatched in maximum-cardinality literal-pin site graph; full route architecture not judged'});continue
            site=allsites[int(j)];h=site['home'];local=int(j)-offset[h];used[h].add(local);cap=access(n['source']['literal_rectangles'],site,apins,rc)
            assigned.append(dict(site,branch_net=branch['net'],branch_destination=branch['destination'],role='first_relay',source_instance=branch['source'],sink_pin=branch['sink_pin'],source_pin_rectangles=n['source']['literal_rectangles'],native_sink=next(v for v in n['sinks'] if v['instance']==branch['destination']),first_branch_metal_budget_fF=budget,optimistic_literal_pin_metal_C_fF=cap,constructed_M8_M9_center_route_metal_C_fF=(abs(n['source']['point_DBU'][0]-(site['bbox_DBU'][0]+27))*rc['M8']+abs(n['source']['point_DBU'][1]-(site['bbox_DBU'][1]+135))*rc['M9'])/1000,via_and_escape_C_reserved_not_proven=True))
        total=old['raw_empty_row_correction_site_inventories'][s]['requested_sites'];remaining=total-len(assigned)
        # Fill the remaining fixed inventory across ALL rows, interleaved x.
        free=[(j,v) for j,v in enumerate(rawsites) if j not in used['raw']]
        rows={}
        for j,v in free:rows.setdefault(v['bbox_DBU'][1],[]).append((j,v))
        level=0
        while remaining:
            progressed=False
            for y,vs in sorted(rows.items()):
                if level<len(vs) and remaining:
                    j,v=vs[level];assigned.append(dict(v,role='downstream_relay_or_equal_depth_pad',actual_branch_assignment=None));remaining-=1;progressed=True
            if not progressed:raise ValueError('fixed inventory site deficit')
            level+=1
        escape_records=[]
        source_by_name={v['instance']:v for v in cells}
        for n in nets.values():escape_records.append(local_escape(source_by_name[n['source']['instance']],'Y',grid,lef))
        for site in assigned:
            for pin in ('A','Y'):escape_records.append(local_escape(site,pin,grid,lef))
        # Actual native sink pin rectangles, not centre-of-region stand-ins.
        sink_seen=set();sink_records=[]
        for n in nets.values():
            for sink in n['sinks']:
                key=(sink['instance'],sink['pin'])
                if key in sink_seen:continue
                sink_seen.add(key);choices=[r['bbox_DBU'] for r in sink['literal_rectangles'] if r['bbox_DBU'][2]-r['bbox_DBU'][0]>=18 and r['bbox_DBU'][3]-r['bbox_DBU'][1]>=22]
                if not choices:raise ValueError('Native CLK VIA12 landing missing')
                rect=choices[0];x=math.floor((rect[0]+rect[2])/2);y=math.floor((rect[1]+rect[3])/2);net=n['name'];shapes=via(grid,'VIA12',x,y,net)
                phase,pitch=m3_phase(grid);vx=phase+math.floor((x-phase)/pitch+.5)*pitch
                shapes+=via(grid,'VIA23',vx,y,net);lo=min(x-14,vx-14);hi=max(x+14,vx+14)
                if hi-lo<38:lo-=5;hi+=5
                shapes.append(dict(net=net,layer='M2',bbox_DBU=[lo,y-9,hi,y+9]))
                sink_records.append(dict(instance=key[0],pin=key[1],literal_pin_rect_DBU=rect,shapes=shapes,global_OBS_or_other_net_spacing_proven=False))
        common_sites=[v for v in assigned if v['home']=='common'];extensions=[]
        for y in sorted({v['bbox_DBU'][1] for v in common_sites}):
            end=max(v['bbox_DBU'][2] for v in common_sites if v['bbox_DBU'][1]==y)
            for name,cy in [('VDD',y),('VSS',y+270)]:
                source=next(r for r in raw['PG_M1_literal_rails'] if r['net']==name and (r['bbox_DBU'][1]+r['bbox_DBU'][3])/2==cy)
                extensions.append(dict(net=name,layer='M1',bbox_DBU=[source['bbox_DBU'][2]-18,cy-9,end+18,cy+9],role='proposed_common_same_net_rail_extension',current_or_OBS_qualified=False))
        feeds=pg_feed(f'raw_shard{s}',raw['raw_slot_bbox_DBU'],raw['PG_M1_literal_rails'],grid,raw['raw_slot_bbox_DBU'][0]-4320)
        for name,obj in [('buffer_native_escapes',escape_records),('native_sink_escapes',sink_records),('PG_upfeed',dict(raw_feed=feeds,common_rail_extensions=extensions,source_current_capacity_unknown=True))]:
            (outdir/f'shard{s}_{name}.json.gz').write_bytes(gzip.compress((json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
        first=[v for v in assigned if v['role']=='first_relay'];outside=[v for v in first if v['home']=='common'];rawchosen=[v for v in assigned if v['home']=='raw']
        # Literal same-net supply coverage for raw sites. Common uses explicitly
        # proposed extensions; it is not a retained PG qualification.
        rails=raw['PG_M1_literal_rails'];supplies=E.shapes(lef,'VDD')+E.shapes(lef,'VSS')
        for v in rawchosen:
            for pin in ('VDD','VSS'):
                for pr in E.shapes(lef,pin):
                    r=E.transform(pr,v)
                    if not any(t['net']==pin and t['bbox_DBU'][0]<=r[0] and t['bbox_DBU'][1]<=r[1] and t['bbox_DBU'][2]>=r[2] and t['bbox_DBU'][3]>=r[3] for t in rails):raise ValueError('raw PG coverage')
        blob=gzip.compress((json.dumps(assigned,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0);name=f'shard{s}_sites.json.gz';(outdir/name).write_bytes(blob)
        cases[str(s)]=dict(buffer_native_escape_ports=len(escape_records),native_sink_escape_ports=len(sink_records),common_rail_extensions=len(extensions),actual_global_OBS_PG_via_spacing_proven=False,total_fixed_buffers=total,first_relay_assigned=len(first),first_relay_failed=len(failed),failures=failed,outside_raw_first_relays=len(outside),expected_outside_raw_minimum=len(cuts),outside_raw_body_um2=len(outside)*.10206,raw_buffers=len(rawchosen),raw_rows_used=len({v['bbox_DBU'][1] for v in rawchosen}),raw_rows_available=len(rows),site_file=name,site_sha256=sha(outdir/name),unique_sites=len({v['proposed_site_ID'] for v in assigned}),source_cells_untouched=True,raw_supply_literal_covered=True,common_owner_must_reserve_relocated_sites=True,common_M1_rail_extensions_and_via_upfeeds_required=True,downstream_relay_and_pad_branch_assignment_complete=False)
    result=dict(schema='DS_FIXED_GRAPH_CLOCK_FIRST_HOP_REALLOCATION_V1',candidate=old['candidate'],arch_rejection_origins=origins,escape_helpers_origin=json.loads((BASE/'inputs/escape_function_origin.json').read_text()),selected_bank=old['selected_selector_clock_construction'],annex_charge_mm2=0,additional_buffers=0,source_graph_changed=False,shards=cases,old_bd872_rejection_preserved=True,first_hop_pass_scope='Unique source-to-first-relay M8-horizontal/M9-vertical centre-line metal cap under halfwire/k budget; contact/stub half remains reserved but unqualified. No full branch path or skew proof.',first_hop_geometry_pass=all(v['first_relay_failed']==0 and v['outside_raw_first_relays']>=v['expected_outside_raw_minimum'] for v in cases.values()),native_sink_refs_in_each_assigned_branch=True,escape_provider='db47c807 literal M1/VIA12/M2/VIA23/M3 constructions; relocated sites require regeneration and global collision checks',PG_provider='Retained raw M1 rails; common relocated sites need named same-net extensions and finite-current upfeed',equal_depth_or_optimistic_pin_C_is_not_skew_slew_or_SSFF=True,added_cycles=None,single_user_latency_qualified=False,physical_fit=False,contextual_PR_admitted=False,remaining_gate='Assign every downstream relay/pad on its fixed branch, construct native sink escapes/common PG and check loaded source clock/reset SS/FF; first-hop allocation alone does not admit P&R',new_jobs=[])
    (outdir/'model.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=BASE);a=p.parse_args();m=build(a.out);print(json.dumps({'first_hop_geometry_pass':m['first_hop_geometry_pass'],'shards':{s:{k:v[k] for k in ('first_relay_assigned','first_relay_failed','outside_raw_first_relays','raw_rows_used','total_fixed_buffers')} for s,v in m['shards'].items()}},indent=2))
