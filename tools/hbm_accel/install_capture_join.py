#!/usr/bin/env python3
"""Install HA1 joins in a sibling of Euclid's actual ranked SM assembly.
No runtime authority dictionaries, event synthesis, new clocks or debt gates.
"""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
JOIN='rtl/hbm_accel/txcount/ot_hbm_txcount_capture_join.sv'

def install(base,out):
 base=base.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=True)
 book=json.loads((base/'ports.json').read_text());sv=(base/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
 if book['inventory']['rank_count']!=2 or book['inventory']['guarded_SM_count']!=64:raise ValueError('actual64SM ranked assembly required')
 top='ot_gpu_qwen_hbm_integrated_ranked_ha1'
 old='module ot_gpu_qwen_hbm_integrated_ranked #(parameter bit ENABLE=0)('
 if sv.count(old)!=1:raise ValueError('source module header')
 sv=sv.replace(old,'module '+top+' #(parameter bit ENABLE=0,parameter bit HA1_ENABLE=0)(')
 probes={'ha1_enabled':('output',1),'ha1_w6_visible_valid':('input',64),'ha1_w6_visible_ready':('input',64),'ha1_w6_fault':('input',64),'ha1_w6_visible_owner55':('input',64*55),
         'ha1_dependency_ready':('input',64),'ha1_dependency_valid':('output',64),'ha1_dependency_tuple':('output',64*239),
         'ha1_dependency_owner55':('output',64*55),'ha1_dependency_page_mask':('output',64*32),
         'ha1_retained':('output',64),'ha1_fault':('output',64)}
 declarations=''.join(f' {d} wire [{n-1}:0] {k},\n' for k,(d,n) in probes.items())
 sv=sv.replace(' input wire stream_clk,',declarations+' input wire stream_clk,',1)
 hardware='''
assign ha1_enabled=ENABLE && HA1_ENABLE;
generate for(genvar h=0;h<64;h=h+1)begin:ha1_actual_capture
 ot_hbm_txcount_capture_join #(.ENABLE(ENABLE && HA1_ENABLE),.INDEX(h)) join(
  .clk(stream_clk),.por_n(issuer_por_n),.rst_n(sm_rst_n[h]),
  .go_accept(issuer_backend_go_valid[h] && issuer_backend_go_ready[h]),
  .go_tuple(issuer_backend_go_tuple[h*239+:239]),.go_owner55(issuer_backend_go_owner[h*55+:55]),
  .go_page_mask(issuer_issue_output_page_mask[h*32+:32]),
  .rf_ack_accept(sm_rf_ack_accept[h]),.rf_ack_owner55(sm_rf_ack_owner55[h*55+:55]),
  .w6_visible_accept(ha1_w6_visible_valid[h] && ha1_w6_visible_ready[h]),
  .w6_visible_owner55(ha1_w6_visible_owner55[h*55+:55]),
  .producer_visible_accept(issuer_producer_visible_valid[h] && issuer_producer_visible_ready[h]),
  .producer_visible_tuple(issuer_producer_visible_tuple[h*239+:239]),
  .frame_retire_accept(issuer_frame_retire_valid[h] && issuer_frame_retire_ready[h]),
  .frame_retire_tuple(issuer_frame_retire_tuple[h*239+:239]),.frame_retire_owner55(issuer_frame_retire_owner[h*55+:55]),
  .source_fault(issuer_fault[h] || sm_rf_ack_fault[h] || ha1_w6_fault[h]),
  .dependency_valid(ha1_dependency_valid[h]),.dependency_ready(ha1_dependency_ready[h]),
  .dependency_tuple(ha1_dependency_tuple[h*239+:239]),.dependency_owner55(ha1_dependency_owner55[h*55+:55]),
  .dependency_page_mask(ha1_dependency_page_mask[h*32+:32]),.retained(ha1_retained[h]),.fault(ha1_fault[h]));
end endgenerate
'''
 if sv.count('endmodule')!=1:raise ValueError('single enclosing source required')
 sv=sv.replace('endmodule',hardware+'endmodule')
 (out/(top+'.sv')).write_text(sv)
 book['HA1_base_source_sha256']=hashlib.sha256((base/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_bytes()).hexdigest()
 book['HA1_base_driver_sha256']=hashlib.sha256((base/'pin_driver.cpp').read_bytes()).hexdigest()
 book['top']=top
 for k,(d,n) in probes.items():book['pins'][k]=dict(direction=d,bits=n,count=(1 if n==1 else 64),leaf_bits=(1 if n==1 else n//64),leaf=k.removeprefix('ha1_'),block='ha1')
 book['inventory']['HA1_capture_join_count']=64
 book['HA1']='default-off; actual W6 probes required; scheduler observation only, canonical debt unchanged'
 (out/'ports.json').write_text(json.dumps(book,indent=2)+'\n')
 deps=(base/'sources.f').read_text().splitlines();original='rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_hbm_integrated_ranked.sv'
 if deps.count(original)!=1:raise ValueError('ranked source selection')
 selected=str((out/(top+'.sv')).relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out/(top+'.sv'))
 deps[deps.index(original):deps.index(original)+1]=['rtl/hbm_accel/txcount/ot_hbm_rf_visibility_fence_live.sv','rtl/hbm_accel/txcount/ot_hbm_w6_source_select.sv',JOIN,selected]
 (out/'sources.f').write_text('\n'.join(deps)+'\n')
 # Retain the real enclosing pin driver; extend GET/SET only for added pins.
 driver=(base/'pin_driver.cpp').read_text().replace('Vot_gpu_qwen_hbm_integrated_ranked','V'+top).replace('ot_gpu_qwen_hbm_integrated_ranked ENABLE=',top+' ENABLE=')
 gets=[];sets=[]
 for k,(d,n) in probes.items():
  v='dut.'+k
  if n<=32:read=f'word(uint32_t({v}));';write=f'{v}=v[0];'
  elif n<=64:read=f'word(uint32_t({v}>>32));word(uint32_t({v}));';write=f'{v}=uint64_t(v[0]) | (uint64_t(v[1])<<32);'
  else:read=f'for(int i={(n+31)//32-1};i>=0;i--)word({v}[i]);';write=f'for(unsigned i=0;i<{(n+31)//32};i++){v}[i]=v[i];'
  gets.append(f' if(name=="{k}"){{{read}}} else\n')
  if d=='input':sets.append(f' if(name=="{k}"){{auto v=unpack(value,{n});{write}}} else\n')
 # Extend the actual driver refusal branches without adding a clock hook.
 for section,rows in [('GET',gets),('SET',sets)]:
  start=driver.index('else if(op=="'+section+'")');end=driver.find('else if(op==',start+1)
  if end<0:end=driver.index('catch(',start)
  chunk=driver[start:end]
  anchor='throw std::runtime_error("unknown pin");' if section=='GET' else 'throw std::runtime_error("unknown/output pin");'
  if chunk.count(anchor)!=1:raise ValueError('actual driver refusal anchor: '+section)
  chunk=chunk.replace(anchor,''.join(rows)+anchor)
  driver=driver[:start]+chunk+driver[end:]
 (out/'pin_driver.cpp').write_text(driver)
 return out
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--base',type=Path,default=ROOT/'rtl/model/qwen_hbm_integrated_20261003/ranked');a.add_argument('--out',type=Path,required=True);x=a.parse_args();install(x.base,x.out)
