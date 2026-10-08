#!/usr/bin/env python3
"""Distinct complete synchronous-CE hierarchy; not a protected transaction shell."""
from pathlib import Path
import hashlib,re,json
R=Path(__file__).resolve().parents[1];D=R/'rtl/hbm_accel/control_20261007/protected_registered'
BASE=R/'rtl/hbm_accel/control_20261007/ot_hbm_sm_serial_owner.sv'
ING=R/'rtl/hbm_accel/control_20261007/ot_hbm_sm_seq_ingress.sv'
SM=R/'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv'
BC=R/'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv'
critical='state,record,address,limit,count,index,word_index,group,ordinal,weight_base,resident,resident_base,resident_extent,resident_c,resident_fmt,arrive_q,arrived,published,started,fault,xw_en,xw_addr,xw_grp,xw_data'
names=['ot_hbm_sm_serial_owner','ot_hbm_sm_seq_ingress','ot_hbm_accel_smv_chan','ot_hbm_accel_smv_chain','ot_hbm_accel_smv_pipe','ot_hbm_accel_bc_kreg']
rename={n:'ot_hbm_regcheck_'+n.removeprefix('ot_hbm_') for n in names}

def transform(n,s):
 s=re.sub(r'input\s+wire\s+clk', 'input wire step_en,\n input wire clk',s,count=1)
 for a,b in rename.items():s=s.replace(a,b)
 s=s.replace('.clk(clk)', '.clk(clk),.step_en(step_en)')
 if n==names[0]:
  s=s.replace('output reg fault\n);','output reg fault,output wire[2672:0] state_observe\n);')
  s=s.replace('wire[31:0] rows=', 'wire[100:0] ingress_observe;\n assign state_observe={'+critical+',ingress_observe};\n wire[31:0] rows=')
  s=s.replace('.fault(ingress_fault));','.fault(ingress_fault),.state_observe(ingress_observe));')
  s=s.replace('end else begin\n   xw_en<=0;', 'end else if(step_en)begin\n   xw_en<=0;')
 elif n==names[1]:
  s=s.replace('output reg fault\n);','output reg fault,output wire[100:0] state_observe\n);')
  s=s.replace('reg active,pending;', 'wire[50:0] channel_observe;\n assign state_observe={active,pending,payload,fault,channel_observe};\n initial if(HOPS!=0||DEPTH!=1)$fatal(1,"selected CE owner ingress geometry");\n reg active,pending;')
  s=s.replace('.m_data(received));','.m_data(received),.state_observe(channel_observe));')
  s=s.replace('else if(ENABLE) begin','else if(step_en && ENABLE) begin')
 elif n==names[2]:
  s=s.replace('output wire [W-1:0] m_data','output wire[W+3:0] state_observe,\n    output wire [W-1:0] m_data')
  s=s.replace('localparam integer CW', 'initial if(P!=0||DEPTH!=1)$fatal(1,"selected CE owner channel geometry");\n    assign state_observe={cred,wp,rp,cnt,(cnt!=0?mem[0]:{W{1\'b0}})};\n    localparam integer CW')
  s=s.replace('else cred <=','else if(step_en) cred <=').replace('else begin\n            if (f_v)', 'else if(step_en)begin\n            if (f_v)').replace('if (f_v) mem[wp]', 'if (step_en && f_v) mem[wp]')
 elif n==names[4]:s=s.replace('always @(posedge clk) q <= d;', 'always @(posedge clk) if(step_en) q <= d;')
 elif n==names[5]:s=s.replace('else q <= d;', 'else if(step_en) q <= d;')
 return s

def main():
 D.mkdir(parents=True,exist_ok=True);parts=[];sources={}
 for path,wanted in [(BASE,[names[0]]),(ING,[names[1]]),(SM,names[2:5]),(BC,[names[5]])]:
  text=path.read_text();sources[str(path.relative_to(R))]=hashlib.sha256(path.read_bytes()).hexdigest()
  for n in wanted:
   s=re.search(r'module '+n+r'\b.*?endmodule',text,re.S)[0]
   parts.append('// Source SHA256 '+sources[str(path.relative_to(R))]+'\n'+transform(n,s))
 (D/'ot_hbm_regcheck_ce_hierarchy.sv').write_text('// GENERATED synchronous CE foundation. No external transaction shell or registered verification yet.\n'+'\n\n'.join(parts)+'\n')
 print(json.dumps(dict(source_sha256=sources,modules=rename,observed_bits=2673,scope='CE foundation only')))
if __name__=='__main__':main()
