import json, re, sys, math
from pathlib import Path

root = Path('/srv/opentallas-scratch2/claude/codex-vms-last1-1106')
out = root / 'via_guard_candidate'
out.mkdir(exist_ok=True)
base = root / 'kit/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base'
text = (base / '6_final.def').read_text()
inst = 'u_fcore.u_core.u_ot_pr_core.bank.u_a'
placed = re.search(r'- '+re.escape(inst)+r' (\S+) \+ FIXED \( (\d+) (\d+) \) (\w+) ;', text)
master, ox, oy, orient = placed.groups()
assert orient == 'N', 'This measured guard is scoped to the actual N-oriented bank A'
ox, oy = int(ox)/1000, int(oy)/1000
lef = (root/'kit/macros'/f'{master}.lef').read_text()
width, height = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', lef).groups())
obs = re.search(r'\n  OBS\n(.*?)\n  END', lef, re.S).group(1)
m4obs = tuple(map(float, re.search(r'LAYER M4 ;\s*RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', obs).groups()))
signal_ports=[]
for body in re.split(r'\n  PIN ', lef)[1:]:
    body=body.split('\n  END ')[0]
    if not re.search(r'USE (SIGNAL|CLOCK)',body): continue
    assert set(re.findall(r'LAYER (\w+)',body)) == {'M4'}
    signal_ports.extend(tuple(map(float,a)) for a in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body))
west_ports=[a for a in signal_ports if a[0]==0]
pin_right=ox+max(a[2] for a in west_ports)
tech=(out/'actual_tech.lef').read_text()
rules={n:re.search(r'^LAYER '+n+r'\n(.*?)^END '+n,tech,re.M|re.S).group(1) for n in ('M4','M5')}
minw=float(re.search(r'\n WIDTH ([\d.]+)',rules['M5']).group(1))
spacing=float(re.search(r'\n SPACING ([\d.]+)',rules['M5']).group(1))
table=re.findall(r'\n WIDTH ([\d.]+) ([\d.]+)',rules['M4'].split('SPACINGTABLE')[1])
wide_threshold,wide_spacing=map(float,table[-1])
assert minw < wide_threshold and abs(spacing-.024)<1e-9
tracks=(root/'kit/make_tracks.tcl').read_text()
ndrs=re.search(r'^NONDEFAULTRULES (\d+) ;(.*?)^END NONDEFAULTRULES',text,re.M|re.S)
assert int(ndrs.group(1))==1
assert re.search(r'LAYER M5 WIDTH 24 SPACING 48',ndrs.group(2))
offset,pitch=map(float,re.search(r'make_tracks M5 -x_offset ([\d.]+) -x_pitch ([\d.]+)',tracks).groups())
via=re.search(r'^VIA VIA45 Default\n(.*?)^END VIA45',tech,re.M|re.S).group(1)
via_m4=tuple(map(float,re.search(r'LAYER M4 ;\s*RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',via).groups()))
via_m5=tuple(map(float,re.search(r'LAYER M5 ;\s*RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',via).groups()))
bad=offset+math.floor((pin_right-offset+1e-10)/pitch)*pitch
good=bad-pitch
obswest=ox+m4obs[0]
region=tuple(round(a,6) for a in (obswest-minw,oy-minw,obswest,oy+height+minw))
gaps={'bad_M4_to_OBS':obswest-(bad+via_m4[2]),'good_M4_to_OBS':obswest-(good+via_m4[2]),
      'bad_M5_to_guard':region[0]-(bad+via_m5[2]),'good_M5_to_guard':region[0]-(good+via_m5[2])}
assert gaps['bad_M4_to_OBS']<wide_spacing<=gaps['good_M4_to_OBS']+1e-9
assert gaps['bad_M5_to_guard']<spacing<=gaps['good_M5_to_guard']+1e-9

def touches(a, b, margin=0):
    return a[0] < b[2]+margin and a[2] > b[0]-margin and a[1] < b[3]+margin and a[3] > b[1]-margin

sys.path.insert(0, str(root / 'tools_bg/tools/die_plan'))
from clock_routed import parse_def_routes
names = (base / 'clk_freeze_nets.txt').read_text().splitlines()
clock = parse_def_routes(text, names)
clock_shapes = []
for name, items in clock.items():
    for a in items:
        if a[0] == 'VIA':
            if '5' not in a[1][3:5]:
                continue
            box = (a[2]-.060, a[3]-.060, a[2]+.060, a[3]+.060)
        else:
            if a[0] != 'M5':
                continue
            box = (min(a[1], a[3])-.060, min(a[2], a[4])-.060,
                   max(a[1], a[3])+.060, max(a[2], a[4])+.060)
        if touches(box, (47, 75, 48.5, 148)):
            clock_shapes.append({'net':name, 'box':box, 'route':a})
clock_hits = [a for a in clock_shapes if touches(a['box'], region)]

via_boxes = {}
via_section = re.search(r'^VIAS .*?^END VIAS', text, re.M|re.S).group()
for name, body in re.findall(r'- (\S+) (.*?);', via_section, re.S):
    boxes = re.findall(r'RECT M5 \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', body)
    if boxes:
        via_boxes[name] = [tuple(int(x)/1000 for x in a) for a in boxes]
special = re.search(r'^SPECIALNETS .*?^END SPECIALNETS', text, re.M|re.S).group()
pg = []
for line in special.splitlines():
    match = re.search(r'(?:NEW|\+ ROUTED) (M\d+) (\d+) .*?\( ([\d-]+) ([\d-]+)(?: [\d-]+)? \)(.*)', line)
    if not match:
        continue
    layer, width, x, y, tail = match.groups()
    x, y, half = int(x)/1000, int(y)/1000, int(width)/2000
    end = re.search(r'\( ([\d*-]+) ([\d*-]+)(?: [\d-]+)? \)', tail)
    if layer == 'M5' and end:
        ex, ey = end.groups()
        ex = x if ex == '*' else int(ex)/1000
        ey = y if ey == '*' else int(ey)/1000
        pg.append((min(x, ex)-half, min(y, ey)-half, max(x, ex)+half, max(y, ey)+half))
    for name in re.findall(r'\bVIA\w+', tail):
        if '5' in name[3:5]:
            if name not in via_boxes:
                raise RuntimeError('No exact M5 PG via box: '+name)
            pg.extend((x+a, y+b, x+c, y+d) for a,b,c,d in via_boxes[name])
# Exact per-shape screen: default and actual NDR M5 widths are 24nm; the
# clock NDR adds 48nm spacing. Patches and PG use their actual narrow dimension.
# Inflate at least40nm for the corner/EOL rule, a conservative rectangular screen.
tech_vias={}
for name,body in re.findall(r'^VIA (\S+)[^\n]*\n(.*?)^END \S+',tech,re.M|re.S):
    boxes=re.findall(r'LAYER M5 ;\s*RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',body)
    if boxes:tech_vias[name]=[tuple(map(float,a)) for a in boxes]
tech_vias.update(via_boxes)
def required(box,clock_net=False):
    narrow=min(box[2]-box[0],box[3]-box[1])
    table=.072 if narrow>=wide_threshold-1e-10 else spacing
    return max(table,.048 if clock_net else 0,.040)
actual_clock=[]
for name,items in clock.items():
    for a in items:
        if a[0]=='VIA':
            if '5' not in a[1][3:5]:continue
            assert a[1] in tech_vias,a
            boxes=[(a[2]+l,a[3]+b,a[2]+r,a[3]+t) for l,b,r,t in tech_vias[a[1]]]
        elif a[0]=='M5':
            boxes=[(min(a[1],a[3])-.012,min(a[2],a[4])-.012,max(a[1],a[3])+.012,max(a[2],a[4])+.012)]
        else:continue
        for box in boxes:actual_clock.append({'net':name,'box':box,'required_um':required(box,True)})
nets=re.search(r'^NETS .*?^END NETS',text,re.M|re.S).group()
patch_count=0
patch_expected=0
for body in nets.split(';'):
    t=body.split()
    if len(t)<2 or t[0]!='-' or t[1] not in clock:continue
    patch_expected+=len(re.findall(r'(?:NEW|FIXED) M5[^\n]*\bRECT\b',body))
    for a in re.findall(r'(?:NEW|FIXED) M5 \( (-?\d+) (-?\d+)(?: -?\d+)? \) RECT \( (-?\d+) (-?\d+) (-?\d+) (-?\d+) \)',body):
        x,y,l,b,r,t=map(int,a);box=((x+l)/1000,(y+b)/1000,(x+r)/1000,(y+t)/1000)
        actual_clock.append({'net':body.split()[1],'box':box,'required_um':required(box,True),'patch':True});patch_count+=1
assert patch_count==patch_expected,(patch_count,patch_expected)
clock_hits=[a for a in actual_clock if touches(a['box'],region,a['required_um'])]
clock_shapes=[a for a in actual_clock if touches(a['box'],(47,75,48.5,148))]
pg_hits=[{'box':a,'required_um':required(a)} for a in pg if touches(a,region,required(a))]
def gap(box):
    return max(box[0]-region[2],region[0]-box[2],box[1]-region[3],region[1]-box[3],0)
wide_clock=[a for a in actual_clock if min(a['box'][2]-a['box'][0],a['box'][3]-a['box'][1])>=wide_threshold-1e-10]
nearest_clock=min(actual_clock,key=lambda a:gap(a['box']))
nearest_pg=min(pg,key=gap)
summary = {'candidate_only':True, 'layer':'M5', 'region_um':region,
           'actual_instance':inst,'master':master,'origin_um':[ox,oy],'orientation':orient,
           'west_ports':len(west_ports),'signal_clock_rectangles':len(signal_ports),
           'M4_OBS_local':m4obs,'M5_actual_track_offset_pitch':[offset,pitch],
           'bad_good_via_x_um':[bad,good],'VIA45_M4_local':via_m4,'VIA45_M5_local':via_m5,
           'gap_um':gaps,'wide_spacing_threshold_required_um':[wide_threshold,wide_spacing],
           'M5_guard_width_required_spacing_um':[minw,spacing],
           'clock_nets_screened':len(clock),'actual_clock_M5_shapes':len(actual_clock),
           'clock_M5_patches':patch_count,'actual_clock_NDR_M5_width_spacing_um':[.024,.048],
           'clock_hits_with_actual_rule_spacing':clock_hits,'nearest_clock':dict(nearest_clock,gap_um=gap(nearest_clock['box'])),
           'wide_clock_shapes':len(wide_clock),'nearest_wide_clock_gap_um':min((gap(a['box']) for a in wide_clock),default=None),
           'actual_pg_boxes_screened':len(pg),'pg_hits_with_actual_rule_spacing':pg_hits,
           'nearest_pg':{'box':nearest_pg,'gap_um':gap(nearest_pg),'required_um':required(nearest_pg)},
           'outline_um':[0,0,270,403.920], 'source_data_cycles':0}
(out/'clearance.json').write_text(json.dumps(summary, indent=2)+'\n')
assert len(clock) > 1000 and len(pg) > 100, summary
assert not clock_hits and not pg_hits, summary
(out/'vms_macro_west_via_guard.tcl').write_text('''# Candidate only: derive/review with vms_access_guard_prepare.py.
# M4 ports/OBS remain unchanged; a minimum-width M5 obstruction forces west escape.
set b [ord::get_db_block]
set i [$b findInst {%s}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "%s" || [$i getOrient] ne "R0"} {
  error "VMS_VIA_GUARD: unexpected bank A master/orientation"
}
if {[$i getLocation] ne "%d %d"} { error "VMS_VIA_GUARD: unexpected actual origin" }
set l [[ord::get_db_tech] findLayer M5]
if {[$l getWidth] != 24 || [$l getSpacing] != 24} { error "VMS_VIA_GUARD: technology mismatch" }
odb::dbObstruction_create $b $l %d %d %d %d
puts "VMS_VIA_GUARD M5 %s, zero cycles, M4 escape unchanged"
''' % (inst,master,round(ox*1000),round(oy*1000),*(round(a*1000) for a in region),region))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, ax = plt.subplots(figsize=(8,7))
ax.add_patch(Rectangle((ox,oy), .72,height,facecolor='#ddd',label='Actual SRAM body (crop)'))
ax.add_patch(Rectangle((obswest,oy), .648,height,facecolor='#aaa',label='Existing M4 OBS starts +72nm'))
for a in west_ports:
    ax.add_patch(Rectangle((ox+a[0],oy+a[1]),a[2]-a[0],a[3]-a[1],facecolor='#555'))
ax.add_patch(Rectangle((region[0],region[1]),region[2]-region[0],region[3]-region[1],facecolor='#f0804080',edgecolor='#b04000',label='Proposed M5-only via exclusion'))
for a in clock_shapes:
    b=a['box']; ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor='#2878b580'))
for y in (94.584,94.680,119.880,136.008):
    ax.plot([47.663,47.688],[y,y],color='red',linewidth=2)
ax.axvline(bad,color='red',linestyle=':',label='Rejected near-pin via track')
ax.axvline(good,color='green',linestyle=':',label='Next west via track')
ax.set_xlim(47.30,48.05); ax.set_ylim(75.8,147.5)
ax.set_xlabel('Actual X (um) — horizontal scale expanded'); ax.set_ylabel('Actual Y (um)')
ax.set_title('VMS bank A: candidate M5 via exclusion\nM4 ports/OBS, supplies and frozen clocks unchanged')
ax.legend(fontsize=8,loc='center right'); ax.grid(alpha=.2)
fig.tight_layout(); fig.savefig(out/'review.png',dpi=150)
print(json.dumps(summary))
