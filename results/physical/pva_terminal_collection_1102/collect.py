from pathlib import Path
import json,hashlib,time,re,collections
root=Path('/srv/opentallas-scratch2/claude/die-kv-60/pvq');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out={}
for n in ['pvA_p2W','pvA_p2D']:
 k=root/n;base=next(k.glob('run/results/asap7/*/base'));so=json.loads((k/'signoff/signoff.json').read_text());insts={}
 for b in (base/'6_final.v').read_text().split(';'):
  m=re.match(r'\s*([A-Za-z_]\w+)\s+(\S+)\s+\(',b)
  if m and m[1]!='module':insts[m[2]]=m[1];insts[m[2].lstrip('\\')]=m[1]
 drv={};hold=[]
 for c in ['tt','ff']:
  text=(k/f'signoff/{c}/sta.log').read_text();b=text.split('max slew\n',1)[1].split('SO_PATH_END',1)[0];pins=[l.split()[0] for l in b.splitlines() if '(VIOLATED)' in l]
  drv[c]={'pins':pins,'master_counts':dict(collections.Counter(insts.get(v.rsplit('/',1)[0],'UNKNOWN') for v in pins)),'clock_pins':[v for v in pins if v.rsplit('/',1)[1] in ['CLK','CK','CLKN']]}
  if c=='ff':
   for b in text.split('Startpoint:')[1:]:
    if 'slack (VIOLATED)' in b:hold.append('Startpoint:'+b[:b.index('slack (VIOLATED)')+len('slack (VIOLATED)')])
 p=k/'lec/lec.json';old=json.loads(p.read_text())
 out[n]={'subject':str(k),'official_signoff':so,'current_files':{str(p.relative_to(k)):{'sha256':sha(p),'mtime':p.stat().st_mtime,'mtime_local':time.ctime(p.stat().st_mtime)} for p in [k/'prd_result.json',k/'signoff/signoff.json',base/'6_final.v',base/'6_final.spef',base/'6_final.odb',k/'clk_geom_diff.json']},'drv':drv,'hold_paths':hold,'copied_old_lec':{'path':str(p),'mtime':p.stat().st_mtime,'generated':old.get('generated'),'netlist':old.get('netlist'),'verdict':old.get('verdict'),'current_final_proof_credit':False},'original_dpl_overlap_class':'CLOSED: native route/fill/current placement and DRC pass','no_rerun_needed':True}
print(json.dumps(out,indent=2))
