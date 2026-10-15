#!/usr/bin/env python3
"""Native assigned-pin prototypes for actual two-stage static VM write path."""
import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D

def main():
 out=R/'physical/s81_vm_direct_write_native_1015';out.mkdir(exist_ok=True)
 for leaf,pin,params,profile in [('write_capture128','dsfd_vm_static_write_capture128_E',{},'capture_e'),('scatter_b8_out','dsfd_vm_static_scatter_b8_out',{'BANK_BASE':0},'scatter_b0')]:
  top='dsfd_vm_static_'+leaf;src=f'rtl/dsrom_sys/s81_ph/vm/{top}.sv';p=R/src
  assigned=json.loads((R/f'physical/s81_die_pins/v20_vm_direct_write/{pin}.json').read_text());assert assigned['source_sha256']==hashlib.sha256(p.read_bytes()).hexdigest(),top
  w,h=assigned['outline_um'];m=D.parse_modules(p.read_text(),str(p))[0];env=m.env(params)
  faces={f:[] for f in 'NSEW'}
  for n,(d,_) in m.ports.items():
   pp=assigned['ports'][n]['per_bit'];assert len(pp)==m.width(n,env),n
   ff={v[0] for v in pp};assert len(ff)==1,(n,ff)
   faces[next(iter(ff))].append(n)
  benches=[]
  kind='capture' if leaf.startswith('write') else 'scatter'
  for mode in [0,1,2]:benches.append(dict(name=f'exact_{kind}_mode{mode}',cmd=f'bash tools/s81_vm_direct_write/bench.sh {{RUN}}/bench/{kind}_m{mode} {kind} base {mode}',expect='pass',pass_regex=f'TB_VM_DIRECT_SCATTER PASS mode {mode} checks 1003',min_count_regex=r'checks (\d+)',threads=1,peak_ram_gb=1,needs=['iverilog']))
  benches.append(dict(name=f'mutant_actual_{kind}',cmd=f'bash tools/s81_vm_direct_write/bench.sh {{RUN}}/bench/{kind}_mut {kind} mutant 0',expect='fail',fail_regex='TB_VM_DIRECT_SCATTER FAIL mode 0 checks 1003 bad',min_count_regex=r'checks (\d+)',threads=1,peak_ram_gb=1,needs=['iverilog']))
  if kind=='scatter':benches.append(dict(name='mutant_actual_scatter_addr',cmd='bash tools/s81_vm_direct_write/bench.sh {RUN}/bench/scatter_addr scatter address 0',expect='fail',fail_regex='TB_VM_DIRECT_SCATTER FAIL mode 0 checks 1003 bad',min_count_regex=r'checks (\d+)',threads=1,peak_ram_gb=1,needs=['iverilog']))
  spec=dict(name=f'dsfd_vm_direct_{profile}_native',top=top,kind='tile',sources=[src],clock='cts',clock_port='ck',reset_ports=['rst_n'],outline=dict(w=w,h=h,exact=True),pins=faces,io_tcl=f'physical/s81_die_pins/v20_vm_direct_write/{pin}.tcl',params=params,layer_cap='M5',macros=[],route=dict(pd=.40,threads=4,peak_ram_gb=8,hold_margin_ns=.030,macro_halo_um=5.4),recipe=2,io_flop_at_pins=dict(cols=4,allow_none=True),inhold=True,outhold=True,keep_pin_regs=True,pin_reg_split=True,hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),structural_change='Hardening exact existing bank-local capture/output stages, fixed two-stage dataflow unchanged; no runtime scheduling or credit',slot_change_request=dict(contract='S81 static VM direct q8 native option',version='30421c7c5/a60002977/eaca93a88',why='Actual assigned pins/registered endpoint geometry; representativeE/B0 only, production parent nativephase/cut/calendar stillopen'),job=dict(owner='Codex:S_VM directwrite native',branch='codex/s81-direct-write-native-1015',tag='nativepin1',purpose=f'Actual {profile} nativeleaf only; physicalTTsetup/FFhold/DRC0/nativefaceIO and same2existingstages; othercaptureW/scatterB8/16/24 do notinheritthisview',extra_paths=['rtl/dsrom_sys/s81_ph/vm','rtl/dsrom_sys/s81_ph/test','tools/s81_vm_direct_write','physical/s81_die_pins/v20_vm_direct_write','physical/s81_vm_direct_write_native_1015'],benches=benches))
  (out/(profile+'.json')).write_text(json.dumps(spec,indent=2)+'\n')
  print(profile,top,w,h,sum(m.width(n,env) for n in m.ports))
if __name__=='__main__':main()
