"""Read-only finite inventory and geometry model; no physical implementation."""
import collections, csv, gzip, hashlib, json, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent / 'hbm_bw_native_model_1019'
OUT = HERE
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
summary = json.loads((BASE / 'summary.json').read_text())
macros = json.loads((BASE / 'macros.json').read_text())
with gzip.open(BASE / 'raw_cells.tsv.gz', 'rt') as f:
    cells = {r['inst']: r for r in csv.DictReader(f, delimiter='\t')}
with gzip.open(BASE / 'raw_pins.tsv.gz', 'rt') as f:
    pins = list(csv.DictReader(f, delimiter='\t'))
area = summary['master_area_um2']
role_area = collections.Counter()
for c in cells.values(): role_area[c['role']] += area[c['master']]
pg = [r for r in pins if r['master'] != 'PORT' and r['pin'].rsplit('/',1)[-1] in ('VDD','VSS')]
unbound = [r['pin'] for r in pg if not r['net']]
ports = [r for r in pins if r['master'] == 'PORT']
clock_cells = {r['pin'].rsplit('/',1)[0] for r in pins if r['net_type']=='CLOCK' and r['master']!='PORT'}
clock_comb = [cells[n] for n in clock_cells if cells[n]['role']=='comb']

# Preserve every native MTerm and exact offset, with distinct proposed contacts.
contacts=[]; placements=[]; faces={}
for j,m in enumerate(macros):
    col=j%6; row=j//6
    x=43.2*(col+1); y=[43.2,86.4,216.,259.2][row]
    placements.append({'inst':m['inst'],'origin_um':[x,y], 'outline_um':[33.72,27.576], 'orientation':'R0', 'owner_strip_x_um':[x-9.48,x+33.72]})
    side_records=collections.defaultdict(list)
    for q in m['pins']:
        if q['direction']=='INOUT':continue
        dx=q['xy'][0]-m['bbox'][0];dy=q['xy'][1]-m['bbox'][1]
        side='W' if dx<16.86 else 'E'
        side_records[side].append((dy,q,dx))
    for side,items in side_records.items():
        items.sort(key=lambda a:a[0]); vs=[z[0] for z in items]
        faces[f'{j}/{side}']={'contacts':len(vs),'span_um':[min(vs),max(vs)],'whole_face_density':len(vs)/27.576,'occupied_span_density':len(vs)/(max(vs)-min(vs)), 'min_pitch_um':min(b-a for a,b in zip(vs,vs[1:])), 'max_contacts_in_10um':max(sum(a<=b<a+10 for b in vs) for a in vs)}
        for k,(dy,q,dx) in enumerate(items):
            # Proposed new family only; immutable old LEF and libs are untouched.
            py=.780+.192*k
            native=[x+dx,y+dy]; proposed=[x+dx,y+py]
            landing=[x+16.86,129.735 if y<129.6 else 194.265]
            contacts.append({'inst':m['inst'],'pin':q['pin'].rsplit('/',1)[-1],'direction':q['direction'],'net':q['net'],'side':side,'native_offset_um':[dx,dy],'translated_native_um':native,'proposed_new_family_um':proposed,'proposed_landing_reservation_um':landing,'native_contact_to_reservation_l1_um':sum(abs(a-b) for a,b in zip(native,landing)), 'proposed_contact_to_reservation_l1_um':sum(abs(a-b) for a,b in zip(proposed,landing)), 'binding_status':'UNBOUND reservation: no named RTL FF'} )

# Raw native first/last contacts, folding only real transparent masters.
drivers=collections.defaultdict(list); sinks=collections.defaultdict(list); instpins=collections.defaultdict(list)
for p in pins:
    if p['master']=='PORT' or not p['net']:continue
    instpins[p['pin'].rsplit('/',1)[0]].append(p)
    if p['direction']=='OUTPUT':drivers[p['net']].append(p)
    if p['direction']=='INPUT':sinks[p['net']].append(p)
def transparent(p):return p['master'].startswith(('BUF','INV','HB2','HB4'))
def trace(net, forward, seen=None):
    seen=set() if seen is None else seen
    if net in seen:return []
    seen.add(net); ans=[]
    for q in (sinks if forward else drivers)[net]:
        if not transparent(q):ans.append(q);continue
        for z in instpins[q['pin'].rsplit('/',1)[0]]:
            if z['direction']==('OUTPUT' if forward else 'INPUT') and z['net']:
                ans.extend(trace(z['net'],forward,seen))
    return list({q['pin']:q for q in ans}.values())
boundary=[]
for p in ports:
    if p['direction']=='INOUT' or p['net_type']=='CLOCK':continue
    ends=trace(p['net'],p['direction']=='INPUT')
    boundary.append({'port':p['pin'],'direction':p['direction'],'native_contacts':[{'pin':q['pin'],'master':q['master']} for q in ends], 'non_FF_contact_count':sum('DFF' not in q['master'] for q in ends)})
badboundary=[r for r in boundary if r['non_FF_contact_count'] or not r['native_contacts']]

lef=(BASE/'family/ot_sram_1r1w2c_128x64_m1.lef').read_text()
straps={}
for supply in ('VDD','VSS'):
    block=lef.split('  PIN '+supply+'\n')[1].split('  END '+supply)[0]
    straps[supply]=[list(map(float,m)) for m in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',block)]
std=sum(v for k,v in role_area.items() if k!='macro')
band=345.6*64.8; floor=698.32368
result={'status':'MODEL_ONLY_BLOCKED_BEFORE_SOURCE', 'inputs':{n:sha(BASE/n) for n in ('summary.json','macros.json','raw_cells.tsv.gz','raw_pins.tsv.gz','family/ot_sram_1r1w2c_128x64_m1.lef')},'native_std_area_by_role_um2':dict(role_area),'native_std_area_all_um2':std,'native_clock_comb_count':len(clock_comb),'native_clock_comb_area_um2':sum(area[c['master']] for c in clock_comb),'pg':{'required_native_iterms':len(pg),'bound_at_4_cts':len(pg)-len(unbound),'unbound_at_4_cts':len(unbound),'unbound_examples':unbound[:12],'macro_supply_rectangles_per_macro':{k:len(v) for k,v in straps.items()},'macro_supply_rectangles_total':23*sum(map(len,straps.values())),'candidate_existing_plus_2375_ff_required_iterms_floor':len(pg)+2375*2,'candidate_final_contact_connectivity':'UNPROVEN; CTS snapshot is not final PG'},'geometry':{'outline_um':[345.6,345.6],'aspect':1,'band_um':[0,129.6,345.6,194.4],'band_area_um2':band,'baseline_plus_known_floor_um2':std+floor,'baseline_plus_known_floor_band_util':(std+floor)/band,'extra_area_until_60pct_um2':band*.6-std-floor,'existing_helper_area_is_escrow_not_reusable_tree':True,'minimum_between_macro_edges_x_um':9.48,'minimum_between_macro_edges_y_um':15.624,'macro_count':23,'macro_area_um2':23*929.86272,'macroface_pitch_native_um':.096,'macroface_pitch_proposed_new_family_um':.192,'proposed_span_um':19.968,'proposed_occupied_density':105/19.968,'max_native_contact_to_reservation_um':max(c['native_contact_to_reservation_l1_um'] for c in contacts),'max_new_contact_to_reservation_um':max(c['proposed_contact_to_reservation_l1_um'] for c in contacts),'boundary_collar':'2.7um outer connected collar reservation; local pin-bound occupancy and exact FF ownership OPEN'},'native_boundary':{'signal_ports':len(boundary),'inputs':sum(r['direction']=='INPUT' for r in boundary),'outputs':sum(r['direction']=='OUTPUT' for r in boundary),'non_FF_or_missing_port_count':len(badboundary),'non_FF_or_missing_ports':badboundary},'clock':{'source':'only native PORT/clk; no other domain','root_reservation_um':[172.8,172.8],'baseline_ff_sinks':9383,'new_ff_known_floor':2375,'macro_clock_contacts':46,'candidate_sink_floor':9383+2375+46,'macro_TT_cap_fF':429.9068,'macro_FF_cap_fF':477.1672,'new_FF_corner_cap_and_tree_area':None,'new_macro_clock_location':'actual wclk/rclk translated from native MTerms; proposal changes rclk by .096um','boundary_phase_root_to_native_capture_reference':None,'TT_FF_spread_and_setup_hold':None},'unpriced':['source-specific named landing owners and all nonmacro crossings','new mux/collision/ring-pointer controls native cells','reset new bookkeeping and collar contacts + parent fixed point','boundary first/last FF moves, semantics and exact local placement','new family port-lead and internal RC versus macro functionality and PG/OBS','clock source phase/root delivery and all sink cell caps/tree','parent footprint/crossing/PG supply and compiler calendars']}
result['new_boundary_floor']={'output_ff':279,'k_v_input_ff':1,'additional_ff':280,'additional_ordinary_ff_area_um2':81.648,'cost_is_floor_excluding_new_control_reset_valid_and_clock':True,'extra_observation_calendar':None}
result['geometry']['including_boundary_floor_band_util']=(std+floor+81.648)/band
result['geometry']['including_boundary_floor_extra_area_until_60pct_um2']=band*.6-std-floor-81.648
result['clock']['candidate_sink_with_boundary_ff_floor']=9383+2375+280+46
result['pg']['candidate_with_boundary_ff_required_iterms_floor']=len(pg)+(2375+280)*2
for name,obj in [('model.json',result),('macro_contacts.json',contacts),('placements.json',placements),('native_faces.json',faces),('boundary_bindings.json',boundary),('native_pg_straps.json',straps)]:
    (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({'std_area':std,'band_util':result['geometry']['baseline_plus_known_floor_band_util'],'headroom':result['geometry']['extra_area_until_60pct_um2'],'pg_required':len(pg),'pg_unbound_at_CTS':len(unbound),'boundary_bad_count':len(badboundary)},indent=2))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,10))
ax.add_patch(Rectangle((0,129.6),345.6,64.8,facecolor='#bee8c5',edgecolor='green',label='Full-width std band: 48.1% known reserve'))
for p in placements:
    x,y=p['origin_um'];ax.add_patch(Rectangle((x,y),33.72,27.576,facecolor='#bacde8',edgecolor='navy'))
    idx=placements.index(p);ax.text(x+16.86,y+14,str(idx),ha='center',va='center',fontsize=9)
    ax.plot([x,x],[y+.78,y+20.748],color='orange',linewidth=2)
    ax.plot([x+33.72,x+33.72],[y+.78,y+20.748],color='orange',linewidth=2)
for xy,wh in [((0,0),(345.6,2.7)),((0,342.9),(345.6,2.7)),((0,0),(2.7,345.6)),((342.9,0),(2.7,345.6))]:
    ax.add_patch(Rectangle(xy,*wh,facecolor='#e3b7ce',edgecolor='purple'))
ax.plot(172.8,172.8,'r*',ms=16,label='Clock root reservation; phase/tree OPEN')
ax.set(xlim=(0,345.6),ylim=(0,345.6),xlabel='um',ylabel='um',title='BW geometry MODEL — not placed or qualified\nOrange: proposed distinct .192um contacts; native .096um family HOLD')
ax.set_aspect('equal');ax.legend(loc='upper left',fontsize=8);fig.tight_layout();fig.savefig(OUT/'candidate.png',dpi=160)
