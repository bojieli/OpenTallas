#!/usr/bin/env python3
"""Exercise generated direct QX ROM loading on the actual bound element source.

This is an image identity gate, not a numeric or physical token qualification.
The four physical mask arrays are compared against the original emitted files
at every row; wrong-bank and wrong-bit controls must both fail.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import native_rom_bundle as B

RTL='''rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv
rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv
rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv
rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv
rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
rtl/proto/ot_fp32_add_rne_pipe.sv rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv
rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv
rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv rtl/v41rom/ot_v41_bterm5_w10.sv
rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv rtl/v41rom/ot_v41_segtree6.sv
physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v
physical/asap7_memory_macros_v2/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v'''.split()


def run(source, top, bundle, out):
    source,top,bundle,out=map(Path,(source,top,bundle,out))
    if out.exists():raise ValueError('preserve prior image identity evidence')
    manifest=json.loads((bundle/'manifest.json').read_text())
    binding=manifest['qx_bindings'][0]
    dut=binding['dut'];part,leaf=binding['bound_element'].split('.')
    prefix=f'{dut}.{part}.{leaf}'
    selected=[]
    qx=B.BoundQX(top);qx.banks(binding['bound_element'],binding['selector'])
    master=qx.cells[part][0];call=qx.partitions[master][leaf]
    body=(top.parent/(master+'.sv')).read_text()
    module=re.search(r'([A-Za-z_]\w*)\s*$',body[:call['insert']])[1]
    params={key:value[2] for key,value in call['params'].items()}
    params['INSTANCE']=json.dumps(binding['absolute_prefix'])
    parameter_text=', '.join('.'+key+'('+value+')' for key,value in params.items())
    tb='`timescale 1ps/1fs\nmodule actual_part;\n'+module+' #('+parameter_text+') '+leaf+''' (
.clk(1'b0),.rst_n(1'b0),.cfg_v(1'b0),.cfg_a(5'd0),.cfg_d(48'd0),.go(1'b0),.go_tag(2'd0),
.xs_v(1'b0),.xs_p(8'd0),.xs_b(3'd0),.xs_pos(3'd0),.xs_q0(256'd0),.xs_q1(256'd0),.xs_e0(10'd0),.xs_e1(10'd0));
endmodule
module actual_die; actual_part '''+part+''' (); endmodule
module tb; actual_die '''+dut+' ();\n'+'\n'.join(selected)+'\n'
    references=[];checks=[]
    for i,bank in enumerate(binding['banks']):
        original=manifest['images'][bank['image']]['source'];references.append(original)
        tb+=f'reg[2191:0] ref{i}[0:511];\n'
        checks.append(f'if({dut}.{bank["hierarchy"]}.arr[row] !== ref{i}[row]) errors=errors+1;')
    reference=references[0];absolute=str((bundle/(binding['selector']+'_0')).resolve())
    tb+='''reg ck=0,ce=0;reg[11:0]addr=0;always #416.5 ck=~ck;
wire[273:0] old_d,new_d,absolute_d;
'''
    tb+=f'ot_rom_4096x274_m8_reference #(.VIAMAP({json.dumps(reference)})) old_m(ck,ce,addr,old_d);\n'
    tb+=f'ot_rom_4096x274_m8 #(.VIAMAP({json.dumps(reference)})) new_m(ck,ce,addr,new_d);\n'
    tb+=f'ot_rom_4096x274_m8 #(.INSTANCE({json.dumps(absolute)})) absolute_m(ck,ce,addr,absolute_d);\n'
    tb+='integer errors=0;reg[273:0]previous=0;\ninitial begin\n'
    for i,file in enumerate(references):tb+=f'$readmemh({json.dumps(file)}, ref{i});\n'
    tb+='''#1;
if($test$plusargs("bad_bit")) ref0[37][13]=~ref0[37][13];
if($test$plusargs("bad_bank")) for(integer row=0;row<512;row=row+1) ref0[row]=ref1[row];
for(integer row=0;row<512;row=row+1)begin
'''+ '\n'.join(checks)+'''
end
for(integer step=0;step<256;step=step+1)begin
 @(negedge ck);ce=(step%7)!=0;addr=12'((step*1777+219)&4095);
 @(posedge ck);#1;
 if(new_d!==old_d||absolute_d!==old_d)errors=errors+1;
 if($test$plusargs("bad_age")&&absolute_d!==previous)errors=errors+1;
 previous=old_d;
end
$display("QX_DIRECT_ROM_LOAD %s rows=2048 banks=4 read_cycles=256 errors=%0d",errors==0?"PASS":"FAIL",errors);
if(errors)$fatal(1,"actual QX ROM selection differs from emitted masks");$finish;
end
endmodule
'''
    out.mkdir(parents=True)
    (out/'tb.sv').write_text(tb)
    overlay=manifest['rom_model_overlays'][B.QX_ROM]
    if B.digest(source/B.QX_ROM)!=overlay['original_sha256']:raise ValueError('the measured original ROM model changed')
    reference_model=(source/B.QX_ROM).read_text().replace('module ot_rom_4096x274_m8 #', 'module ot_rom_4096x274_m8_reference #')
    (out/'original_reference.v').write_text(reference_model)
    files=[str(bundle/overlay['overlay_file']) if p==B.QX_ROM else str(source/p) for p in RTL]
    with (out/'build.log').open('w') as log:
        subprocess.run(['verilator','--binary','--timing','-O1','-j','2','-Wno-fatal','-Wno-WIDTH','-Wno-PINMISSING',
                        '--top-module','tb','--Mdir',str(out/'obj'),*files,str(out/'original_reference.v'),str(out/'tb.sv')],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    codes={}
    for mode in ('base','bad_bit','bad_bank','bad_age'):
        with (out/(mode+'.log')).open('w') as log:
            codes[mode]=subprocess.run([str(out/'obj/Vtb')]+([] if mode=='base' else ['+'+mode]),
                                      stdout=log,stderr=subprocess.STDOUT).returncode
    good=codes['base']==0 and all(codes[m]!=0 for m in ('bad_bit','bad_bank','bad_age'))
    result=dict(status='PASS' if good else 'FAIL',scope='actual bound QX image loading only',
        bound_element=part+'.'+leaf,actual_module=module,actual_parameters=params,rows=2048,banks=4,
        read_cycles=256,default_and_absolute_read_lockstep=True,rom_model_overlay=overlay,
        source_sha256={p:B.digest(source/p) for p in RTL},reference_images={p:B.digest(p) for p in references},
        exit_codes=codes,production_enabled=False,added_cycles=0)
    (out/'check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'actual QX bank identity;',codes)
    return 0 if good else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--bound-top',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();raise SystemExit(run(a.source_root,a.bound_top,a.bundle,a.out))
