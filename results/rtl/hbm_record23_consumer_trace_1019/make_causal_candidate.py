from pathlib import Path
import sys,json,hashlib
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019')
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static')]
from su_arith_generate import FIELDS
from hbm_layer_vehicle.layer_images import column_image
O=Path(__file__).resolve().parent
words=[int(s,16) for s in (D/'record23_profile/native18/quarter.mem').read_text().split()]
off={};pos=0
for name,width in reversed(FIELDS):off[name]=pos;pos+=width
widths=dict(FIELDS)
def get(c,n):return (c>>off[n])&((1<<widths[n])-1)
def put(c,n,v):return (c&~(((1<<widths[n])-1)<<off[n]))|(v<<off[n])
controls=[w>>680 for w in words]
issues=[(i,c) for i,c in enumerate(controls) if get(c,'emit')]
assert len(issues)==1,(len(issues),[i for i,c in issues])
base=put(put(issues[0][1],'emit',0),'ld',0)
# This exact record uses only A and O. Its source physically reads all4 ports.
# Copy A local address into semantically unused B/C/D; no new fetch or write.
assert all(get(c,'srcs')==0 for c in controls)
def legal(c):
 t=get(c,'ld_c');a=t&((1<<240)-1)
 v=get(c,'vb');av=v&0xffffff
 for role in [1,2,3]:
  assert (t>>(240*role))&((1<<240)-1)==0
  t|=a<<(240*role)
  v=(v&~(0xffffff<<(24*role)))|(av<<(24*role))
 return put(put(c,'ld_c',t),'vb',v)
patched=[(w&((1<<680)-1))|(legal(c if c else base)<<680) for w,c in zip(words,controls)]
assert len(patched)==len(words)==52
for old,new in zip(words,patched):assert (old^new)&((1<<680)-1)==0
for name,data in [('hold_and_local',patched),('hold_only',[(w&((1<<680)-1))|((c if c else base)<<680)for w,c in zip(words,controls)])]:
 dest=O/name;column_image(data,dest)
 (dest/'quarter.mem').write_text(''.join(f'{w:0606x}\n'for w in data))
print(json.dumps(dict(issues=[i for i,c in issues],commands=52,changed_control_edges=[i for i,(a,b) in enumerate(zip(words,patched))if a!=b],low680_unchanged=True),indent=2))
