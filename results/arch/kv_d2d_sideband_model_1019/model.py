"""Read-only, bounded source/lib/geometry arithmetic. No hardware simulation or EDA."""
import collections, gzip, hashlib, json, math, re
from pathlib import Path
P = Path(__file__).parent
I = P / 'input'
def read(name):
    p = I / name
    if not p.exists():p=I/(name+'.gz')
    return gzip.open(p, 'rt').read() if p.name.endswith('.gz') else p.read_text()
def blocks(s, kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(([^)]+)\)\s*\{', s):
        d, e = 1, m.end()
        while d:
            d += (s[e] == '{') - (s[e] == '}'); e += 1
        yield m.group(1).strip('"'), s[m.end():e-1]
def scalar(b, key):
    m = re.search(r'\b'+key+r'\s*:\s*([\d.eE+-]+)', b)
    return float(m.group(1)) if m else None
def table(b):
    def nums(s): return list(map(float, re.findall(r'[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?',s)))
    x = nums(re.search(r'index_1\s*\((.*?)\);',b,re.S).group(1))
    y = nums(re.search(r'index_2\s*\((.*?)\);',b,re.S).group(1))
    v = nums(re.search(r'values\s*\((.*?)\);',b,re.S).group(1))
    assert len(v) == len(x)*len(y)
    return x,y,[v[k:k+len(y)] for k in range(0,len(v),len(y))]
def lookup(t, x, y):
    xs,ys,z=t
    # Clamp only inside characterized edge bins; all assumptions are emitted.
    x=max(xs[0],min(xs[-1],x));y=max(ys[0],min(ys[-1],y))
    ix=min(len(xs)-2,next((k for k in range(len(xs)-1) if x<=xs[k+1]),len(xs)-2))
    iy=min(len(ys)-2,next((k for k in range(len(ys)-1) if y<=ys[k+1]),len(ys)-2))
    a=(x-xs[ix])/(xs[ix+1]-xs[ix]);b=(y-ys[iy])/(ys[iy+1]-ys[iy])
    return (1-a)*((1-b)*z[ix][iy]+b*z[ix][iy+1])+a*((1-b)*z[ix+1][iy]+b*z[ix+1][iy+1])
names = ['DFFHQNx1_ASAP7_75t_R','OR4x1_ASAP7_75t_R','OR3x1_ASAP7_75t_R','OR2x2_ASAP7_75t_R','INVx1_ASAP7_75t_R']
libs={}
for corner in ['TT','FF']:
    seq=read('asap7sc7p5t_SEQ_RVT_'+corner+'_nldm_220123.lib.gz')
    simple=read('asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz' if corner=='TT' else 'simple_ff.lib.gz')
    inv=read('asap7sc7p5t_INVBUF_RVT_'+corner+'_nldm_220122.lib.gz')
    cells=dict(blocks(seq+'\n'+simple+'\n'+inv,'cell')); libs[corner]={}
    for name in names:
        b=cells[name]; pins={n:scalar(p,'capacitance') for n,p in blocks(b,'pin') if scalar(p,'capacitance') is not None}
        arcs={k:[table(v) for _,v in blocks(b,k)] for k in ['cell_rise','cell_fall','rise_transition','fall_transition']}
        libs[corner][name]=dict(area_um2=scalar(b,'area'),input_cap_ff=pins,arcs=arcs)

ff=names[0];o4,o3,o2=names[1:4];inv=names[4]
counts={o4:171,o3:2,o2:16} # 179 producer + 10 receiver gates
comb=sum(libs['TT'][n]['area_um2']*v for n,v in counts.items())
# Exact disjoint input sets prove the two transported options reconstruct the same OR expressions.
cmd=[set(range(19,32))]+[set(range(32*z,32*z+32)) for z in range(1,16)]
status=[set(range(5,32))]+cmd[1:]
assert set.union(*cmd)==set(range(19,512))
assert set.union(*status)==set(range(5,512))
assert all(cmd[z]==status[z] for z in range(1,16))
options={}
for bits in [32,17]:
    nff=13*bits
    options[str(bits)]=dict(bits=bits,producer_ff=bits,relay_hops=11,relay_ff=11*bits,receiver_ff=bits,
        ff=nff,resettable_ff=0,reset_set_cap_ff=0,
        added_edges=0,producer_gates={o4:161,o3:2,o2:16},receiver_gates={o4:10},
        positive_capture_inv=nff,
        positive_capture_inv_area_um2=nff*libs['TT'][inv]['area_um2'],
        positive_capture_inv_input_cap_ff={c:nff*sum(libs[c][inv]['input_cap_ff'].values()) for c in libs},
        stdcell_area_um2=nff*(libs['TT'][ff]['area_um2']+libs['TT'][inv]['area_um2'])+comb,
        ff_area_um2=nff*libs['TT'][ff]['area_um2'],comb_area_um2=comb,
        clock_cap_ff={c:nff*libs[c][ff]['input_cap_ff']['CLK'] for c in libs},
        ff_d_cap_ff={c:nff*libs[c][ff]['input_cap_ff']['D'] for c in libs},
        comb_input_cap_ff={c:sum(v*sum(libs[c][n]['input_cap_ff'].values()) for n,v in counts.items()) for c in libs},
        max_new_nonclock_logical_loads=2,
        edge_bus_bits=548+bits,incremental_bus_fraction=bits/548,
        external_signal_contacts=24*bits, # 12 segments, both endpoint faces
        dedicated_face_length_min_um=bits/6,
        metal67_incremental_track_width_um=bits*.064,
        metal45_incremental_track_width_um=bits*.048,
        proposed_separate_relay_frame_um=[12.96,12.96],
        proposed_relay_face_signal_density_per_um=bits/12.96,
        proposed_relay_bbox_area_um2=11*12.96**2,
        native_total_area_um2=None,clock_tree_area_um2=None,wire_cap_ff=None,dynamic_power_mw=None)

# Conditional, wire-free combinational estimates at explicit 20 ps starting slew.
# Three OR4 levels conservatively cover every producer reduction. The final load is
# two kept D inputs for the 32-bit option, one for the 17-bit option.
cell_est={}
for corner in libs:
    c=libs[corner][o4]; cap=max(c['input_cap_ff'].values()); fd=libs[corner][inv]['input_cap_ff']['A']
    cell_est[corner]={}
    for bits in [32,17]:
        slew=20.;delay=0.;stages=[]
        for load in [cap,cap,fd*(2 if bits==32 else 1)]:
            d=max(lookup(t,slew,load) for k in ['cell_rise','cell_fall'] for t in c['arcs'][k]);
            ns=max(lookup(t,slew,load) for k in ['rise_transition','fall_transition'] for t in c['arcs'][k]);
            stages.append(dict(input_slew_ps=slew,load_ff=load,delay_ps=d,output_slew_ps=ns));delay+=d;slew=ns
        cell_est[corner][str(bits)]=dict(producer_three_or4_ps=delay,stages=stages)

die=read('gen8_die.v.gz');lines=[x for x in die.splitlines() if (' d2d_kv (' in x or ' kvs_attn (' in x or ('qkd_rlys_' in x and ('rly_ks_d2d_kv__rx_payload_' in x or 'rly_pinfix_ks_d2d_kv_rx_payload_' in x)))]
assert len(lines)==24, len(lines)
assert sum('qkd_rlys_528' in x for x in lines)==11
assert all('.ck(n_clk_core_c)' in x for x in lines if 'qkd_rlys_' in x)
path=dict(captured_die_sha256=hashlib.sha256(die.encode()).hexdigest(),producer_master='qkd_d2ds',
          producer_binding=json.loads(read('gen8_d2ds_view.json')),actual_payload_relay_hops=11,
          source_to_receiver_landing_captures=13,clock_net='n_clk_core_c',lines=lines,
          accounting='10 planned route hops plus 1 pinfix; calendar error not established',
          first_use='Require matching payload/flag cohorts through all 13 captures before an authorized observation; actual reset/PLL/event guarantee open')
(P/'current_path.json').write_text(json.dumps(path,indent=2)+'\n')

old=json.loads(read('old_rx_root_loads.json'))
assert old['cells']==40694 and old['rx_roots']==548
roots=[x for x in old['rows'] if x['bit']<512]
for r in roots:
    r['new_leaf_loads']=int(r['bit']>=5)+int(19<=r['bit']<32)
    r['modeled_total_logical_loads']=r['logical_loads']+r['new_leaf_loads']
ancestry=dict(source_kind='historical mapped r7w only, not GEN8 native',roots=roots,
             root_max_before=max(x['logical_loads'] for x in roots),root_max_after=max(x['modeled_total_logical_loads'] for x in roots),
             new_cone_max=2,new_copy_fixedpoint=0,whole_d2d_source_unsafe_reset_roots_remain=True)
(P/'added_branch_ancestry.json').write_text(json.dumps(ancestry,indent=2)+'\n')

macro='ot_sram_1r1w_64x137_m1_r2c2_p192';lef=read(macro+'.lef');w,h=map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',lef).groups())
contacts=[];obs=lef[lef.index('  OBS'):];pg=[]
for b in lef.split('\n  PIN ')[1:]:
    pn=b.split()[0];b=b[:b.index('\n  END '+pn)]
    for layer,chunk in re.findall(r'LAYER\s+(\S+)\s*;(.*?)(?=LAYER|$)',b,re.S):
        for v in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;',chunk):
            x0,y0,x1,y1=map(float,v);x=(x0+x1)/2;y=(y0+y1)/2
            if pn in ['VDD','VSS']:pg.append(dict(pin=pn,layer=layer,rect=[x0,y0,x1,y1]));continue
            face=min({'W':x,'E':w-x,'S':y,'N':h-y},key={'W':x,'E':w-x,'S':y,'N':h-y}.get)
            contacts.append(dict(pin=pn,layer=layer,face=face,axis=y if face in 'WE' else x,rect=[x0,y0,x1,y1]))
faces={}
for face in 'WENS':
    a=sorted(x['axis'] for x in contacts if x['face']==face);length=h if face in 'WE' else w
    gaps=[b-a for a,b in zip(a,a[1:])]
    faces[face]=dict(contacts=len(a),length_um=length,average_per_um=len(a)/length,min_centroid_gap_um=min(gaps) if gaps else None,
                     worst_one_um_window=max((sum(y>=x and y<x+1 for y in a) for x in a),default=0))
storage=dict(candidate_source_commit='99cbdd49d',candidate=macro,banks=4,words_per_bank=64,useful_width_per_bank=137,
             useful_bits=4*64*137,old_physical_bits=4*64*512,read_bits_per_edge=548,write_bits_per_edge=548,
             read_bytes_per_edge=68.5,write_bytes_per_edge=68.5,macro_width_um=w,macro_height_um=h,
             macro_area_um2=4*w*h,signal_contacts=len(contacts),faces=faces,pg_abstract_contacts=len(pg),
             clocks='one shared logical ck, one clk pin per bank; NOT dual-clock CDC',
             collision='same posedge synchronous read-before-write OLD plus existing age0/age1 forwarding; preserve both',
             initialization='no reset; OT_MEM_NO_INIT arbitrary-memory proof required',
             historical_source_ff_per_bank=137*3+6+3,current_sf_ff_per_bank=137*3+6+1+3*9,
             current_sf_ff_all_banks=4*(137*3+6+1+3*9),
             occupancy='64 publication identities; immediate scheduled read, no credits, no variable replay; preserve slot/read collision checks',
             proposed_lattice_origins_um=[[43.2,43.2],[172.8,43.2],[43.2,129.6],[172.8,129.6]],
             proposed_macro_array_bbox_um=[43.2,43.2,230.712,175.272],
             pg_actual_contact_via_connectivity=None,obstruction_escape=None,same_age_native_timing=None,
             qualification='analytical candidate only; no old native view or Qwen gate transferred')
(P/'macro_contacts.json').write_text(json.dumps(dict(contacts=contacts,pg=pg,faces=faces),indent=2)+'\n')
result=dict(verdict='MODEL_HOLD_BEFORE_RTL_BUILD',options=options,cell_only_estimate=cell_est,storage=storage,
            library_cells={co:{n:{k:v for k,v in c.items() if k!='arcs'} for n,c in cs.items()} for co,cs in libs.items()},
            source_branch_fixedpoint=dict(max_root_before=ancestry['root_max_before'],max_root_after=ancestry['root_max_after'],new_copies=0),
            limits=['No current GEN8 native binding','Actual first-use/reset/PLL authority open','No complete receiver timing proof',
                    'No source physical PG/access/clock/spread receipt','Conditional cell estimates omit launch CQ, old loads and all wire RC',
                    'Existing payload relay528 face density 528/82.08 exceeds6; separate physical redesign required'])
(P/'model.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(options=options,cell_only_estimate=cell_est,storage=storage),indent=2))
