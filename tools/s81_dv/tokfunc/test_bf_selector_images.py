#!/usr/bin/env python3
"""Actual two-frame BF image namespace gate, not an arithmetic/mission gate."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MACRO = ROOT/'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
COL = ROOT/'rtl/v41rom/ot_v41_bf_col.sv'


def word(rows, address):
    row = rows[address//8]
    return sum(((row >> (bit*8+address%8)) & 1) << bit for bit in range(274))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--join',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();j=json.loads(a.join.read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    frames=('u_f_0L01','u_f_0L02')
    images=[r for r in j['images_join'] if r['frame'] in frames]
    columns=sorted({r['original_column'] for r in images});assert len(columns)==14 and len(images)==28
    image={(r['original_column'],r['bank']):r for r in images}
    rows={k:[int(v,16) for v in Path(r['source']).read_text().split()] for k,r in image.items()}
    assert all(len(v)==512 and all(r.bit_length()<=2192 for r in v) for v in rows.values())
    classes={}
    for frame in frames:
        ps=j['field_classes'][frame]['phases']
        classes[frame]={label:next(x for x in ps if (x['op'],x['rows'])==target)
                        for label,target in [('full',('attn.wo_a',6)),('tail',('attn.wo_a',5)),('router',('ffn.router',1))]}
    first=columns[0];other=next(c for c in columns if c.startswith(frames[1]+'.'))
    difference=next(x for x in range(4096) if word(rows[first,0],x)!=word(rows[other,0],x))
    addresses=sorted({0,1,7,8,63,511,1023,2047,4095,difference});NA=len(addresses)
    romdir=out/'rom';romdir.mkdir()
    for k,r in image.items():(romdir/(r['candidate_selector']+'.viamap.hex')).symlink_to(Path(r['source']).resolve())
    wanted=[]
    for column in columns:
        for bank in (0,1):wanted.extend(word(rows[column,bank],address) for address in addresses)
    (out/'wanted.hex').write_text(''.join(f'{v:069x}\n' for v in wanted))
    selector_args=[l.strip() for l in COL.read_text().splitlines() if '#(.INSTANCE(MB' in l][:2]
    assert len(selector_args)==2
    sv=['`timescale 1ps/1ps', 'module column #(parameter INSTANCE="", parameter integer MB=0)(input wire clk,input wire issue,input wire[12:0] counter,output wire[273:0] rd0,rd1);']
    for bank in (0,1):
        cond='!counter[0]' if not bank else 'counter[0]'
        sv.append(f'ot_rom_4096x274_m8 {selector_args[bank]} r{bank}(.clk(clk),.ce_in(issue&&{cond}),.addr_in(counter[12:1]),.rd_out(rd{bank}));')
    sv+=['endmodule',f'module tb;localparam NC={len(columns)},NA={NA};reg clk=0;always begin #416 clk=1;#417 clk=0;end',
         'reg issue=0;reg[12:0]counter=0;wire[273:0]d0[0:NC-1],d1[0:NC-1];reg[273:0]gold[0:NC*2*NA-1];',
         'integer i,c,b,n,errors=0;reg[11:0]addr[0:NA-1];reg[273:0]old0[0:NC-1],old1[0:NC-1];']
    for c,column in enumerate(columns):sv.append(f'column #(.INSTANCE("{column}"),.MB(0)) c{c}(clk,issue,counter,d0[{c}],d1[{c}]);')
    sv+=['initial begin $readmemh("wanted.hex",gold);']
    for i,address in enumerate(addresses):sv.append(f'addr[{i}]={address};')
    sv+=['for(i=0;i<NA;i=i+1)begin for(b=0;b<2;b=b+1)begin',
         '@(negedge clk);issue=1;counter={addr[i],1\'b0}+b;',
         'for(c=0;c<NC;c=c+1)begin old0[c]=d0[c];old1[c]=d1[c];end',
         '@(posedge clk);#1;',
         'for(c=0;c<NC;c=c+1)begin',
         'if((b?d1[c]:d0[c])!==gold[(c*2+b)*NA+i])begin errors=errors+1;$display("BF_IMAGE_MISMATCH c%0d bank%0d address%0d",c,b,addr[i]);end',
         'if(i>0 && (b?d0[c]:d1[c])!==(b?old0[c]:old1[c]))errors=errors+1;',
         'end end end',
         '$display("BF_IMAGE_RESULT columns%0d images%0d samples%0d errors%0d clock833",NC,NC*2,NC*2*NA,errors);',
         'if(errors)$fatal(1,"BF_IMAGE_SELECTOR_FAIL");$display("BF_IMAGE_SELECTOR_PASS");$finish;end endmodule']
    (out/'tb.sv').write_text('\n'.join(sv)+'\n')
    cmd=['verilator','--binary','--timing','-j','2','-Wno-fatal','-Wno-WIDTH','--top-module','tb','--Mdir',str(out/'obj'),str(MACRO),str(out/'tb.sv')]
    with (out/'build.log').open('w') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
    def run(name):
        with (out/(name+'.log')).open('w') as f:r=subprocess.run([str(out/'obj/Vtb'),'+OT_ROM_DIR='+str(romdir)],cwd=out,stdout=f,stderr=subprocess.STDOUT)
        return r.returncode
    assert run('positive')==0
    wrong=romdir/(image[first,0]['candidate_selector']+'.viamap.hex');original=wrong.readlink()
    try:
        wrong.unlink();wrong.symlink_to(Path(image[other,0]['source']).resolve())
        assert run('wrong_frame_mutant')!=0
    finally:
        wrong.unlink();wrong.symlink_to(original)
    result=dict(status='PASS_SELECTED_NATIVE_274_BIT_BF_IMAGE_NAMESPACE',frames=list(frames),columns=14,images=28,
                addresses=addresses,read_samples=28*NA,classes_present_in_source_fields=classes,MB=0,PP=1,
                actual_native_macro='ot_rom_4096x274_m8',native_selector_expressions=selector_args,
                wrong_frame_image_caught=True,arithmetic_or_reset_requalified=False,full_token=False,
                canonical_manifest_or_active_ROM_directory_changed=False)
    (out/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
