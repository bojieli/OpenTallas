#!/usr/bin/env python3
"""Prepare (never compile) a native k79 ROOT arithmetic source fixture.

Uses the actual scalar leaf plus live calendar/native FDN/RP/CTL. PSUMs are
fixture inputs at the native reducer boundary. No SU, VM, HEAD producer or
production scheduling is replaced by a numerical stub.
"""
import argparse,hashlib,json,re,sys,shutil,collections
from pathlib import Path

TOP=r'''
`timescale 1ns/1fs
module native_root_component(input wire ck,rst_n,input wire[115:0]cmd_i,
 input wire red_we,input wire[23:0]red_addr,input wire[31:0]red_data,
 output wire[100:0]sc_cfg,output wire sc_busy,sc_fault,
 output wire w1_we,output wire[23:0]w1_addr,output wire[31:0]w1_data);
 wire[115:0]cmd_q,rp_cmd;wire[1037:0]chd_q,rp_chd;wire rp_fault;
 wire[47:0]scu_q,sc_dn,sc_up;wire[1094:0]own_ch;wire[9:0]ag_own;
 wire[106:0]st;wire[49:0]cc;wire pc_bad;
 wire[7:0]zero_vm=0;wire[3:0]sid;wire[28:0]stn_cfg;wire[30:0]stm_cfg;wire[9:0]su_cmd;
 wire am_v;wire[23:0]am_idx;wire[31:0]am_val;wire[1:0]am_u;
 wire sc_w1;wire[23:0]sc_addr;wire[31:0]sc_data;
 wire tok_v,tok_own;wire[23:0]tok_idx;wire[31:0]tok_val;wire[1:0]tok_user;
 qfd_dv_s8_fdn_arf1 u_fdn(.ck(ck),.rst_n(rst_n),.cmd_i(cmd_i),.hr_i('0),
 .st_up_i('0),.sc_up_i('0),.ch_dn_i('0),.treq_i('0),.cmd_q(cmd_q),.scu_q(scu_q),.chd_q(chd_q),
 .chu_ar_sel('0),.chu_dd_sel('0),.chu_q('0),.own_ch(own_ch),.pc_bad(pc_bad),
 .agu_q('0),.ag_own(ag_own),.st_dn_c('0),.sc_dn_c(sc_dn),.st_c(st),.cc_c(cc),.l9_i('0));
 qfd_dv_s8_rp1 u_rp(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_q),.chd_q(chd_q),
 .tw_we(1'b0),.tw_kind(2'd0),.tw_addr(24'd0),.tw_data('0),
 .ctl_cmd(rp_cmd),.ctl_chd(rp_chd),.fault(rp_fault));
 qfd_dv_s5_ctl_repair4_leaf u_ctl(.ck(ck),.rst_n(rst_n),.cmd_q(rp_cmd),.chd_q(rp_chd),
 .r_v(1'b0),.r_idx(8'd0),.r_last(1'b0),.r_d('0),.l9o_v(1'b0),.stn_fault(1'b0),
 .vm_we(8'd0),.vm_waddr('0),.vm_wdata('0),.kv_we(8'd0),.kv_waddr('0),.kv_wdata('0),
 .su_nr(1'b0),.su_idle(1'b1),.su_fault(1'b0),.su_prog(16'd0),.su_rows(16'd0),.vm_fault(1'b0),
 .red_we(red_we),.red_addr(red_addr),.red_data(red_data),
 .sc_w1_we(sc_w1),.sc_w1_addr(sc_addr),.sc_w1_data(sc_data),
 .tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),
 .sc_busy(sc_busy),.sc_fault(sc_fault),.stm_fault(1'b0),.tld_fault(1'b0),.hd_fault(1'b0),.pc_bad(pc_bad|rp_fault),
 .sid(sid),.stn_cfg(stn_cfg),.sc_cfg(sc_cfg),.stm_cfg(stm_cfg),.su_cmd(su_cmd),
 .am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),
 .w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.own_ch(own_ch),.ag_own(ag_own),.st(st),.cc_o(cc));
 qfd_dv_s5_sc2_leaf u_sc(.ck(ck),.rst_n(rst_n),.sc_cfg(sc_cfg),.dn_i(48'd0),.dn_o(sc_dn),.up_i(scu_q),.up_o(sc_up),
 .red_we(red_we),.red_addr(red_addr),.red_data(red_data),.vm_we(8'd0),.vm_win0(2'd0),.vm_wdata0(32'd0),
 .am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),
 .w1_we(sc_w1),.w1_addr(sc_addr),.w1_data(sc_data),.tok_v(tok_v),.tok_idx(tok_idx),
 .tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.busy(sc_busy),.fault(sc_fault));
endmodule
'''
TB=r'''
`timescale 1ns/1fs
module tb_native_root;
 reg ck=0;always #0.416500 ck=~ck;reg rst_n=0;
 reg[5:0]stage=1;reg pv=0,dv=0,cs=0;reg[9:0]pa=0;reg[2:0]da=0;reg[63:0]pd=0,dd=0;reg[1:0]cu=0;
 wire[115:0]cmd;wire cf,ready;wire[5:0]fc;wire[1:0]issued_user;
 reg red_we=0;reg[23:0]red_addr=0;reg[31:0]red_data=0;
 wire[100:0]cfg;wire busy,fault,we;wire[23:0]wa;wire[31:0]wd;
 integer active=-1,seen=0,configs=0,cyc=0,cfg_edge=-1,outputs=0,hazard=0,late=0,collect=0,inject=0,boot_seen=0;
 reg[31:0]psum[0:127],gold[0:3];integer u,j,x,guard;reg[115:0]root_cmd;reg[127:0]entry;
 qfd_dv_cmd_cal_mu #(.NU(4),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.TABLE_USER_RELOC(1),.BTAB_COMPACT(1),.UFOLD(1)) cal(
 .ck(ck),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.dw_v(dv),.dw_addr(da),.dw_data(dd),
 .start(cs),.stage(stage),.start_user(cu),.start_rng(1'b0),.start_first(10'd0),.start_cnt(10'd0),
 .cmd(cmd),.cmd_user(issued_user),.image_ready(ready),.fault(cf),.fault_code(fc));
 native_root_component dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.red_we(red_we),.red_addr(red_addr),.red_data(red_data),
 .sc_cfg(cfg),.sc_busy(busy),.sc_fault(fault),.w1_we(we),.w1_addr(wa),.w1_data(wd));
 function automatic[115:0] rc(input integer rx);
  rc=116'd7|(116'd1<<4)|(116'd32<<5)|(116'd384<<11)|(116'd1<<35)|
     (116'(rx)<<36)|(116'h358637bd<<60)|(116'd12<<92);
 endfunction
 task wrpw(input integer addr,input reg[63:0]data);
  begin pv=1;pa=10'(addr);pd=data;@(negedge ck);pv=0;end
 endtask
 task loadcal;
  begin
   for(x=0;x<1024;x=x+1)begin
    entry=0;
    if(x==0||x==1)entry=(128'd16<<116)|128'(rc(400));
    if(inject&&(x==2||x==3))entry=(128'(collect?24:96)<<116)|128'(rc(401));
    if(x==8||x==9)entry=(128'd16<<116)|128'd15;
    wrpw(x,(x%2)?entry[127:64]:entry[63:0]);
   end
   repeat(8)@(negedge ck);
   for(x=0;x<8;x=x+1)begin
    dv=1;da=3'(x);dd=0;
    if(x==0)dd=64'h43414c4400000005;
    if(x==1||x==4)dd=64'h0000000000040001;
    if(x==2)dd=inject?64'd2:64'd1;
    @(negedge ck);
   end
   dv=0;repeat(16)@(negedge ck);if(!ready||cf)$fatal(1,"ROOT_CAL_SEAL %b %b %h",ready,cf,fc);
  end
 endtask
 always @(negedge ck)if(rst_n)begin
  cyc=cyc+1;
  if(cmd[0]&&cmd[3:1]==7)begin
   if(cmd!==116'd15)$fatal(1,"ROOT_BOOT_SETID_WORD %h",cmd);
   boot_seen=boot_seen+1;$display("ROOT_AUTOBOOT_SETID cyc%0d",cyc);
  end
  if(cf)$fatal(1,"ROOT_CAL_FAULT %h",fc);
  if(fault)$fatal(1,"NATIVE_ROOT_FAULT active%0d busy%b hazard%0d",active,busy,hazard);
  if(cfg[100])begin
   if(active<0)$fatal(1,"ROOT_CFG_NO_OWNER");
   if(cfg[91:68]!==24'(384+4096*active))$fatal(1,"ROOT_SS_RELOCATION");
   if(cfg[66:43]!==24'(400+4096*active)&&!(inject&&cfg[66:43]===24'(401+4096*active)))$fatal(1,"ROOT_RX_RELOCATION");
   if(configs>0&&seen==0)begin hazard=hazard+1;$display("ROOT_CFG_DURING_LEASE cyc%0d active%0d busy%b",cyc,active,busy);end
   configs=configs+1;cfg_edge=cyc;
  end
  if(we)begin
   outputs=outputs+1;
   if(active<0||wa!==24'(400+4096*active))$fatal(1,"ROOT_OUTPUT_ADDRESS active%0d addr%h hazard%0d",active,wa,hazard);
   if(wd!==gold[active])$fatal(1,"ROOT_RSTD_BITS active%0d got%h expected%h hazard%0d",active,wd,gold[active],hazard);
   seen=seen+1;$display("NATIVE_ROOT_CASE user%0d bits%h cfg_to_write%0d",active,wd,cyc-cfg_edge);
  end
 end
 initial begin
  late=$test$plusargs("LATE_CFG");collect=$test$plusargs("COLLECT_CFG");inject=late||collect;$readmemh("psum.hex",psum);$readmemh("rstd.hex",gold);
  repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);loadcal();
  guard=0;while(boot_seen==0)begin @(negedge ck);guard=guard+1;if(guard>512)$fatal(1,"NO_ROOT_AUTOBOOT_SETID");end
  repeat(64)@(negedge ck); // actual autoBOOT SETID traverses native FDN/RP/CTL before arithmetic
  for(u=0;u<4;u=u+1)begin
   active=u;seen=0;configs=0;cu=2'(u);cs=1;@(negedge ck);cs=0;
   guard=0;while(configs==0)begin @(negedge ck);guard=guard+1;if(guard>512)$fatal(1,"NO_NATIVE_ROOT_CFG");end
   repeat(16)@(negedge ck);
   for(j=0;j<32;j=j+1)begin red_we=1;red_addr=24'hc00000|24'(j);red_data=psum[32*u+j];@(negedge ck);end
   red_we=0;guard=0;
   while(seen==0)begin @(negedge ck);guard=guard+1;if(guard>1024)$fatal(1,"NO_NATIVE_RSTD active%0d busy%b hazard%0d",u,busy,hazard);end
   repeat(32)@(negedge ck);if(busy||seen!=1)$fatal(1,"NATIVE_ROOT_LEASE_DRAIN");
  end
  if(inject)$fatal(1,"CFG_LEASE_CONTROL_NOT_CAUGHT");
  if(outputs!=4||hazard)$fatal(1,"NATIVE_ROOT_CASE_COUNT");
  $display("NATIVE_ROOT_FOUR_CASES_PASS outputs%0d",outputs);$finish;
 end
endmodule
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--baseline-portable',type=Path,required=True)
 p.add_argument('--scalar-source',type=Path,required=True)
 p.add_argument('--golden-tools',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'.keep').touch();src=a.out/'src';src.mkdir()
 paths=[]
 for line in (a.baseline_portable/'source.f').read_text().splitlines():
  q=Path(line)
  if q.name not in ('50_native_su_component.sv','51_tb_mu_native.sv'):paths.append(q)
 paths += [a.scalar_source/n for n in ('qfd_dv_s5_sc2_leaf.sv','qfd_dv_s5_sc2_k79.sv','qfd_dv_s5_sc2_k79_helpers.sv')]
 modules={}; origins={}; timescales={}
 for path in paths:
  text=path.read_text()
  directives=[(m.start(),m.group().strip()) for m in re.finditer(r'(?m)^\s*`timescale[^\n]+',text)]
  for m in re.finditer(r'(?m)^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+(\w+)\b[\s\S]*?\bendmodule\b',text):
   name=re.search(r'\bmodule\s+(\w+)',m.group()).group(1)
   if name in modules and modules[name]!=m.group():raise ValueError('ambiguous module '+name)
   modules[name]=m.group();origins[name]=path
   timescales[name]=next((value for pos,value in reversed(directives) if pos<m.start()),'')
 modules['native_root_component']=TOP;modules['tb_native_root']=TB
 # Keep actual FDN/RP/CTL/scalar definitions; source-only dependency closure.
 pattern=re.compile(r'\b('+'|'.join(map(re.escape,sorted(modules,key=len,reverse=True)))+r')\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()')
 pending=['tb_native_root'];selected=set()
 while pending:
  name=pending.pop()
  if name in selected:continue
  selected.add(name);body=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',modules[name])
  pending.extend(x for x in pattern.findall(body) if x!=name and x not in selected)
 if 'qfd_dv_s5_sc2_k79' not in selected:raise ValueError('native scalar absent')
 if any(x in selected for x in ('qfd_dv_s8_flat','qfd_dv_scalar2','qfd_dv_head_safe1')):raise ValueError('nonminimal arithmetic substituted')
 files=[];receipt=[]
 for n in sorted(selected):
  path=src/(n+'.sv');path.write_text((timescales.get(n,'')+'\n' if timescales.get(n) else '')+modules[n]+'\n');files.append(path.resolve())
  o=origins.get(n);receipt.append(dict(module=n,bytes=path.stat().st_size,origin=str(o) if o else 'fixture adapter',origin_sha256=hashlib.sha256(o.read_bytes()).hexdigest() if o else None,module_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),original_timescale=timescales.get(n)))
 (a.out/'source.f').write_text(''.join(str(q)+'\n' for q in files))
 if (a.baseline_portable/'defines.f').exists():shutil.copy2(a.baseline_portable/'defines.f',a.out/'defines.f')
 # Golden checks the actual32-slot tree and fused scale/epsilon/3NR order.
 sys.path.insert(0,str(a.golden_tools));import hdc_golden as G;import numpy as np
 ps=[];gold=[];cases=[]
 for u in range(4):
  vals=np.array([64+32*u+4*(j%7) for j in range(32)],dtype=np.float32)
  tree=list(vals)
  while len(tree)>1:tree=[G.add(tree[j],tree[j+1]) for j in range(0,len(tree),2)]
  r=G.rsqrt(G.add(G.mul(tree[0],np.float32(2**-12)),np.float32(1e-6)))
  ps.extend(int(v) for v in G.bits(vals));gold.append(int(G.bits(r)))
  cases.append(dict(user=u,ss=384+4096*u,rx=400+4096*u,psum_external_indices=list(range(32)),total_bits=int(G.bits(tree[0])),rstd_bits=int(G.bits(r))))
 (a.out/'psum.hex').write_text(''.join(f'{v:08x}\n' for v in ps));(a.out/'rstd.hex').write_text(''.join(f'{v:08x}\n' for v in gold))
 primitive_counts=collections.Counter(re.findall(r'\b(qfd_s2_bmath_\w+)\s*(?:#|\\?\w+\s*\()',modules['qfd_dv_s5_sc2_k79']))
 packet=dict(status='PREP_ONLY_NOT_COMPILED',source_files=receipt,source_bytes=sum(x['bytes'] for x in receipt),selected_modules=len(selected),native_scalar='qfd_dv_s5_sc2_leaf -> qfd_dv_s5_sc2_k79',scalar_latencies=dict(LA=7,LM=9),clock_ps=833,global_timeprecision_fs=1,original_module_timescales_preserved=True,
 native_scalar_primitive_counts=dict(primitive_counts),native_scalar_primitive_instances=sum(primitive_counts.values()),
 native_scalar_FF_primitives=primitive_counts['qfd_s2_bmath_dff_p']+primitive_counts['qfd_s2_bmath_dff_pn0'],
 build_proposal=dict(hierarchical=False,output_split=10000,output_split_cfuncs=1000,compile_jobs=1,admission_ram_gb=None,qualification='source/codegen split proposal only; RAM not inferred from XA; no compile submitted'),
 defines_sha256=hashlib.sha256((a.out/'defines.f').read_bytes()).hexdigest() if (a.out/'defines.f').exists() else None,
 fixture='live calendar/native FDN/RP/CTL/native k79, fixture PSUM inputs, actual native writes checked',cases=cases,
 golden_sha256=hashlib.sha256((a.golden_tools/'hdc_golden.py').read_bytes()).hexdigest(),
 vectors_sha256={n:hashlib.sha256((a.out/n).read_bytes()).hexdigest() for n in ('psum.hex','rstd.hex')},
 hazard=['COLLECT_CFG clears shared partial slots before trig while busy may still be0','LATE_CFG changes RX while arithmetic busy; native source has no cfg&&busy fault guard'],
 startup='Observe actual live-calendar autoBOOT SETID0 with512-cycle watchdog, then64 native transport settling cycles; no redundant explicit stage0 start',
 lease='Begins at ROOT cfg/firstPSUM and ends only after fused publication/drain; busy0 during collection does not release slots',
 held=['syntax/elaboration/runtime gate','native result timing measurement','production ROOT leases/TREQ','HEAD normalized input/installation','physical/canonical adoption'])
 (a.out/'preparation.json').write_text(json.dumps(packet,indent=2)+'\n')
 print('NATIVE_ROOT_PREP',packet['selected_modules'],packet['source_bytes'],'NOT_COMPILED')
if __name__=='__main__':main()
