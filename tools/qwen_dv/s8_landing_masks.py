#!/usr/bin/env python3
"""Persistent S8 write-conditioned shared flag gates; no new state or edge."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]

def module(text,name):
    a=text.index('module '+name+' #(');b=text.index('endmodule',a)+len('endmodule')
    return text[a:b]

def helpers(prefix):
    src=(ROOT/'rtl/common/landed_parent/ot_pl_land_n32.sv').read_text()
    local=module(src,'ot_pl_land_n32_local_w')
    local=local.replace('ot_pl_land_n32_local_w',prefix+'_local_w',1)
    local=local.replace('parameter integer W = 24, D = 4,','parameter integer W = 24, D = 4, FW=2, FLO=16,')
    local=local.replace('    input wire [W-1:0] i,','    input wire [W-1:0] i,\n    input wire [D*FW-1:0] masked,\n    output wire [D-1:0] flags_oh,',1)
    anchor='    always @(posedge ck)\n        if (!rq) valid <= 0;'
    assert anchor in local
    local=local.replace(anchor,'    assign flags_oh=oh[(FLO/GB)*D+:D];\n'+anchor,1)
    old='            always @(posedge ck) if (oh[g*D + s]) dq <= i[LO +: GW];'
    new='''            wire [GW-1:0] slot_i;
            for(genvar h=0;h<GW;h=h+1)begin:g_input
                if(LO+h>=FLO && LO+h<FLO+FW)begin:g_masked
                    assign slot_i[h]=masked[s*FW+LO+h-FLO];
                end else begin:g_original
                    assign slot_i[h]=i[LO+h];
                end
            end
            always @(posedge ck) if (oh[g*D + s]) dq <= slot_i;'''
    assert local.count(old)==1;local=local.replace(old,new)
    chunk=module(src,'ot_pl_land_n32_chunk_w')
    chunk=chunk.replace('ot_pl_land_n32_chunk_w',prefix+'_chunk_w',1)
    chunk=chunk.replace('parameter integer W = 514, D = 4, CHUNK_BITS = 24,','parameter integer W = 514, D = 4, CHUNK_BITS = 24, FW=2, FLO=64,')
    chunk=chunk.replace('    input wire [W-1:0] i,','    input wire [W-1:0] i,\n    input wire [D*FW-1:0] masked,\n    output wire [D-1:0] flags_oh,',1)
    a=chunk.index('        (* keep_hierarchy = "yes" *) ot_pl_land_n32_local_w')
    b=chunk.index('        for (s = 0;',a)
    original=chunk[a:b]
    target=original.replace('ot_pl_land_n32_local_w',prefix+'_local_w').replace('.D(D))','.D(D),.FW(FW),.FLO(FLO-c*CHUNK_BITS))').replace('.i(i[c*CHUNK_BITS +: CW]),','.i(i[c*CHUNK_BITS +: CW]), .masked(masked), .flags_oh(flags_oh),')
    chunk=chunk[:a]+'        if(c==FLO/CHUNK_BITS)begin:g_mask_target\n'+target+'        end else begin:g_unchanged\n'+original+'        end\n'+chunk[b:]
    cell=f'''(* keep_hierarchy="yes" *) module {prefix}_gate #(parameter integer FW=2,ID=0)(
 input wire [FW-1:0] i,input wire a,b,c,output wire [FW-1:0] y);
 wire any_en=a|b|c;
 assign y=any_en ? i : {{FW{{1'b0}}}};
endmodule'''
    return '\n\n'+local+'\n\n'+chunk+'\n\n'+cell+'\n'

def transform(text):
    assert '_flags_mask_' not in text,'already transformed'
    top=re.search(r'module (\w+)\s*[#(]',text)[1];prefix=top+'_flags_mask'
    pattern=re.compile(r'    ot_pl_land_n32_chunk_w #[^\n]+ u_lpl_(\d+)_w [^\n]+;')
    groups={'rss':[],'rsn':[],'nb':[]}
    for m in pattern.finditer(text):
        line=m[0];inp=re.search(r'\.i\((\w+)\)',line)[1]
        hit=re.fullmatch(r'(rss|rsn|nb)_r(\d)',inp)
        if hit:
            depth=int(re.search(r'\.D\((\d+)\)',line)[1]);fam=hit[1]
            groups[fam].append(dict(number=m[1],region=int(hit[2]),line=line,D=depth))
    assert [len(groups[x]) for x in ['rss','rsn','nb']]==[7,8,8]
    code=['    // Shared real flag gates conditioned on the actual independent slot enables.']
    for fam,rows in groups.items():
        rows.sort(key=lambda r:r['region']);fw=2 if fam=='nb' else 4;flo=64 if fam=='nb' else 128
        depth=rows[0]['D'];assert all(r['D']==depth for r in rows)
        for r in rows:code.append(f"    wire [{depth-1}:0] flag_oh_{r['number']};")
        for group,start in enumerate(range(0,len(rows),3)):
            batch=rows[start:start+3];name=f'flag_mask_{fam}_{group}'
            code.append(f'    wire [{depth*fw-1}:0] {name};')
            src={'rss':'rs_s[1027:1026],rs_s[513:512]','rsn':'rs_n[1027:1026],rs_n[513:512]','nb':'l9_i[513:512]'}[fam]
            for slot in range(depth):
                enables=[f"flag_oh_{r['number']}[{slot}]" for r in batch]+["1'b0"]*(3-len(batch))
                code.append(f"    {prefix}_gate #(.FW({fw}),.ID({group*depth+slot})) u_fmask_{fam}_{group}_{slot} (.i({{{src}}}),.a({enables[0]}),.b({enables[1]}),.c({enables[2]}),.y({name}[{slot*fw}+:{fw}]));")
            for r in batch:
                line=r['line'];new=line.replace('ot_pl_land_n32_chunk_w',prefix+'_chunk_w',1).replace('.CHUNK_BITS(24))',f'.CHUNK_BITS(24),.FW({fw}),.FLO({flo}))',1)
                new=new.replace('.bank(',f".masked({name}), .flags_oh(flag_oh_{r['number']}), .bank(",1)
                assert text.count(line)==1;text=text.replace(line,new,1)
    anchor='    // ---- LANDING 0:'
    assert text.count(anchor)==1;text=text.replace(anchor,'\n'.join(code)+'\n'+anchor,1)
    return text+helpers(prefix)

def apply(path):
    path=Path(path);path.write_text(transform(path.read_text()))
if __name__=='__main__':
    import sys
    for name in sys.argv[1:]:apply(name)
