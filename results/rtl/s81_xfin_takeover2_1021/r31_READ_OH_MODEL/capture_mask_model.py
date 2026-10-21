from pathlib import Path
import re,json
root=Path('/home/ubuntu/wt/codex-s81-xfin-takeover2-1021');s=(root/'rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv').read_text();s=s[s.index('module ot_s81dv_finish_readgroup #'):s.index('module ot_s81dv_finish_readgroup_oh')]
func={}
for n in ['ca_node','cb_node','node_role','node_rank']:
 f=re.search(r'function[^\n]*\b'+n+r'\(.*?endfunction',s,re.S).group(0);cases=re.findall(r'case\(n\)(.*?)endcase',f,re.S);func[n]=[{int(a):int(b) for a,b in re.findall(r"8'd(\d+):\s*"+n+r"=8'd(\d+)",c)} for c in cases]
profiles={}
for name,tr,assoc,leaf in [('norm',1,False,False),('norm_mutleaf',1,False,True),('eng',3,False,False),('eng_mutassoc',3,True,False)]:
 k=0 if assoc else 1;ca,cb,role,rank=[func[n][k] for n in ['ca_node','cb_node','node_role','node_rank']];nb=19 if tr==3 else 17;ng=(nb+2)//3;nc=tr*128;mask=0;counts=[];nodes=sorted(ca)
 assert len(nodes)==79 and set(ca)==set(cb)
 def desc(n,t,pb):
  if n>=128:
   ix=n-128
   if leaf and ix==1:ix=2
   slot=t*16+ix//5;bank=pb*5+ix%5
  else:
   slot=t*39+rank.get(n,0);bank=15+role.get(n,0)*(2 if tr==3 else 1)+slot//64
  return bank,(slot>>1)%32,slot%2
 for g in range(ng):
  count=0
  for t in range(tr):
   for n in nodes:
    used=False
    for oa in range(4):
     for ob in range(4):
      da=desc(ca[n],t,oa);db=desc(cb[n],t,ob)
      for bank in range(g*3,min(nb,g*3+3)):
       aa=da[0]==bank;bb=db[0]==bank;row=da[1] if aa else db[1]
       if aa or bb or row or da[2] or db[2]:used=True
    if used:mask|=1<<(g*nc+t*128+n);count+=1
  counts.append(count)
 profiles[name]={'TREES':tr,'NC':nc,'groups':ng,'used_capture_counts':counts,'width':ng*nc,'mask_hex':format(mask,'0'+str((ng*nc+3)//4)+'x'),'new_capture_total':sum(counts),'old_capture_total':ng*tr*79}
print(json.dumps(profiles,indent=2));Path('/home/ubuntu/scratch/codex-s81-xfin-takeover2-1021/read_oh_capture_masks.json').write_text(json.dumps(profiles,indent=2)+'\n')
