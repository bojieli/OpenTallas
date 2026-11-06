import re,json
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--include-native-controls',action='store_true');parser.add_argument('--out',type=Path);args=parser.parse_args()
b=args.work_dir
ff={ln.split(chr(9))[0] for ln in (b/'native_ff_clocks.tsv').read_text().splitlines()}
groups={}
for ln in (b/'native_instances.tsv').read_text().splitlines():
 f=ln.split(chr(9));n=f[0]
 if n not in ff:continue
 pattern=r'u_ft_ft\d+_o_\d+|u_cland_ft\d+_i'
 if args.include_native_controls:pattern+=r'|u_rrl_\d+(?:_t)?|u_rst_in|u_cland_collect_[A-Za-z0-9_]+|u_cland_monitor_\d+'
 m=re.match(r'u_bound\.('+pattern+r')(?:[/.]|$)',n)
 if not m:continue
 x,y,X,Y=map(float,f[2:]);key='u_bound.'+m[1]
 z=groups.setdefault(key,[0,x,y,X,Y]);z[0]+=1;z[1]=min(z[1],x);z[2]=min(z[2],y);z[3]=max(z[3],X);z[4]=max(z[4],Y)
(args.out or b/'mapped/native_groups.json').write_text(json.dumps(groups,indent=1))
print('NATIVE_GROUPS',len(groups))
