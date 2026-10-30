import re,json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-hr-1030/phypad_rows');d=json.load(open(p/'selected100.json'));r=p/'run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base';v=(r/'6_final.v').read_text();cs={}
for m in re.finditer(r'BUFx2_ASAP7_75t_R\s+(\S+)\s*\((.*?)\);',v,re.S):
 name=m[1].lstrip('\\');cs[name]={x:y.strip().lstrip('\\') for x,y in re.findall(r'\.(\w+)\s*\(([^)]+)\)',m[2])}
wanted={cs[name]['Y'] for c in d['chains'] for name in c['cells']};text=(r/'6_final.spef').read_text();h,t=text.split('*D_NET',1);names={}
for l in h.splitlines():
 m=re.match(r'^(\*\d+)\s+(\S+)$',l)
 if m:names[m[1]]=re.sub(r'\\(.)',r'\1',m[2])
wire={}
for b in ('*D_NET'+t).split('*D_NET')[1:]:
 a=b.splitlines()[0].split();n=names.get(a[0],a[0])
 if n not in wanted:continue
 res=b.split('*RES',1)[1].split('*END',1)[0];rs=sum(float(l.split()[-1]) for l in res.splitlines() if l.strip());cp=float(a[1]);wire[n]={'resistor_sum_ohm':rs,'net_cap_pf':cp,'elmore_upper_ps':rs*cp}
assert wanted==set(wire),(len(wanted),len(wire),wanted-set(wire))
for c in d['chains']:
 c['old_ports']=[cs[name] for name in c['cells']];c['wire_rc']=[wire[cs[name]['Y']] for name in c['cells']];inter=sum(x['elmore_upper_ps'] for x in c['wire_rc'][:2]);c['interstage_wire_elmore_upper_ps']=inter;c['ff_min_cell_delta_ps']=min(c['ff_nldm'][t]['cell_delta_ps'] for t in ['rise','fall']);c['ff_cell_gain_less_old_interstage_wire_upper_ps']=c['ff_min_cell_delta_ps']-inter
json.dump(d,open(p/'selected100_rc.json','w'),indent=1)
print('chains',len(d['chains']),'max_interwire',max(c['interstage_wire_elmore_upper_ps'] for c in d['chains']),'min_gain_afterinterwire',min(c['ff_cell_gain_less_old_interstage_wire_upper_ps'] for c in d['chains']))
