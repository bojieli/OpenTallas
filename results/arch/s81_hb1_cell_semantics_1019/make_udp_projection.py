import pathlib,re,json,hashlib
p=pathlib.Path(__file__).resolve().parent
src=(p/'official/asap7sc7p5t_SEQ_RVT_TT_220101.v').read_text()
primitives=[];ledger=[]
for name in ['altos_dff','altos_dff_sr_0','altos_dff_err','altos_dff_sr_err']:
 raw=re.search(r'primitive '+name+r'\b.*?endprimitive',src,re.S).group()
 variants=[('default',None)] if name.endswith('err') else [('default',None),('init0',0),('init1',1)]
 for variant,val in variants:
  new='proj_'+name+('_'+variant if variant!='default' else '')
  text=raw.replace('primitive '+name+' ', 'primitive '+new+' ',1)
  if val is not None:text=text.replace('\n\ttable',f"\n\tinitial q = 1'b{val};\n\ttable",1)
  primitives.append(text);ledger.append({'name':new,'original':name,'initial':val,'original_sha256':hashlib.sha256(raw.encode()).hexdigest()})
m=json.loads((p/'manifest.json').read_text())['used_masters']
comb='`timescale 1ns/1ps\n'
for name,info in m.items():
 if name.startswith('DFF'):continue
 raw=(p/'official'/info['file']).read_text()
 comb+=re.search(r'module '+name+r'\b.*?endmodule',raw,re.S).group()+'\n'
wrappers='''
module DFFHQNx1_ASAP7_75t_R #(parameter INIT=-1)(output QN,input D,CLK);
reg notifier;wire nd,xcr;not(nd,D);proj_altos_dff_err e(xcr,CLK,nd);
generate if(INIT==0)begin proj_altos_dff_init0 u(QN,notifier,CLK,nd,xcr);end
else if(INIT==1)begin proj_altos_dff_init1 u(QN,notifier,CLK,nd,xcr);end
else begin proj_altos_dff u(QN,notifier,CLK,nd,xcr);end endgenerate
endmodule
module DFFASRHQNx1_ASAP7_75t_R #(parameter INIT=-1)(output QN,input D,RESETN,SETN,CLK);
reg notifier;wire nd,ns,nr,xcr;not(nd,D);not(ns,RESETN);not(nr,SETN);
proj_altos_dff_sr_err e(xcr,CLK,nd,ns,nr);
generate if(INIT==0)begin proj_altos_dff_sr_0_init0 u(QN,notifier,CLK,nd,ns,nr,xcr);end
else if(INIT==1)begin proj_altos_dff_sr_0_init1 u(QN,notifier,CLK,nd,ns,nr,xcr);end
else begin proj_altos_dff_sr_0 u(QN,notifier,CLK,nd,ns,nr,xcr);end endgenerate
endmodule
'''
header=src.split('// Verilog for library')[0]
(p/'validation/udp_functional_projection.v').write_text(header+'// Simulation-only derivative; see validation/README.md for changes and scope.\n'+comb+'\n'+'\n'.join(primitives)+wrappers)
(p/'validation/udp_ledger.json').write_text(json.dumps({'primitives':ledger,'scope':'Original Function gates and exact UDP tables; delayed_* replaced by actual pins; notifier left as original uninitialized reg; timing checks omitted; no timing/SDF. INIT=-1 default uninitialized, INIT0/1 explicitly seeds UDP output only for bench arbitrary state. Error UDP unchanged/uninitialized.'},indent=2)+'\n')
