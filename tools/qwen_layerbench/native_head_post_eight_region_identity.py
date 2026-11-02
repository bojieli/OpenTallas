#!/usr/bin/env python3
"""Read-only selected wrapper inspection; no compile or worktree operation."""
import hashlib,json,re,subprocess
from pathlib import Path
HOST='epyc2'
BASE='/srv/opentallas-scratch2/claude/codex-qc62-collect-1101/bind_complete4/rtl/'
WT='/srv/opentallas-scratch2/claude/wt/codex-qc62-bind-complete-1101/'
TOP=Path('/home/ubuntu/coord/tmp/codex-native-head-consumer-prep/qwen_compute_bound_top.sv')
OUT=Path('/home/ubuntu/coord/tmp/codex-native-head-post-eight-region-identity.json')
EXPECTED={'ADD_LAT':7,'BT_LAT':1,'JB':8,'MUT':0,'PIN_IN':1,'SCALE_LAT':7,'SKEW':14}
def read_remote(path):
 assert re.fullmatch(r'[\w/.-]+',path)
 return subprocess.check_output(['ssh',HOST,'cat '+path]).decode()
def h(s):return hashlib.sha256(s.encode()).hexdigest()
top=TOP.read_text();default_path=WT+'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv';defaults=read_remote(default_path)
header=defaults[:defaults.index(') (')];parsed_defaults={k:int(v) for k,v in re.findall(r'parameter integer\s+(\w+)\s*=\s*(\d+)',header)}
parsed_defaults['BT_LAT']=parsed_defaults['PIN_IN'];assert all(parsed_defaults[k]==v for k,v in EXPECTED.items())
wrappers=[];count=0
for block,sender,receiver in [(0,'W5','W4'),(148,'E3','E2')]:
 for role,sl in [('sender',sender),('receiver',receiver)]:
  for part in ['st_a','st_b']:
   tm=re.search(r'\n\s*(\w+)\s+sl_'+sl+'_'+part+r'\s*\((.*?)\n\s*\);',top,re.S);assert tm
   fn=BASE+tm[1]+'.sv';src=read_remote(fn)
   row={'block':block,'role':role,'slice':sl,'parent_instance':'sl_'+sl+'_'+part,'module':tm[1],'path':fn,'sha256':h(src),'parent_clk_expression':re.search(r'\.clk\(([^)]+)\)',tm[2])[1],'stations':[]}
   for m in re.finditer(r'\b(qfd_dv_s8_station_tail1(?:_nb0)?)\s*(?:#\((.*?)\))?\s+(u_u_r(\d))\s*\((.*?)\n\s*\);',src,re.S):
    mod,paramtext,inst,region,body=m.groups();region=int(region)
    ports=dict(re.findall(r'\.(\w+)\(([^\n]*)\),?\s*$',body,re.M))
    explicit={k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',paramtext or '')}
    effective=dict(EXPECTED);effective.update(explicit)
    assert all(effective[k]==v for k,v in EXPECTED.items())
    assert ports['ck']=='clk';assert mod==('qfd_dv_s8_station_tail1_nb0'if role=='sender'else'qfd_dv_s8_station_tail1')
    assert (part=='st_a')==(region<4)
    local=region%4;expected_bt=('w_u_btab_bt_q'if part=='st_a'else'x_st_a_i_q')+f'[{32*local+31}:{32*local}]'
    assert ports['bt_q_p']==expected_bt,(inst,ports['bt_q_p'],expected_bt)
    fields={k:v for k,v in ports.items()if k in ['bt_q_p','ck','rst_n','rs_s_lo_p','rs_s_hi_p','rs_n_lo_p','rs_n_hi_p','rs_s_c_p','rs_n_c_p','nb_d_p','nb_c_p']}
    assert all(k in fields for k in ['rs_s_lo_p','rs_s_hi_p','rs_n_lo_p','rs_n_hi_p'])
    for k in ['rs_s_lo_p','rs_s_hi_p','rs_n_lo_p','rs_n_hi_p']:
     val=ports[k]
     if val.startswith('{'):
      bits=re.findall(r'\w+\[0\]',val);assert len(bits)==64,(inst,k,len(bits))
     else:
      mm=re.search(r'\[(\d+):(\d+)\]',val);assert mm and int(mm[1])-int(mm[2])+1==64,(inst,k,val)
    row['stations'].append({'module':mod,'instance':inst,'region':region,'line':src[:m.start()].count('\n')+1,'explicit_params':explicit,'effective_params':effective,'literal_ck_clk':True,'bt_global_bit_interval':[32*region,32*region+32],'literal_ports':fields,'actual_instance_source':m[0]})
   assert len(row['stations'])==4
   if part=='st_a':
    matches=[{'line':i,'source':l}for i,l in enumerate(src.splitlines(),1)if 'u_bout_x_st_b_o' in l]
    assert len(matches)==1 and 'w_u_btab_bt_q[255:128]'in matches[0]['source'];row['upper_BTAB_transport_source']=matches[0]
   else:
    matches=[{'line':i,'source':l}for i,l in enumerate(src.splitlines(),1)if 'u_bin_x_st_a_i' in l];assert len(matches)==1;row['upper_BTAB_boundary_capture']=matches[0]
   count+=len(row['stations']);wrappers.append(row)
assert count==32
result={'status':'PASS_SOURCE_IDENTITY_AND_LITERAL_8REGION_SELECTION','wrapper_count':8,'station_count':32,'rows':'two row-block contexts; each sender+receiver uses all8 two-lane regions','effective_params':EXPECTED,'receiver_default_source':{'path':default_path,'sha256':h(defaults),'actual_header':header},'selected_bound_top':{'path':str(TOP),'sha256':h(top)},'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'wrappers':wrappers,'scope':'Source module identity and literal lane/scale selection only. Distinct selected parent regional clocks retained as facts. One-clock sequential context reuse is an explicit numerical component premise, not selected spatial transport or phase proof.'}
OUT.write_text(json.dumps(result,indent=2)+'\n');print(OUT,h(OUT.read_text()),count)
