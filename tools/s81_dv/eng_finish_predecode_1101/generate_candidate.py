#!/usr/bin/env python3
"""Emit an explicit private candidate; never edits canonical RTL or recipes."""
from pathlib import Path
import argparse,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args()
s=a.source.read_text();assert hashlib.sha256(s.encode()).hexdigest()=='fcf117b4d9bea108d167f59c0cad567f518a4615401f59acf91e2f324350df02','wrong active-kit source'
start=s.index('module ot_s81dv_eng_finish #');end=s.index('endmodule',start)+len('endmodule');old=s[start:end];new=old
assert new.count('    wire [CW-1:0] wr_n;')==1
new=new.replace('    wire [CW-1:0] wr_n;','')
needle='wr_v && wr_n == t * NVP + n';assert new.count(needle)==2;new=new.replace(needle,'wr_v && wr_onehot[t * NVP + n]')
for oldexpr,newexpr,count in [('wr_v && wr_n == 2 * NVP + 1','wr_v && wr_onehot[2 * NVP + 1]',3),('wr_v && wr_n == NVP + 1','wr_v && wr_onehot[NVP + 1]',3),('wr_v && wr_n == 1 * 1','wr_v && wr_onehot[1]',1),('wr_v && wr_n == 1','wr_v && wr_onehot[1]',2)]:
 assert new.count(oldexpr)==count,(oldexpr,new.count(oldexpr));new=new.replace(oldexpr,newexpr)

ut=re.search(r'    ot_hdc_delay #\(\.W\(CW\), \.D\(LAV\)\) u_t .*?;',new).group()
block='''    // Private source-bound six-edge write predecode: t_q capture is retained.
    wire [NC-1:0] wr_early, wr_onehot;
    genvar wt, wn;
    generate for (wt=0; wt<T; wt=wt+1) begin : g_predecode_tree
        for (wn=0; wn<NVP; wn=wn+1) begin : g_predecode_node
            if (wn>=1 && isadd(wn)) begin : g_live
                assign wr_early[wt*NVP+wn] = (t_q == wt*NVP+wn);
            end else begin : g_dead
                assign wr_early[wt*NVP+wn] = 1'b0;
            end
        end
    end endgenerate
    wire [NC-1:0] wr_early_bound = wr_early MUTATION;
    ot_hdc_delay #(.W(NC), .D(LAV)) u_wr_onehot (.clk(clk), .rst_n(rstn), .d(wr_early_bound), .q(wr_onehot));'''
block=block.replace('MUTATION',"^ {{(NC-2){1'b0}},2'b10}" if a.mutant else '')
new=new.replace(ut,block);assert not re.search(r'\bwr_n\b',new)
header=lambda t:t[:t.index('    localparam integer T')]
assert header(old)==header(new),'public contract changed'
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(s[:start]+new+s[end:])
a.out.with_suffix('.binding.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(s.encode()).hexdigest(),candidate_file_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),candidate_module_sha256=hashlib.sha256(new.encode()).hexdigest(),changed_module='ot_s81dv_eng_finish',mutant=a.mutant,public_header_unchanged=True,retained_t_q_capture=True,delay_edges='same LAV=6',changed_write_sites=11,production_edits=False),indent=2)+'\n')
