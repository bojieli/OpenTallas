#!/usr/bin/env python3
"""Create distinct native masters for the four remaining assigned-pin profiles.
Wrappers contain only named pin wires and compile-time BANK_BASE constants;
existing b5 primitive RTL is unchanged. Production adoption is a separate gate.
"""
import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D

def main():
 vm=R/'rtl/dsrom_sys/s81_ph/vm';dest=vm/'dsfd_vm_direct_write_native_profiles.sv';text=['`timescale 1ns/1ps','`default_nettype none','// Source-identical transparent native profile boundaries; no added FF/cycle.','// Production slice must select actual closed profile by assigned pins; no view aliases.']
 profiles=[]
 for tag,base in [('capture_w',None),('scatter_b8',8),('scatter_b16',16),('scatter_b24',24)]:
  primitive='dsfd_vm_static_write_capture128' if base is None else 'dsfd_vm_static_scatter_b8_out';top=primitive+('_W' if base is None else f'_B{base}')
  p=vm/(primitive+'.sv');m=D.parse_modules(p.read_text(),str(p))[0];env=m.env({});ports={n:(d,m.width(n,env)) for n,(d,_) in m.ports.items()}
  header=',\n'.join(f' {d} wire '+(f'[{w-1}:0] ' if w>1 else '')+n for n,(d,w) in ports.items())
  text+=['module '+top+'(\n'+header+'\n);',primitive+('' if base is None else f' #(.BANK_BASE({base}))')+' u_leaf (\n'+',\n'.join(f' .{n}({n})' for n in ports)+'\n);','endmodule']
  profiles.append(dict(tag=tag,top=top,primitive=primitive,bank_base=base,ports={n:dict(direction=d,width=w) for n,(d,w) in ports.items()},primitive_source=str(p.relative_to(R)),primitive_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 text+=['`default_nettype wire'];dest.write_text('\n'.join(text)+'\n')
 out=R/'physical/s81_vm_direct_write_native_1015';template=json.loads((out/'capture_e.json').read_text());scatter=json.loads((out/'scatter_b0.json').read_text())
 for p in profiles:
  spec=json.loads(json.dumps(template if p['bank_base'] is None else scatter));tag=p['tag'];spec['name']='dsfd_vm_direct_'+tag+'_native';spec['top']=p['top'];spec['sources']=[p['primitive_source'],'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_direct_write_native_profiles.sv'];
  # Every parsed wrapper needs the two actual primitive definitions for lint;
  # synthesis uses only the selected top and removes the unrelated modules.
  other='rtl/dsrom_sys/s81_ph/vm/'+('dsfd_vm_static_scatter_b8_out' if p['bank_base'] is None else 'dsfd_vm_static_write_capture128')+'.sv';spec['sources'].append(other)
  spec['params']={};spec['io_tcl']='physical/s81_die_pins/v20_vm_direct_write/'+('dsfd_vm_static_write_capture128_W' if p['bank_base'] is None else 'dsfd_vm_static_scatter_b8_out')+'.tcl'
  assigned=json.loads((R/spec['io_tcl']).with_suffix('.json').read_text());faces={f:[] for f in 'NSEW'}
  for port,entry in assigned['ports'].items():
   ff={bit[0] for bit in entry['per_bit']};assert len(ff)==1;faces[next(iter(ff))].append(port)
  spec['pins']=faces
  spec['job']['purpose']=f'Actual distinct native {tag} wrapper, exact assigned sourceport/pin map and constant BANK_BASE; not inheritedE/B0view. Primitiveb5unchanged; production parent binding stillrequiresproof.'
  spec['job']['benches']=[dict(name='exact_actual_'+tag,cmd=f'python3 tools/s81_vm_direct_write/profile_bench.py --profile {tag} --out {{RUN}}/bench/{tag}',expect='pass',pass_regex='PROFILE_WRITE_PASS records 8000',min_count_regex=r'records (\d+)',threads=1,peak_ram_gb=1,needs=['iverilog']),dict(name='mutant_actual_'+tag,cmd=f'python3 tools/s81_vm_direct_write/profile_bench.py --profile {tag} --mutant --out {{RUN}}/bench/{tag}_mut',expect='fail',fail_regex='PROFILE_WRITE_FAIL records 8000',min_count_regex=r'records (\d+)',threads=1,peak_ram_gb=1,needs=['iverilog'])]
  (out/(tag+'.json')).write_text(json.dumps(spec,indent=2)+'\n')
 (out/'remaining_profiles.json').write_text(json.dumps(dict(schema='opentallas.s81.vm-distinct-native-write-profiles.v1',status='ACTUAL_TRANSPARENT_SOURCE_WRAPPERS_NOT_NATIVE_CLOSURE_OR_PRODUCTION_ADOPTION',wrapper_source=str(dest.relative_to(R)),wrapper_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),profiles=profiles,assertion='Eachprimitiveinput/output/clock/resetconnectedoncebyname, nocomputation/state/controlinwrapper; constantBANK_BASEsourceidentity. Pin304variants retained exact. Existingproductionprimitivebytes unchanged.'),indent=2)+'\n')
 print('PROFILES_SOURCE_PASS captureW/scatterB8/B16/B24 distinctmasters,primitiveRTLunchanged')
if __name__=='__main__':main()
