# Critical-net limits for route2. ME-loop/layer-loop buses: root->sink steps <= max(grid Manhattan, stage boundary of the
# pin-pair stage count + extra). With other_extra>=0 every other bus is also bounded at its pin-pair stages + other_extra
# (floor 1.25 x Manhattan) so non-critical buses cannot detour without limit.
import json,re,sys,math
from pathlib import Path
CRIT=re.compile(r'^(head_\w+|cor_\d+_\d+|tap_\d+_\d+|tree_\d+_\d+_\d+[ab]|bword_\d+|pfrag_\d+_.*|slab_rq_\d+|rq_\d+|rs_\d+|xs_aw|seq_coll|seq_coll_x|coll_seq|coll_seq_x|x3|x3m|attn_ret|o4_cb_[aq]_\d+)$')
d=Path(sys.argv[1]);md=json.load(open(d/'route-metadata.json'));rows={r['bus']:r for r in json.load(open(sys.argv[2]))}
slack=float(sys.argv[3]) if len(sys.argv)>3 else 1.0;extra=int(sys.argv[4]) if len(sys.argv)>4 else 0;oextra=int(sys.argv[5]) if len(sys.argv)>5 else -1
MEFAM=r'^(tree_|bword_|head_23$|head_24$)';ADD=int(sys.argv[7]) if len(sys.argv)>7 else 2;MEADD=int(sys.argv[8]) if len(sys.argv)>8 else 0;B=md["grid_um"];ny=md['ny'];out=[];nc=no=0
for k,net in enumerate(md['nets']):
 bus=md['buses'][net['rid']]['bus'];c=bool(CRIT.match(bus))
 if not c and oextra<0:continue
 r0=net['terms'][0];man=max(abs(q//ny-r0//ny)+abs(q%ny-r0%ny) for q in net['endpoint_nodes'])
 stub=net['max_endpoint_stub_um'][0]+max(net['max_endpoint_stub_um']);pp=rows[bus]['pin_pair_ideal500_stages'] if bus in rows else 1
 if c:lim=max(math.ceil(man*slack)+ADD,int(((pp+extra)*500-stub)//B));nc+=1;out.append(f'{k} {lim} {MEADD if re.match(MEFAM,bus) else 0}');continue
 else:lim=max(math.ceil(man*1.5)+2,int(((pp+oextra)*500-stub)//B));no+=1
 out.append(f'{k} {lim}')
(Path(sys.argv[6]) if len(sys.argv)>6 else d/'crit.txt').write_text('\n'.join(out)+'\n');print('crit',nc,'other bounded',no,'of',len(md['nets']))
