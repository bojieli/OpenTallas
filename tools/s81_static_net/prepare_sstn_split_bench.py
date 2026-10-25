#!/usr/bin/env python3
"""Generate a full-port lockstep bench against the five actual monolithic x2 modules.

S81-KITS-RTLB 10-24: ot_s81_sstn_base566 lands its status inputs (e0 e1 c0 c1 si nf) in pin registers (owner rule:
register every pin, in RTL), so its `so` is the monolithic module's `so` one edge later.
S81-KITS-RTLC 10-24: base566 also lands cci / xai / xbi and payload536 lands x2i in pin registers (2 flops per bit, the
1-flop pass-through stations are gone), so EVERY output is the monolithic module's output one edge later.  The bench
models exactly that: the reference instance refd_<role> sees every input through bench-side landing registers whose
reset class mirrors the new input stage (column reset for cci, xai[282], the status inputs and x2i[0] / x2i[4];
reset-free for the data bits) and every output is checked against it.  The 5 monolithic x2 references are the ones of
commit 9233f6363 (not on main), kept beside this script in tools/s81_static_net/ref_x2/."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as B
ROLES=['e0c0','e0c0si','e0c0sinf','e0e1c0c1si','e0e1c0c1sinf']

def prepare(out):
    out.mkdir(parents=True,exist_ok=True)
    decl=['`timescale 1ns/1ps','module tb;reg ck=0,rs=1;integer n,j,checks=0;']
    insts=[];drives=[];checks=[];maps=[];sources=[]
    SP=('c0','c1','e0','e1','si','nf')       # status inputs: +1 landing edge in base566 (column reset)
    RST={'cci':None,'xai':{282},'x2i':{0,4}}  # reset-class bits of the data inputs (None = every bit)
    for role in ROLES:
        name='dsfd_sstn_'+role+'_x2';src=ROOT/'tools/s81_static_net/ref_x2'/f'{name}.sv'
        mod=B.parse_modules(src.read_text(),str(src))[0];sources.append(src)
        ref=[];refd=[];base=[];payload=[];straps={};nc=[]
        for pn,(direction,_) in mod.ports.items():
            w=mod.width(pn,mod.env({}));sig=role+'_'+pn
            if pn in ('ck','rs'):ref.append(f'.{pn}({pn})');refd.append(f'.{pn}({pn})');continue
            decl.append(f'{"reg" if direction=="input" else "wire"} [{w-1}:0] {sig};')
            ref.append(f'.{pn}({sig})')
            if direction=='input':
                drives.append(f'for(j=0;j<{w};j=j+1) {sig}[j]=$random;')
                # every input one landing edge later: da_ (column reset) / dn_ (reset-free) per bit as the DUT's stage
                decl.append(f'reg [{w-1}:0] da_{sig}; always @(posedge ck or negedge rs) if(!rs) da_{sig}<=0; else da_{sig}<={sig};')
                decl.append(f'reg [{w-1}:0] dn_{sig}; always @(posedge ck) dn_{sig}<={sig};')
                rb=set(range(w)) if (pn in SP or (pn in RST and RST[pn] is None)) else RST.get(pn,set())
                refd.append(f'.{pn}({{'+','.join((f'da_{sig}[{b}]' if b in rb else f'dn_{sig}[{b}]') for b in range(w-1,-1,-1))+'})')
            else:
                decl.append(f'wire [{w-1}:0] dut_{sig}; wire [{w-1}:0] refd_{sig};')
                refd.append(f'.{pn}(refd_{sig})')
                want=f'refd_{sig}'
                checks.append(f'if({want} !== dut_{sig}) begin $display("SSTN_SPLIT_MISMATCH {role}.{pn} cycle%0d got%h want%h",n,dut_{sig},{want});$fatal(1);end checks=checks+{w};')
        for pn in ['cci','xai','xbi','c0','c1','e0','e1','si','nf','cc','xa','xb','so']:
            if pn in mod.ports:
                direction=mod.ports[pn][0];expr=('dut_' if direction=='output' else '')+role+'_'+pn
            elif pn in ['c0','c1','e0','e1','si','nf']:
                expr="1'b0" if pn=='nf' else "2'b00";straps[pn]=expr
            else:
                expr='';nc.append(pn)
            base.append(f'.{pn}({expr})')
        insts += [f'{name} ref_{role} ('+', '.join(ref)+');',
                  f'{name} refd_{role} ('+', '.join(refd)+');',
                  f'ot_s81_sstn_base566 base_{role} (.ck(ck),.rs(rs),'+', '.join(base)+');',
                  f'ot_s81_sstn_payload536 payload_{role} (.ck(ck),.rs(rs),.i({role}_x2i),.o(dut_{role}_x2));']
        maps.append(dict(role=role,logical_parent=name,base='ot_s81_sstn_base566',payload='ot_s81_sstn_payload536',base_role_straps=straps,base_unused_outputs=nc,base_port_map={pn:('ck_base' if pn=='ck' else 'rs' if pn=='rs' else straps.get(pn,pn)) for pn in ['ck','rs','cci','xai','xbi','c0','c1','e0','e1','si','nf','cc','xa','xb','so']},payload_port_map=dict(ck='ck_payload',rs='rs',i='x2i',o='x2'),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
    test='\n'.join(decl+insts)+'''\ninitial begin
#1;rs=0;#1;
for(n=0;n<4000;n=n+1)begin
'''+ '\n'.join(drives)+'''\n#2;ck=1;#1;
'''+ '\n'.join(checks)+'''\n#2;ck=0;#1;
'''+ '\n'.join(checks)+'''\nif(n%137==0)begin rs=0;#1;
'''+ '\n'.join(checks)+'''\n#1;rs=1;#1;end
end
$display("SSTN_SPLIT_EXACT PASS five actual roles 4000 cycles both edges warm resets checked_bits=%0d",checks);$finish;end
endmodule
'''
    (out/'tb.sv').write_text(test)
    (out/'sources.f').write_text('\n'.join(str(p) for p in sources+[ROOT/'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv',ROOT/'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv'])+'\n')
    contract=dict(schema='s81-sstn-two-leaf-map-v1',status='candidate_only_actual_parent_incident_and_clock_proof_open',parent_outline=[172.8,30.24],leaves=dict(base=dict(master='ot_s81_sstn_base566',origin=[0,0],outline=[84.24,30.24],clock='ck_base'),payload=dict(master='ot_s81_sstn_payload536',origin=[86.4,0],outline=[86.4,25.92],clock='ck_payload')),seam_um=2.16,clock_delivery='separate phi - R per child, same logical posedge calendar',production_edges=2,extra_production_edges=1,status_so_edges=2,status_note='every output = monolithic output one edge later (base566 status input pin registers S81-KITS-RTLB 10-24; cci / xai / xbi / x2i pin registers S81-KITS-RTLC 10-24)',async_reset='same immediate column reset for valid/control bits only',roles=maps)
    (out/'parent_map.json').write_text(json.dumps(contract,indent=1)+'\n')
    return contract

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('out');a=ap.parse_args();prepare(Path(a.out))
