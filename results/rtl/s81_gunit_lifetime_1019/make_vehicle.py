from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
out=Path(__file__).resolve().parent
p=root/'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l5.sv'; s=p.read_text()
a=s.index('        // job select ranks:'); b=s.index('    end else begin : g_tbl_legacy',a)
body=s[a:b]
head='''`timescale 1ns/1ps
module vehicle(input clk,rst_n,input wv,input[9:0]wa,input[255:0]wd,input tj_set,tj_w,input launch,input cw_v,input[9:0]cw_a,output[767:0]bases,output[95:0]scales,output tbl_f,output reg fault);
`ifdef FIXED
localparam TABLE_LIFETIME_SAFE=1;
`else
localparam TABLE_LIFETIME_SAFE=0;
`endif
localparam NSET=2; wire[15:0]rr={16{rst_n}}; wire[2:0]ln_c={3{launch}}; genvar g;
'''
tail='''always @(posedge clk or negedge rst_n) if(!rst_n) fault<=0; else if(tbl_f) fault<=1;
endmodule
module dsdv_gunit_control_first(input clk,rst_n,d,output reg q); always @(posedge clk or negedge rst_n) if(!rst_n)q<=0;else q<=d; endmodule
'''
(out/'vehicle.sv').write_text(head+body+tail)
(out/'source.json').write_text(json.dumps({'source':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'table_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'baseline_commit':'d9ef2759827ab649e467ad5cb7e171f3e97c696f','baseline_source_sha256':'a5843756e6653d500250351589640a4c7a7a03a301699473911aa702e3c632a8','scope':'byte exact FANOUT_SAFE table branch; internal registered inputs; actual native macro; arithmetic excluded'},indent=2)+'\n')
