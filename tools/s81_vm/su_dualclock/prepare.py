#!/usr/bin/env python3
"""Freeze the real 128-SRAM VM plus the real 112-root SU bridge for a phase probe.
Preparation only. Builds/simulation belong on a resource-admitted remote host.
The expected S+15 response is a hypothesis until the actual DUT gate passes.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D
VM='4305ce06f'
BRIDGE='3cfd4a1c2'
BRIDGE_PATH='rtl/dsrom_sys/s81_suhc/hier/generated/canonical/ot_s81_su_vm_static_bridge.sv'
def blob(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'src';src.mkdir()
 receipt=json.loads(blob('3a6025831','results/rtl/s81_vm_native_integration_1015/receipt.json'))
 hashes={};paths={}
 for p,h in receipt['source_bound_files'].items():
  if p.endswith(('.sv','.v')):
   data=blob(VM,p);assert hashlib.sha256(data).hexdigest()==h;name=Path(p).name;(src/name).write_bytes(data);hashes[name]=h;paths[name]={'commit':VM,'path':p}
 data=blob(BRIDGE,BRIDGE_PATH);assert hashlib.sha256(data).hexdigest()=='637cfaf0524e12ede9234e6225105d7ec0dd9b7026f85997c1d3f45c09fbf54a';(src/Path(BRIDGE_PATH).name).write_bytes(data);hashes[Path(BRIDGE_PATH).name]=hashlib.sha256(data).hexdigest();paths[Path(BRIDGE_PATH).name]={'commit':BRIDGE,'path':BRIDGE_PATH}
 mod=D.parse_modules(D.preprocess((src/'dsfd_sp_vm_static.sv').read_text(),{}),'vm')[0];env=mod.env();cons=[]
 fun={'f_su_rqv':'tv','f_su_rq':'tr','t_su_rsv':'rv','t_su_rs':'rd','f_su_wqv':'wv','f_su_wq':'wr','f_su_wqm':'wm','f_su_wqd':'wd','c_st':'c_st'}
 for p,(direction,_) in mod.ports.items():
  if p in fun:cons.append(f'.{p}({fun[p]})')
  elif direction=='input':
   w=mod.width(p,env)
   if p=='cks' or p.startswith('ck_'):value='s_ck' if p.endswith('_s') else 't_ck';expr=value if w==1 else '{'+str(w)+'{'+value+'}}'
   elif p=='rss' or p.startswith(('rss_','rst_')):expr='rst_n' if w==1 else '{'+str(w)+'{rst_n}}'
   else:expr=f"{w}'d0"
   cons.append(f'.{p}({expr})')
 vm='dsfd_sp_vm #(.READ_PIPE(1),.CAP_PIPE(1)) dut ('+',\n'.join(cons)+');\n'
 bmod=D.parse_modules(data.decode(),BRIDGE_PATH)[0];benv=bmod.env();bcons=[]
 bf={'s_rq_v':'sv','s_rq_row':'sr','s_rs_v':'sov','s_rs_data':'sod','s_wq_v':'swv','s_wq_row':'swr','s_wq_mask':'swm','s_wq_data':'swd','t_rq_v':'tv','t_rq_row':'tr','t_rs_v':'rv','t_rs_data':'rd','t_wq_v':'wv','t_wq_row':'wr','t_wq_mask':'wm','t_wq_data':'wd','req_fault':'req_fault','rsp_fault':'rsp_fault','wr_fault':'wr_fault','fault':'bridge_fault'}
 for p,(direction,_) in bmod.ports.items():
  if p in bf:expr=bf[p]
  elif p.startswith('ck_'):expr='{16{s_ck}}' if p.endswith('_s') else '{16{t_ck}}'
  elif p.startswith('rst_'):expr='{16{rst_n}}'
  else:raise ValueError(p)
  bcons.append(f'.{p}({expr})')
 bridge='ot_s81_su_vm_static_bridge bridge ('+',\n'.join(bcons)+');\n'
 template=(Path(__file__).parent/'tb.sv.in').read_text();tb=template.replace('@VM_INSTANCE@',vm).replace('@BRIDGE_INSTANCE@',bridge)
 # Actual macro write-enable observations, all 128 real SRAM instances.
 mon=''
 for s in range(4):
  for b in range(32):
   path=f'dut.u_core.u_mem.slice[{s}].u_slice.bank[{b}].u_bank'
   mon+=f'if({path}.u_sram.w_ce_in)macro_writes=macro_writes+1;\n'
 mon+='''if(dut.u_core.u_mem.slice[0].u_slice.bank[0].u_bank.u_sram.w_ce_in && write_trace<3)begin
 $display("RAW_W_CE T%0d rowaddr%0d",tk,dut.u_core.u_mem.slice[0].u_slice.bank[0].u_bank.waq);write_trace=write_trace+1;end
if(dut.u_core.u_mem.slice[0].u_slice.bank[0].u_bank.u_sram.r_ce_in && read_trace<3)begin
 $display("RAW_R_CE T%0d rowaddr%0d",tk,dut.u_core.u_mem.slice[0].u_slice.bank[0].u_bank.raq);read_trace=read_trace+1;end
'''
 tb=tb.replace('@MACRO_MONITOR@',mon);(src/'tb_su_vm_dualclock.sv').write_text(tb)
 hashes['tb_su_vm_dualclock.sv']=hashlib.sha256(tb.encode()).hexdigest()
 (a.out/'manifest.json').write_text(json.dumps({'schema':'opentallas.s81.su-vm-dualclock-probe.v1','VM':VM,'bridge':BRIDGE,'source_hashes':hashes,'source_paths':paths,'qualification':'PREPARED_ONLY_NO_BUILD_OR_SIMULATION','expected_serial_read_latency':15,'expected_VM_stream_read_latency':13,'actual_VM_SRAMs':128,'clock_pins':{'VM':682,'bridge':112,'combined':794},'raw_reset_pins':{'VM':618,'bridge':112,'combined':730},'nominal_period_ps':{'stream':[2500,3],'serial':[10000,9]},'simulation_period_ps':{'stream':833.334,'serial':1111.112},'clock_note':'exact 3:4 ratio; periods quantized by 0.0008ppm on 1fs time grid; first postreset edges define common epoch0','physical_native_qualified':False,'canonical_programme_qualified':False},indent=2)+'\n')
 (a.out/'gate.sh').write_bytes((Path(__file__).parent/'gate.sh').read_bytes())
 print(a.out)
if __name__=='__main__':main()
