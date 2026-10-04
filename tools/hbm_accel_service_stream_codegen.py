#!/usr/bin/env python3
"""Derive the one selected protected short-window PC from pinned 52ce3.

This is a source transformation, not a memory timing or inference simulation.
Every sequential assignment also updates a fail-closed SECDED shadow. The live
flags remain unencoded, avoiding a decode on the iteration feedback loop.
"""
import hashlib,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def generate():
 s=subprocess.check_output(['git','show','52ce3e9c1:rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv'],cwd=ROOT,text=True)
 origin=hashlib.sha256(s.encode()).hexdigest()
 s=re.sub(r'//[^\n]*','',s)
 s=s.replace('module ot_hbm_r14_stream_pc','module ot_hbm_accel_stream_pc')
 s=re.sub(r'(input\s+wire\s+\[10:0\]\s+desc_n,)',r'\1 input wire [10:0] desc_first,',s)
 s=s.replace('input  wire        go, input wire next_posted,','input  wire        go, input wire next_posted, input wire col_gnt,\n  output wire window_end, output wire window_next,')
 s=s.replace('assign ref_fault=0;', 'assign ref_fault=0; assign window_end=0; assign window_next=0;')
 s=s.replace('    localparam integer PERIOD', '''    import ot_gpu_w6_secded_pkg::*;
    function automatic [287:0] seal256(input [255:0] raw);
      for(integer k=0;k<4;k=k+1) seal256[k*72+:72]=encode64(raw[k*64+:64]);
    endfunction
    wire [31:0] bank_protect;
    wire [3:0] bg_protect;
    reg next_valid; reg [18:0] next_row; reg [10:0] next_first,next_n;
    localparam integer PERIOD''')
 s=s.replace('wire rd_ok;', 'wire rd_ok;')
 s=s.replace('assign rd_ok = running', 'wire rd_offer; assign rd_ok=rd_offer&&col_gnt;\n    assign rd_offer = !protection_bad && running')
 s=s.replace('assign col_v = rd_ok;', 'assign col_v = rd_offer;')
 s=s.replace('assign row_v = c_v;', 'assign row_v = c_v && !protection_bad;')
 s=s.replace('assign desc_r = !streaming && !fault_r;', 'assign desc_r = !next_valid && !fault_r && !protection_bad;')
 s=s.replace('assign busy = streaming; assign ref_fault = fault_r;', 'assign busy = streaming || next_valid; assign ref_fault = fault_r || protection_bad;\n    assign window_end=rd_ok && j==nm1; assign window_next=next_valid||(streaming&&desc_v&&desc_r);')
 s=s.replace('streaming <= 0; last <= 0; nm1 <= 0;', 'next_valid<=0; next_row<=0; next_first<=0; next_n<=0;\n        streaming <= 0; last <= 0; nm1 <= 0;')
 s=s.replace('if (j[6:2] == 5\'d31) done[rd_bank] <= 1\'b1;', 'if (j[6:2] == 5\'d31 && !window_next) done[rd_bank] <= 1\'b1;')
 s=s.replace('if (j == nm1) streaming <= 0;', '''if (j == nm1) begin
            if(next_valid) begin
              j<=next_first; n<=next_n; row<=next_row; done<=0;
              nm1<=next_first+next_n-1'b1; last<=3'((next_first+next_n-1'b1)>>7);
              stale <= (row==next_row) ? stale : open_nx;
              next_valid<=0;
            end else if(desc_v&&desc_r)begin
              j<=desc_first;n<=desc_n;row<=desc_row;done<=0;
              nm1<=desc_first+desc_n-1'b1;last<=3'((desc_first+desc_n-1'b1)>>7);
              stale<=(row==desc_row)?stale:open_nx;
            end else begin streaming<=0; running<=0; end
          end''')
 s=s.replace('if (desc_v && !streaming && !fault_r) begin', '''if(desc_v && desc_r && streaming && !window_end) begin
          next_valid<=1; next_row<=desc_row; next_first<=desc_first; next_n<=desc_n;
        end
        if (desc_v && desc_r && !streaming && !fault_r) begin''')
 s=s.replace('j <= 0; n <= desc_n;', 'j <= desc_first; n <= desc_n;')
 s=s.replace("nm1 <= desc_n - 11'd1; last <= 3'((desc_n - 11'd1) >> 7);", "nm1 <= desc_first+desc_n-11'd1; last <= 3'((desc_first+desc_n-11'd1)>>7);")
 s=s.replace('stale <= open_nx;', 'stale <= (row==desc_row) ? stale : open_nx;')
 # Scalar/array state names written by nonblocking assignments.
 targets=set(re.findall(r'\b(\w+)(?:\[[^\[\];\n]+\])?\s*<=',s))
 declarations={}; groups={'bank':[], 'bg':[], 'top':[]}; shadow_bits=0
 def declare(m):
  nonlocal shadow_bits
  width,names=m.groups();hi=(width or '[0:0]')[1:-1].split(':')[0]
  W='1' if not width else (hi[:-2] if hi.endswith('-1') else str(int(hi)+1))
  additions=[]
  for name in names.split(','):
   match=re.fullmatch(r'\s*(\w+)\s*(\[[^]]+\])?\s*',name)
   if not match or match[1] not in targets:continue
   name,dim=match.groups();dim=dim or '';declarations[name]=(W,dim)
   if name in ['rcd','ras','aok','rtp']: group='bank'
   elif name in ['rrdl','ccdl','faw']: group='bg'
   else: group='top'
   cw=72*((int(W)+63)//64) if W.isdigit() else 72
   copies=1 if not dim else abs(int(dim[1:-1].split(':')[1])-int(dim[1:-1].split(':')[0]))+1
   scope=32 if group=='bank' else 4 if group=='bg' else 1
   shadow_bits+=cw*copies*scope
   additions.append(f'reg [{cw-1}:0] {name}_seal {dim};')
   indices=[''] if not dim else [f'[{i}]' for i in range(copies)]
   for index in indices:
    groups[group].append(f"({name}_seal{index} != {cw}'(seal256(256'({name}{index}))))")
  return m.group(0)+'\n      '+'\n      '.join(additions)
 s=re.sub(r'\breg\s*(\[[^]]+\])?\s*([^;]+);',declare,s)
 def assignment(m):
  target,expr=m.groups();base=target.split('[')[0]
  if base not in declarations:return m.group(0)
  W,dim=declarations[base];suffix=target[len(base):]
  if m.start()>0 and s[:m.start()].rstrip()[-1:]=='(':return m.group(0)
  if suffix and not dim:
   index=suffix[1:-1]
   if ':' in index:raise ValueError('unhandled sequential part-select '+target)
   future=f"(({base} & ~({W}'(1)<<({index}))) | ({W}'(1'({expr}))<<({index})))"
   code_target=base+'_seal'
  else:future=expr;code_target=base+'_seal'+suffix
  return f"begin {target} <= {expr}; {code_target} <= seal256(256'({W}'({future}))); end "
 s=re.sub(r'\b(\w+(?:\[[^\[\];\n]+\])?)\s*<=\s*([^;]+);',assignment,s)
 s=s.replace('assign rcd_z[b]', 'assign bank_protect[b]='+' || '.join(groups['bank'])+';\n      assign rcd_z[b]')
 s=s.replace('assign rrdl_z[g]', 'assign bg_protect[g]='+' || '.join(groups['bg'])+';\n      assign rrdl_z[g]')
 s=s.replace('wire faw_ok =', 'wire protection_bad=(|bank_protect) || (|bg_protect) || '+' || '.join(groups['top'])+';\n    wire faw_ok =')
 s='// Generated from52ce3 stream PC SHA256 '+origin+'\n// SECDED shadow bits per PC: '+str(shadow_bits)+'; live+shadow mismatch fails closed.\n'+s
 s="\n".join(line.rstrip() for line in s.splitlines())+"\n"
 return s,shadow_bits
if __name__=='__main__':
 text,bits=generate();p=ROOT/'rtl/hbm_accel/service/ot_hbm_accel_stream_pc.sv';p.write_text(text)
 print('coded_shadow_FF_bits_per_PC',bits)
