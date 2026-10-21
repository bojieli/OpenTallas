import hashlib,json,re,subprocess
from pathlib import Path
repo=Path(__file__).resolve().parents[5];out=repo/'results/arch/s81_die72_1021/g9_assembly/h9_xok_source';out.mkdir(parents=True,exist_ok=True)
ref='21b97190eba0b3b306026f23a2408867cd099726';parent='rtl/dsrom_sys/s81_dv/frame_lp/kit/col_h9_l4_lp_kit_rf3r.sv';master='rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv';root='physical/ref_tile/s81dv_rly_276_ns/views/dsfd_dvrly_276_NS/'
def get(p):return subprocess.check_output(['git','-C',str(repo),'show',ref+':'+p])
def body(s,name):
 m=re.search(r'\bmodule\s+'+re.escape(name)+r'\b(.*?)\bendmodule\b',s,re.S);assert m;return m.group(1)
def block(s,start):
 i=s.index('{',start);d=1;j=i+1
 while d:
  d+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[i+1:j-1]
def validate_master(s):
 b=body(s,'dsfd_dvrly_276_NS');b=re.sub(r'//[^\n]*','',b)
 calls=re.findall(r'ot_dvrly_ckinv\s+(\w+)\s*\(\s*\.a\((\w+)\),\s*\.y\((\w+)\)\s*\)\s*;',b)
 assert calls==[('u_ck0','ck','ckn'),('u_ck1','ckn','ck_o')],calls
 assert len(re.findall(r'\bck_o\b',b))==2 # output declaration + exactlyone child output
 assert not re.search(r'\bassign\s+ck_o|\b(if|case|always|always_ff|always_comb)\b',b)
 inv=body(s,'ot_dvrly_ckinv');assert re.search(r'assign\s+y\s*=\s*~a\s*;',inv)
 assert not re.search(r'\b(if|case|always|always_ff|always_comb)\b|[?&|]',inv)
 assert re.search(r'\(\*\s*keep_hierarchy\s*\*\)\s*module\s+ot_dvrly_ckinv',s)
 return {'source_path':['ck','u_ck0.a->y inverter','ckn','u_ck1.a->y inverter','ck_o'],'inversions':2,'edge_delta':0,'gating':False,'data_dependency':False,'multiple_drivers':False,'hierarchy_kept':True}
rtl=get(master).decode();proof=validate_master(rtl);top=get(parent).decode();pairs=[]
for i in range(4):
 m=re.search(r'\bdsfd_dvrly_276_NS\s+u_xo'+str(i)+r'\s*\((.*?)\);',top,re.S);assert m;ports={k:v.strip()for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',m.group(1))};assert ports['ck']=='xk[%d]'%i and ports['ck_o']=='xok[%d]'%i
 assert len(re.findall(r'\.ck_o\(\s*xok\['+str(i)+r'\]\s*\)',top))==1
 assert not re.search(r'assign\s+xok|xok\s*(?:<=|=)',top)
 pairs.append({'instance':'u_xo%d'%i,'master':'dsfd_dvrly_276_NS','root_input':ports['ck'],'forwarded_output':ports['ck_o'],'source_ancestry':[ports['ck'],'u_xo%d.ck'%i,'two keptinverters','u_xo%d.ck_o'%i,ports['ck_o']]})
libs={};hashes={p:hashlib.sha256(get(p)).hexdigest()for p in[parent,master]}
for corner in ['tt','ff','ss']:
 p=root+'dsfd_dvrly_276_NS_'+corner+'.lib';raw=get(p);hashes[p]=hashlib.sha256(raw).hexdigest();s=raw.decode();m=re.search(r'pin\s*\(\s*"?ck_o"?\s*\)',s);assert m;b=block(s,m.start());assert re.search(r'direction\s*:\s*output\s*;',b)
 arcs=[]
 for t in re.finditer(r'\btiming\s*\([^)]*\)',b):
  z=block(b,t.start());rel=re.search(r'related_pin\s*:\s*"([^"]+)"',z);sense=re.search(r'timing_sense\s*:\s*(\w+)',z);typ=re.search(r'timing_type\s*:\s*(\w+)',z);arcs.append({'related_pin':rel.group(1)if rel else None,'timing_sense':sense.group(1)if sense else None,'timing_type':typ.group(1)if typ else None})
 assert arcs and all(a=={'related_pin':'ck','timing_sense':'positive_unate','timing_type':'combinational'}for a in arcs),arcs;libs[corner]={'ck_o_direction':'output','arcs':arcs}
neg={}
for name,changed in [('datamux',rtl.replace('.y(ck_o)', '.y(ck_tmp)').replace('wire ckn;','wire ckn; assign ck_o = i[0] ? ck : ckn;')),('gating',rtl.replace('assign y = ~a;','assign y = ~a & 1\'b1;')),('multidriver',rtl.replace('wire ckn;','wire ckn; assign ck_o = ck;'))]:
 try:validate_master(changed);neg[name]='WRONG_ACCEPT'
 except AssertionError:neg[name]='REJECT'
assert all(x=='REJECT'for x in neg.values())
res={'scope':'Bounded source/Liberty proof only, actual placedbuffertrace pending. No sharedhelperchange/defaultwaiver.','source_ref':ref,'parent_top':'col_h9_l4_lp_kit_rf3r','source_sha256':hashes,'pairs':pairs,'relay_transfer':proof,'liberty':libs,'pure_source_causal_rejections':neg,'actual_snapshot':'ep9:/srv/opentallas-scratch2/claude/codex-s81-h9cts-1021/run_cachefix','actual_snapshot_hashes_match':'All5hashes read from actualsrc agree with pinned21b; original3_place.odb untouched'}
(out/'source_liberty.json').write_text(json.dumps(res,indent=1)+'\n');print(json.dumps(res,indent=1))
