#!/usr/bin/env python3
"""Replace the 64 exact full-width BF16 two-add rounding cones, no cycle change."""
import argparse,pathlib,re,json

def rewrite(text,function):
    lines=text.splitlines(keepends=True);count=0;mapping=[]
    for i,line in enumerate(lines):
        m=re.fullmatch(r"(  assign (.+) = )u_core_u_engine_drain_data\[(\d+):(\d+)\] \+ 32'd32767;\n",line)
        if not m:continue
        hi,lo=int(m[3]),int(m[4]);assert hi-lo==31
        expected=f"  assign "
        n=re.fullmatch(r"(  assign .+ = )"+re.escape(m[2])+r" \+ \{ 31'h00000000, u_core_u_engine_drain_data\[(\d+)\] \};\n",lines[i+1])
        assert n and int(n[2])==lo+16,(i+1,lines[i+1][:100])
        lines[i+1]=n[1]+f"ot_rest_round32(u_core_u_engine_drain_data[{hi}:{lo}]);\n"
        mapping.append({'line':i+2,'slice':[hi,lo]});count+=1
    assert count==64,count
    # The first module is the generated leaf; the second wrapper is preserved.
    text=''.join(lines);end=text.index('endmodule');text=text[:end]+function+'\n'+text[end:]
    return text,{'full_width_round_cones':count,'PIN_CYCLES':0,'mapping':mapping}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);p.add_argument('--function',type=pathlib.Path,default=pathlib.Path(__file__).with_name('round32_function.svh'));a=p.parse_args()
    s,r=rewrite(a.source.read_text(),a.function.read_text());a.out.write_text(s);a.out.with_suffix('.round.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
