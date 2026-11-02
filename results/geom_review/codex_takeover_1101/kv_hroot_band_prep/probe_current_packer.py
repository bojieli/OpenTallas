from pathlib import Path
import re,sys,json,subprocess,os,copy
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design(str(P/'inputs/geom.tsv'));body=Path('/home/ubuntu/OpenTallas/tools/die_plan/landing_placement.tcl').read_text();r=[1326.24,86.4,1412.64,120.96];bus='i_kvpc_Q_N_o_next';ring={k:c for k,c in D.cells.items() if 'u_cland_'+bus+'/' in c[6]}
def hit(c):return min(c[4],r[2])>max(c[2],r[0]) and min(c[5],r[3])>max(c[3],r[1])
procs=re.findall(r'^proc [^\n]+\n.*?^}\n|^proc [^\n]+}\n',body,re.M|re.S)
s='\n'.join(procs)+'''\nset ff_x0 4320;set ff_y0 4320;set ff_x1 1896480;set ff_y1 833760;set ff_dbu 1000;set ff_sw 54;set ff_rh 270
set ff_orient {};for {set y 4320} {$y < 833760} {incr y 270} {dict set ff_orient $y R0}
set cland_occ {};set cland_done {};set cland_n 0;set cland_cursor {};set cland_col_cursor {};set cland_famw {};set cland_ff_fill .90
set cland_fh [open /dev/null w];set instances {};set bterms {};set places {}
'''
masters=[]
lef=(P/'inputs/asap7_R_actual.lef').read_text()
for nm,txt in re.findall(r'^MACRO (\S+)\n(.*?)^END \1\s*$',lef,re.M|re.S):
 m=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',txt)
 if not m:continue
 w,h=[round(float(x)*1000) for x in m.groups()];masters.append(nm)
 s+=f'proc {nm} {{m args}} {{switch $m {{getName {{return {nm}}} getWidth {{return {w}}} getHeight {{return {h}}} isBlock {{return 0}} }} }}\n'
s+='proc mlib {m args} {return {'+' '.join(masters)+'}}\nnamespace eval ord {proc get_db {} {return mdb}}\nproc mdb {m args} {return {mlib}}\n'
for k,c in ring.items():
 s+=f'proc i{k} {{m args}} {{switch $m {{getName {{return {{{c[6]}}}}} getMaster {{return {c[1]}}} getPlacementStatus {{return PLACED}} setPlacementStatus {{}} setOrient {{}} setLocation {{dict set ::places {k} $args}} }} }}\nlappend instances i{k}\n'
for p in D.pins:
 if p['name'].startswith(bus+'[') or p['name']=='cland_fstart_in_'+bus+'[0]':
  k=p['k'];x=round(p['x']*1000);y=round(p['y']*1000)
  s+=f'proc bb{k} {{m args}} {{switch $m {{xMin {{return {x}}} xMax {{return {x}}} yMin {{return {y}}} yMax {{return {y}}} }} }}\nproc bt{k} {{m args}} {{switch $m {{getName {{return {{{p["name"]}}}}} getBBox {{return bb{k}}} }} }}\nlappend bterms bt{k}\n'
s+='proc block {m args} {switch $m {getInsts {return $::instances} getBTerms {return $::bterms}}}\nset ff_blk block\n'
for k,c in D.cells.items():
 if k not in ring and hit(c):s+='cland_occupy '+' '.join(str(round(v*1000)) for v in (c[2],c[3],c[4]-c[2],c[5]-c[3]))+'\n'
s+='if {[catch {cland_place_ff u_cland_'+bus+' {'+' '.join(map(str,r))+'} ring:'+bus+'+x+ff} e o]} {puts "ERROR $e";puts [dict get $o -errorinfo];exit 1}\ndict for {k xy} $places {puts "LOC $k $xy"}\n'
(P/'packer_probe.tcl').write_text(s)
e=os.environ.copy();e['OT_CLAND_FIT_RESERVE']='resize';e['OT_CLAND_PINSLOT']='1'
q=subprocess.run(['tclsh'],input=s,text=True,capture_output=True,env=e);(P/'packer_probe.log').write_text(q.stdout+q.stderr)
if q.returncode:print((q.stdout+q.stderr)[-5000:]);raise SystemExit(q.returncode)
E=copy.deepcopy(D);locs={}
for k,x,y in re.findall(r'^LOC (\d+) (\d+) (\d+)',q.stdout,re.M):
 k=int(k);x=int(x)/1000;y=int(y)/1000;c=E.cells[k];b=(x,y,x+c[4]-c[2],y+c[5]-c[3]);E.cells[k]=c[:2]+b+(c[6],);locs[k]=list(b)
basepairs=[];afterpairs=[];base=g.r2r_metrics(D,basepairs);after=g.r2r_metrics(E,afterpairs);old={x['capture'] for x in basepairs};added=[x for x in afterpairs if x['capture'] not in old]
pinmap={int(re.search(r'\[(\d+)\]',p['name'])[1]):p for p in D.pins if p['name'].startswith(bus+'[')};dist=[]
for k,b in locs.items():
 m=re.search(r's_d\[\d+\]\[(\d+)\]',D.cells[k][6].replace(chr(92),''))
 if m and int(m[1]) in pinmap:
  p=pinmap[int(m[1])];dist.append(abs(p['x']-(b[0]+b[2])/2)+abs(p['y']-(b[1]+b[3])/2))
z={'scope':'Actual current Tcl FF packer executed against exact TSV names/ports/master sizes/obstacles and pinned actual RVT LEF, using geometry object adapters; not OpenDB/PG/route credit','placed_ffs':len(locs),'storage_ffs_checked':len(dist),'correct_bit_storage_reach_max_um':max(dist),'before':base,'after':after,'new_bad_captures':added,'rvt_lef':str(P/'inputs/asap7_R_actual.lef'),'helper_revision':'approved main d5fe8b3a6 ancestry current body','positions':locs};(P/'current_packer_witness.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps({k:v for k,v in z.items() if k!='positions'},indent=2));print(q.stdout[:1200])
