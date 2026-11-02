from pathlib import Path
import sys,json,hashlib,copy
R=Path('/srv/opentallas-scratch2/claude/codex-flow-t49-0345');S=Path('/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055/src');sys.path.insert(0,str(S/'tools/die_plan'))
import schema,taps,reset_tree as RT
p=S/'physical/die_plan/s81/plan_source39_clockset_final.json';raw=json.load(open(p));new=copy.deepcopy(raw);tn='slice_station__t49';ck=new['partition_types'][tn]['clock'];assert ck['tap_radius_um']==150 and ck['tap_max_sinks']==1500
node=next(x for x in ck['taps'] if x['name']=='clk_t25');assert node['xy']==[400.1757,307.2182];node['xy']=[400.656,307.712]
A=schema.Plan(raw,p);B=schema.Plan(new,p)
a=taps.explicit_tap_sites(A,tn);b=taps.explicit_tap_sites(B,tn);sa=taps.sink_sites(A,tn);sb=taps.sink_sites(B,tn);assert sa==sb
la,fa,aa=taps.assign(a,sa,1500,150,max_distance_um=150);lb,fb,ab=taps.assign(b,sb,1500,150,max_distance_um=150)
assert la[25]==936 and abs(fa[25]-150.9631)<1e-6
native=taps.explicit_taps(B,tn);assert len(native)==69
old=RT.for_type(A,tn);fresh=RT.for_type(B,tn)
for n,x in [('old_reset',old),('new_reset',fresh),('plan_candidate',new)]: (R/(n+'.json')).write_text(json.dumps(x,indent=1)+'\n')
oldrtl='\n'.join(RT.rtl_lines(old));newrtl='\n'.join(RT.rtl_lines(fresh))
rec=dict(source='39f754dda07e9746c4850ea0814d48d134a6cf2a',input_plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),type=tn,tap='clk_t25',old_xy=a[25][1:],new_xy=b[25][1:],old_load=la[25],new_load=lb[25],old_radius=fa[25],new_radius=fb[25],radius_limit=150,all69_taps_pass=True,membership_changes=sum(x!=y for x,y in zip(aa,ab)),sink_count=len(sa),reset_graph_coords_byte_identical=old==fresh,emitted_reset_rtl_byte_identical=oldrtl==newrtl,old_relays=len(old['relays']),new_relays=len(fresh['relays']),old_outputs=len(old['outs']),new_outputs=len(fresh['outs']),old_depth=old['depth'],new_depth=fresh['depth'],source_only=True,physical_hold=True)
(R/'REPAIR.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec),flush=True)
assert old==fresh and oldrtl==newrtl,'reset changed: need native reset delta proof before BIND'
