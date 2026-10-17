#!/usr/bin/env python3
"""Emit literal clock-port Q3H RTL from the exact collected CB fabric/top.

This is a structural source candidate. It does not assign physical clock pins or
claim native timing. Every active register bank gets its own declared clock; no
single-ck fallback exists. The original diagnostic CB module is untouched.
"""
import argparse,json,re
from pathlib import Path

def depth_of(d):
    m=re.fullmatch(r'MUT == \d+ \? \d+ : (\d+)',d.strip('()'))
    if m:d=m.group(1)
    if not d.isdigit():raise ValueError('nonconstant depth '+d)
    return int(d)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fabric',required=True);ap.add_argument('--top',required=True)
    ap.add_argument('--abi',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();abi=json.loads(Path(a.abi).read_text());entries=abi['entries']
    fs=Path(a.fabric).read_text();ts=Path(a.top).read_text();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    fab=[x for x in entries if x['role']!='hard_tile_clock'];tiles=[x for x in entries if x['role']=='hard_tile_clock']
    fs=fs.replace('module qfd_c_b16_fabric ', 'module qfd_c_b16_fabric_regional ',1)
    fs=fs.replace('    input  wire ck,','\n'.join('    input wire '+x['port']+',' for x in fab),1)
    # Input declaration's whitespace is source-bound; refuse a failed substitution.
    if re.search(r'input\s+wire\s+ck\s*[,\n]',fs):raise ValueError('fabric common ck remains')
    lines=[]
    for line in fs.splitlines():
        if '.ck(ck)' not in line:lines.append(line);continue
        m=re.search(r'qfd_q3h_run #\(\.W\((\d+)\), \.D\((.*?)\)\) (\w+) \(\.ck\(ck\)',line)
        if m:
            w,d,inst=m.groups();d=depth_of(d)
            clocks="{"+','.join(f'ck_f_{inst}_s{i}' for i in reversed(range(d)))+"}" if d else "1'b0"
            pat=re.escape(m.group(0))
            replacement=f'qfd_q3h_run_regional #(.W({w}), .D({d})) {inst} (.ck_stage({clocks})'
            line=re.sub(pat,lambda _:replacement,line,count=1)
        else:
            m=re.search(r'\b(\w+) \(\.ck\(ck\)',line)
            if not m:raise ValueError('unowned clock '+line)
            line=line.replace('.ck(ck)',f'.ck(ck_f_{m.group(1)})',1)
        lines.append(line)
    fs='\n'.join(lines)+'\n'
    if '.ck(ck)' in fs:raise ValueError('common clock sink remains')
    fs=fs.replace('    input  wire ck,','')
    fs=fs.replace('endmodule','''    // The physical baseline fixes all run depths at MUT=0. Swap-leaf MUT2 is
    // retained; use the regional-clock bench for stopped-clock mutants.
    initial if (MUT != 0 && MUT != 2) $fatal(1,"regional fabric supports physical baseline or swap-leaf mutant only");
endmodule''',1)
    ts=ts.replace('module qfd_c_b16 (','module qfd_c_b16_regional (',1)
    ts=ts.replace('    input  wire ck,','\n'.join('    input wire '+x['port']+',' for x in entries),1)
    if re.search(r'input\s+wire\s+ck\s*[,\n]',ts):raise ValueError('top common ck remains')
    ts=ts.replace('qfd_c_b16_fabric u_fab (\n        .ck(ck),',
        'qfd_c_b16_fabric_regional u_fab (\n'+''.join(f"        .{x['port']}({x['port']}),\n" for x in fab).rstrip('\n'))
    # Rewrite each literal hard child block, preserving all existing data and strap wiring.
    for c in range(4):
        for r in range(4):
            start=ts.index(' u_t_'+str(c)+'_'+str(r)+' (')
            end=ts.index(');',start)
            block=ts[start:end]
            owned=[x for x in tiles if x['owner'].startswith(f'u_t_{c}_{r}.')]
            for x in owned:
                port=x['owner'].split('.')[-1]
                if port in ('ck_rse','ck_rne'):continue
                old='.'+port+'(ck)';new='.'+port+'('+x['port']+')'
                if old not in block:raise ValueError(f'missing literal child clock {c}/{r}/{port}')
                block=block.replace(old,new)
            block+=',\n        '+''.join(f".{p}(ck_t{c}_{r}_{p}), " for p in ['ck_rse','ck_rne']).rstrip(', ')
            ts=ts[:start]+block+ts[end:]
    if re.search(r'\.ck\w*\(ck\)',ts):raise ValueError('top still ties clocks together')
    # Simulation parameters: hard views fix GLUE_HARD=1; no parameter applied to synthesis blackboxes.
    ts=re.sub(r'(qfd_tile_n[kl]_rp2_romleaf) (u_t_\d_\d)',r'\1\n`ifndef SYNTHESIS\n #(.GLUE_HARD(1))\n`endif\n \2',ts)
    ts=ts.replace("// Every tile clock entry is driven by the cluster's regional root ck (the cluster CTS balances to each entry).","// Every tile clock entry has its own literal input; physical clock sites/insertion remain unmeasured.")
    (out/'qfd_c_b16_regional.sv').write_text(ts)
    (out/'qfd_c_b16_fabric_regional.sv').write_text(fs)
    (out/'qfd_q3h_run_regional.sv').write_text('''`timescale 1ns/1ps
module qfd_q3h_run_regional #(parameter integer W=514,parameter integer D=1)(
 input wire [((D>0)?D:1)-1:0] ck_stage,
 input wire [W-1:0] d, output wire [W-1:0] q);
 generate if(D==0)begin:g_wire assign q=d;end
 else begin:g_run
   wire [W-1:0] s[0:D];assign s[0]=d;
   for(genvar i=0;i<D;i=i+1)begin:g_s
     qfd_q3h_stn #(.W(W),.N(1)) u_s(.ck(ck_stage[i]),.d(s[i]),.q(s[i+1]));
   end
   assign q=s[D];
 end endgenerate
endmodule
''')
    print('REGIONAL_CLUSTER_SOURCE_EMITTED',len(entries),'literal clocks; no physical timing claim')
if __name__=='__main__':main()
