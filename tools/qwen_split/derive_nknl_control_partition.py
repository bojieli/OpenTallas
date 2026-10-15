from pathlib import Path
import re,json,hashlib
_orig_write=Path.write_text
def checked_write(p,*a,**kw):
 assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
 return _orig_write(p,*a,**kw)
Path.write_text=checked_write
root=Path.cwd();src=root/'rtl/qwen_sys/tile_parent_banked_20261015';out=root/'rtl/qwen_sys/nknl_control_partition_20261015';out.mkdir(exist_ok=True)
issue=(src/'ot_qwen_w12_issue_banked_v1.sv').read_text();mat=(src/'ot_qwen_w12_matvec_part_banked_v1.sv').read_text()
inst=re.search(r'    ot_qwen_w12_issue_banked_v1 #\(.*?\) u_issue \((.*?)\);',mat,re.S)
ports=re.findall(r'\.(\w+)\((\w+)\)',inst[1]);outputs=[(p,n) for p,n in ports if p.startswith('o_') or p in ['wrom_re','kv_re','wrom_addr']]
header=issue.split(');',1)[0];widths={}
for line in header.splitlines():
 if 'output' not in line:continue
 m=re.search(r'output\s+(?:reg|wire)\s*(\[[^\]]+\])?\s*(\w+)',line)
 if m:
  names=line[line.index(m[2]):].strip().rstrip(',').split(',')
  for n in names:widths[n.strip()]=m[1] or ''
# Scalar registers and buses are in the exact existing source order.
wexpr=[]
for p,n in outputs:
 w=widths[p]
 if not w:wexpr.append('1')
 else:
  a,b=w[1:-1].split(':');wexpr.append(f'(({a})-({b})+1)')
cw='+'.join(wexpr)
# Capture hierarchy owns the original IREG and TIDR registers and the unchanged issue loop.
param=issue.split(') (',1)[0].split('#(',1)[1]
param=param.rstrip()+', parameter integer IREG=1, TIDR=1, CAP_MUT=0\n'
cap='// Exact existing-edge descriptor, strap and FAST_ISSUE partition. No new data stage.\nmodule ot_qwen_nknl_control_capture_v1 #(\n'+param+') (\n input wire clk,rst_n,ib_go,\n input wire [3*NW+13*AW+13-1:0] ib, input wire [15:0] tile_id,\n output wire go_i, output wire [3*NW+13*AW+13-1:0] ib_i, output wire [15:0] tile_id_i,\n output wire ['+cw+'-1:0] ctl_bus\n);\n'
cap+='localparam integer IBW=3*NW+13*AW+13;\nreg go_q;reg [IBW-1:0] ib_q;\nalways @(posedge clk or negedge rst_n) if(!rst_n)go_q<=0;else go_q<=ib_go;\nalways @(posedge clk)ib_q<=ib;\nassign go_i=IREG?go_q:ib_go;assign ib_i=IREG?ib_q:ib;\ngenerate if(TIDR!=0)begin:g_tidr\n(* keep *)reg[15:0] tile_id_q;always @(posedge clk)tile_id_q<=tile_id;assign tile_id_i=tile_id_q;\nend else begin:g_tidn assign tile_id_i=tile_id;end endgenerate\n'
rom=(src/'ot_qwen_rom_tile_logic_banked_v1.sv').read_text()
decode=rom[rom.index('    wire [NW-1:0] b_nout'):rom.index('    wire              wrom_re;')]
cap+=decode
for p,n in outputs:cap+=f'wire {widths[p]} {n};\n'
# Use original issue parameters; G=TG forwarded at owner boundary.
cap+=inst[0].replace('.go(go)', '.go(go_i)')
for p,n in ports:
 if p.startswith('i_'):cap=cap.replace(f'.{p}({n})',f'.{p}(b_{p[2:]})')
cap+='\nassign ctl_bus={'+','.join(n for p,n in outputs)+'};\nendmodule\n'
# Negative control changes raw descriptor before original first capture; production CAP_MUT=0.
cap=cap.replace('ib_q<=ib;',"ib_q<=ib ^ ((CAP_MUT==2) ? ({{(IBW-1){1'b0}},1'b1} << (IBW-3*NW-1-AW)): {IBW{1'b0}});")
cap=cap.replace('assign go_i=IREG?go_q:ib_go;', 'assign go_i=(IREG && CAP_MUT!=1)?go_q:ib_go;')
(out/'ot_qwen_nknl_control_capture_v1.sv').write_text(cap)
mat=mat.replace('module ot_qwen_w12_matvec_part_banked_v1','module ot_qwen_w12_matvec_ctlpart_v1',1)
mat=mat.replace('    input wire [58*514-1:0] bank_q,','    input wire ['+cw+'-1:0] ctl_bus,\n    input wire [58*514-1:0] bank_q,',1)
mat=mat.replace(inst[0],'    assign {'+','.join(n for p,n in outputs)+'}=ctl_bus;')
(out/'ot_qwen_w12_matvec_ctlpart_v1.sv').write_text(mat)
for flavor,dirname in [('nk','tile_parent_banked_20261015'),('nl','tile_parent_nl_banked_20261015')]:
 name='ot_qwen_rom_tile_logic_'+('nl_' if flavor=='nl' else '')+'banked_v1'
 r=(root/'rtl/qwen_sys'/dirname/(name+'.sv')).read_text();r=r.replace('module '+name,'module ot_qwen_rom_tile_logic_'+flavor+'_ctlpart_v1',1)
 r=r.replace('    input  wire              clk,','    input wire clk_ctl,\n    input  wire              clk,',1)
 r=r.replace('    reg              go_q;\n    reg  [IBW-1:0]   ib_q;\n','')
 r=r.replace('    wire             go_i  = IREG ? go_q : ib_go;','    wire go_i;')
 r=r.replace('    wire [IBW-1:0]   ib_i  = IREG ? ib_q : ib;','    wire [IBW-1:0] ib_i;')
 r=re.sub(r'    always @\(posedge clk or negedge rst_n\) begin\s*if \(!rst_n\) go_q <= 1\'b0;\s*else go_q <= ib_go;\s*end\s*always @\(posedge clk\) begin ib_q <= ib; end','',r,count=1)
 r=re.sub(r'    generate if \(TIDR != 0\) begin : g_tidr.*?    end endgenerate', '',r,count=1,flags=re.S)
 ci='wire ['+cw.replace('G','TG')+'-1:0] ctl_bus;\n'
 ci+='ot_qwen_nknl_control_capture_v1 #(.W(W),.G(TG),.IL(IL),.AW(AW),.NW(NW),.GT(GT),.SMIN(SMIN),.KV_PREP(KV_PREP),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.TMUT(TMUT),.IREG(IREG),.TIDR(TIDR)) u_control(\n.clk(clk_ctl),.rst_n(rst_n),.ib_go(ib_go),.ib(ib),.tile_id(tile_id),.go_i(go_i),.ib_i(ib_i),.tile_id_i(tile_id_i),.ctl_bus(ctl_bus));\n'
 r=r.replace('    ot_qwen_w12_matvec_part_banked_v1 #(', '''initial if(IREG!=1 || TIDR!=1 || FAST_ISSUE!=1 || ISSUE_LEAF!=1) $fatal(1,"control partition requires registered descriptor/strap and FAST_ISSUE leaf");\n'''+ci+'    ot_qwen_w12_matvec_ctlpart_v1 #(',1)
 r=r.replace('        .bank_q(bank_q),.bank_d(bank_d_me)', '        .ctl_bus(ctl_bus),.bank_q(bank_q),.bank_d(bank_d_me)',1)
 (out/f'ot_qwen_rom_tile_logic_{flavor}_ctlpart_v1.sv').write_text(r)
 for version in ['v1','v2']:
  top=f'qfd_tile_{flavor}_banked_{version}';q=(root/'rtl/qwen_sys'/dirname/(top+'.sv')).read_text()
  q=q.replace('module '+top,'module '+f'qfd_tile_{flavor}_ctlpart_{version}',1)
  q=q.replace(' input wire ck,',' input wire ck_ctl,\n input wire ck,',1)
  q=q.replace(name, f'ot_qwen_rom_tile_logic_{flavor}_ctlpart_v1')
  # Original top has the logic's .clk(ck) binding exactly once.
  q=q.replace('.clk(ck),', '.clk_ctl(ck_ctl),.clk(ck),')
  (out/f'qfd_tile_{flavor}_ctlpart_{version}.sv').write_text(q)
(out/'manifest.json').write_text(json.dumps({'source_commit':'3fa539f2628da0e0a11d0b5412c7578cc0a9276b','existing_register_owners':['ib_q','go_q','g_tidr.tile_id_q','g_issue_leaf.u_issue'],'cycles_added':0,'independent_clock':'clk_ctl (related existing phase; physical crossing tests required)','control_bus_bits_expression':cw,'control_bus_source_ports':outputs,'qualification':'candidate generated source; no proof/physical qualification'},indent=2)+'\n')
print('control bundle',len(outputs),'source buses',cw)
