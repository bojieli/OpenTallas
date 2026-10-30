from pathlib import Path
import json,sys,re,collections
p=Path.cwd();kind,stem=sys.argv[1:];d=p/f'physical/{kind}_pin_clock_install';sl=json.load(open(p/'plans'/(stem+'.json')));tree=sl['core_tree'];norm=lambda s:s.replace(chr(92),'')
expected={norm(n['name'])+'/A':norm(n['parent']).replace('port:ck','root')for n in tree['nodes']};expected.update({norm(g['inst'])+'/CLK':norm(g['parent'])for g in tree['gates']})
for l in tree['leaves']:
 for q in l['sinks']:expected[norm(q)]=l['node']
actual={};masters={}
for line in open(d/'clock_census.tsv'):
 f=line.rstrip().split('\t')
 if f[0]=='S':actual[norm(f[3])+'/'+f[4]]=norm(f[1].split('>')[-1]);masters[norm(f[3])]=f[5]
missing=sorted(expected.keys()-actual.keys());extra=sorted(actual.keys()-expected.keys());mismatch=[(k,v,actual.get(k))for k,v in expected.items()if actual.get(k)!=v]
wrongmaster=[n['name']for n in tree['nodes']if masters.get(n['name'])!=n['master']]
if missing or extra or mismatch or wrongmaster:raise ValueError((missing[:3],extra[:3],mismatch[:3],wrongmaster[:3]))
pins={}
for line in open(d/'geom_clock_installed.tsv'):
 f=line.rstrip().split('\t')
 if f[0]=='P':pins[f[2]]=(f[5],round(float(f[6])*1000),round(float(f[7])*1000))
public=json.load(open(p/f'impact/public_{kind}_pins.json'))['pins'];pinm=[r['name']for r in public if pins.get(r['name'])!=(r['layer'],round(r['x']*1000),round(r['y']*1000))]
if pinm:raise ValueError(('public pin mismatch',pinm[:4]))
sys.path.insert(0,str(p/'geom_tools'));import geom_rules as G
D=G.Design(d/'geom_clock_installed.tsv');reach=G.r2r_metrics(D);face=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));log=(d/'install_clock_geometry.log').read_text();edge=(d/'collect_after.log').read_text();r=dict(scope='actual geometry and exact planned clock connectivity; no STA/GRT',clock_cells=len(tree['nodes']),functional_gates=len(tree['gates']),clock_sinks=sum(len(l['sinks'])for l in tree['leaves']),clock_input_terms=len(actual),direct_parent_mismatches=0,missing_clock_terms=0,extra_clock_terms=0,buffer_master_mismatches=0,public_signal_pins=len(public),public_pin_mismatches=0,all_original_geometry_unchanged='A0_ALL_ORIGINAL_GEOMETRY_UNCHANGED'in log,all_clock_body_displacement_dbu=0,ff_reach=reach,face=face,macro_interface_direct_reach=next(l for l in edge.splitlines()if l.startswith('A0_MACRO_INTERFACE_DIRECT_REACH')))
json.dump(r,open(d/'FINAL_GEOMETRY.json','w'),indent=2);print(json.dumps(r))
