from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[3]
files=[x.removeprefix('/work/') for x in re.search(r'VERILOG_FILES = (.*)',(R/'tools/s81_dv/rtlgap_sukv_1021/pool_census.mk').read_text())[1].split()]
texts={p:(R/p).read_text() for p in files}
mods={n for t in texts.values() for n in re.findall(r'\bmodule\s+(\w+)',t)}
for variant,chunk in [('main',8),('alternate',4)]:
 out=R/f'rtl/dsrom_sys/s81_dv/slice/pool_native_{variant}.sv'
 parts=[]
 for p,t in texts.items():
  # Keep actual sequential owners before optimization. No mapped netlist input.
  t=re.sub(r'(?<!\w)reg\b', '(* keep *) reg',t)
  t=t.replace('output (* keep *) reg','(* keep *) output reg')
  if p.endswith('ot_s81sl_cmp_pool.sv'):
   split=t.index('// One feature lane.')
   top,lane=t[:split],t[split:]
   old="""(* keep *) reg rr0, rr1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rn = rr1;"""
   assert old in top and old in lane
   top=top.replace(old,"wire [3:0] reset_leaf;\n    ot_pool_reset_tree #(.N(4),.ID(0)) u_reset(clk,rst_n,reset_leaf);\n    wire rn = reset_leaf[0];")
   start=top.index('    always @(posedge clk or negedge rn) begin')
   end=top.index('\nendmodule',start)
   blk=top[start:end]
   groups=[{'busy','done','fault','x_rv','x_wv','issuing','fin','l_v','ie'},{'age','nout'},{'sb0','sb1'},{'sob','tw','tr','tn'}]
   result=[]
   for g,names in enumerate(groups):
    b=blk.replace('negedge rn',f'negedge reset_leaf[{g}]').replace('if (!rn)',f'if (!reset_leaf[{g}])')
    b=re.sub(r'\b(\w+)\s*<=\s*[^;]*;',lambda m:m[0] if m[1] in names else ';',b)
    result.append(b)
   top=top[:start]+'\n'.join(result)+top[end:]
   lane=lane.replace(old,"wire [10:0] reset_leaf;\n    ot_pool_reset_tree #(.N(11),.ID(1)) u_reset(clk,rst_n,reset_leaf);\n    wire rn = reset_leaf[0];")
   # Each arithmetic child owns its same-age reset leaf.
   j=1
   def reset(m):
    global j
    v=f'.rst_n(reset_leaf[{j}])';j+=1;return v
   lane=re.sub(r'\.rst_n\(rn\)',reset,lane)
   # Positional arithmetic calls also own private leaves; keep count bounded.
   def posreset(m):
    global j
    v=f'(clk, reset_leaf[{j}],';j+=1;return v
   lane=re.sub(r'\(clk, rn,',posreset,lane)
   # There are more than ten children; set exact declared leaf count.
   lane=lane.replace('[10:0] reset_leaf',f'[{j-1}:0] reset_leaf').replace('.N(11)',f'.N({j})')
   # Turn every wide held payload into byte-owned registers. Each control
   # drives a handful of helper inputs; no registered edge is added.
   repls=[('s0','sc0','d_q'),('s0h','sc1','s0'),('s1h','sc1','d_q'),('mx','sc1','((MUT != 4 && gt(d_q, s0)) ? d_q : s0)'),('e0h','ev && !ev_d','ey'),('denh','dvd[LA]','den'),('p0h','pv && !pv_d','py'),('p1h','pv && pv_d','py'),('m0h','mvd[LM] && !mvd_d','my'),('o_y','yvd[LA]','((MUT == 3) ? {yy[31:16],16\'d0} : bf16(yy))'),('o_y32','yvd[LA]','yy')]
   for num,(name,en,data) in enumerate(repls):
    # Delete exactly this sequential assignment; leave surrounding if/begin grammar.
    pat=rf'\b{re.escape(name)}\s*<=\s*[^;]*;'
    lane,n=re.subn(pat,';',lane)
    assert n==1,(name,n)
    # Existing declaration becomes a wire; output ports require wire too.
    if name.startswith('o_'):
     lane=lane.replace('(* keep *) output reg  [31:0] '+name,'output wire [31:0] '+name)
    else:
     # Split comma declarations first.
     lane=re.sub(r'\(\* keep \*\) reg \[31:0\] ([^;]+);',lambda m:' '.join(('wire' if x.strip()==name else '(* keep *) reg')+' [31:0] '+x.strip()+';' for x in m[1].split(',')),lane)
    ins=f'\n    wire [31:0] hold_d_{num} = {data};\n    for (genvar z{num}=0;z{num}<4;z{num}=z{num}+1) begin:g_hold_{name}\n      ot_pool_hold #(.ID({num}*4+z{num})) u_h(clk,({en}),hold_d_{num}[8*z{num}+:8],{name}[8*z{num}+:8]);\n    end\n'
    lane=lane.replace('\nendmodule',ins+'\nendmodule',1)
   muxes=[('sa','av','s0h','s1h'),('dsel','dvd[LA]','den','denh'),('mb','kv0','((MUT == 2) ? p1h : p0h)','((MUT == 2) ? p0h : p1h)')]
   for num,(name,en,a,b) in enumerate(muxes):
    lane,n=re.subn(r'wire \[31:0\] '+name+r' = [^;]*;',f'wire [31:0] {name};',lane)
    assert n==1,(name,n)
    ins=f"\n    wire[31:0] mux_a_{num}={a}, mux_b_{num}={b};\n    for(genvar m{num}=0;m{num}<4;m{num}=m{num}+1) begin:g_mux_{name}\n      ot_pool_mux #(.ID({num}*4+m{num})) u_m(({en}),mux_a_{num}[8*m{num}+:8],mux_b_{num}[8*m{num}+:8],{name}[8*m{num}+:8]);\n    end\n"
    lane=lane.replace('\nendmodule',ins+'\nendmodule',1)
   t=top+lane
  elif p.endswith('ot_hdc_fp32_f12.sv'):
   # Payload is unreset; valid is still reset. No arithmetic output edge moves.
   for v in ['u_v','o_v']:
    old=f"always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end\n        else begin\n            valid_out <= {v};"
    new=f"always @(posedge clk or negedge rst_n) if (!rst_n) valid_out <= 1'b0; else valid_out <= {v};\n    always @(posedge clk) begin\n        begin"
    assert old in t,v;t=t.replace(old,new)
  elif p.endswith('ot_hdc_sfu.sv'):
   old="""(* keep *) reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end"""
   new="""wire [(D+15)/16-1:0] reset_leaf;
    ot_pool_reset_tree #(.N((D+15)/16),.ID(2)) u_reset(clk,rst_n,reset_leaf);
    (* keep *) reg [D:1] line;
    for(genvar q=1;q<=D;q=q+1) begin:g_valid
      if(q==1) begin:g_first
       always @(posedge clk or negedge reset_leaf[(q-1)/16])
        if(!reset_leaf[(q-1)/16]) line[q]<=1'b0; else line[q]<=v;
      end else begin:g_next
       always @(posedge clk or negedge reset_leaf[(q-1)/16])
        if(!reset_leaf[(q-1)/16]) line[q]<=1'b0; else line[q]<=line[q-1];
      end
    end"""
   assert old in t;t=t.replace(old,new)
  elif p.endswith('ot_hdc_v41x_sfu.sv'):
   # Isolate exp reset fanout and map the same exact readonly ln2 bytes locally.
   end=t.index('\nendmodule')
   ex=t[:end];tail=t[end:]
   case=re.search(r'function automatic \[63:0\] ln2_nk.*?endfunction',ex,re.S)[0]
   vals={int(a):int(b+c,16) for a,b,c in re.findall(r"8'd(\d+)\s*: ln2_nk = \{32'h([0-9A-Fa-f]+), 32'h([0-9A-Fa-f]+)\}",case)}
   assert len(vals)==254,len(vals)
   local=[]
   for g in range(64//chunk):
    rows='\n'.join(f"8'd{k}: tab={chunk}'h{(v>>(g*chunk))&((1<<chunk)-1):x};" for k,v in vals.items())
    local.append(f'''(* keep_hierarchy="yes" *) module ot_pool_exp_table_{g}(input wire clk,input wire[31:0] t,input wire[7:0] nmag,output reg[{chunk-1}:0] y);
    (* keep *) reg[7:0] nk;
    always @(posedge clk) nk <= t[31] ? -nmag : nmag;
    function automatic[{chunk-1}:0] tab(input[7:0] k); begin case(k)
    {rows}
    default:tab=0; endcase end endfunction
    always @(posedge clk) y <= tab(nk);
    endmodule''')
   ex=ex.replace(case,'')
   old="always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);"
   assert old in ex
   ex=ex.replace('(* keep *) reg [31:0] a_hi, a_lo;', 'wire [31:0] a_hi, a_lo;')
   ex=ex.replace(old,'wire[63:0] nk_product;\n    assign {a_hi,a_lo}=nk_product;\n'+ '\n'.join(f'ot_pool_exp_table_{g} u_table_{g}(clk,t,tmag,nk_product[{g*chunk}+:{chunk}]);' for g in range(64//chunk)))
   # Every child reset supplied by a two-level source reset tree. Adds only reset startup.
   i=0
   def childreset(m):
    global i
    r=f'.rst_n(exp_reset[{i}])';i+=1;return r
   ex=re.sub(r'\.rst_n\(rst_n\)',childreset,ex)
   def childpos(m):
    global i
    r=f'(clk, exp_reset[{i}],';i+=1;return r
   ex=re.sub(r'\(clk, rst_n,',childpos,ex)
   where=ex.index('    localparam integer T_N')
   ex=ex[:where]+f'    wire [{i-1}:0] exp_reset;\n    ot_pool_reset_tree #(.N({i}),.ID(3)) u_reset(clk,rst_n,exp_reset);\n'+ex[where:]
   t=ex+tail+'\n'+'\n'.join(local)
  # Keep helper and original module names isolated from production source.
  for name in sorted(mods,key=len,reverse=True):
   if name!='ot_s81sl_cmp_pool':t=re.sub(r'\b'+name+r'\b',name+'_pooln',t)
  parts.append('// Original source: '+p+'\n'+t)
 helpers='''
(* keep_hierarchy="yes" *) module ot_pool_mux #(parameter integer ID=0)(input wire sel,input wire[7:0] a,b,output wire[7:0] q); assign q=sel?a:b; endmodule

// Private source-local ownership cells. Two synchronous reset stages, no data edge.
(* keep_hierarchy="yes" *) module ot_pool_reset_bit #(parameter integer ID=0)(input wire clk,d,output reg q);
 (* keep *) reg owned; always @(posedge clk) owned<=d; always @* q=owned;
endmodule
module ot_pool_reset_tree #(parameter integer N=1,ID=0)(input wire clk,rst_n,output wire[N-1:0] q);
 wire[(N+31)/32-1:0] branch;
 for(genvar b=0;b<(N+31)/32;b=b+1) begin:g_b
  ot_pool_reset_bit #(.ID(ID*4096+b)) u_b(clk,rst_n,branch[b]);
 end
 for(genvar l=0;l<N;l=l+1) begin:g_l
  ot_pool_reset_bit #(.ID(ID*4096+1024+l)) u_l(clk,branch[l/32],q[l]);
 end
endmodule
(* keep_hierarchy="yes" *) module ot_pool_hold #(parameter integer ID=0)(input wire clk,en,input wire[7:0] d,output reg[7:0] q);
 always @(posedge clk) if(en) q<=d;
endmodule
'''
 out.write_text('// GENERATED by tools/s81_dv/rtlgap_sukv_1021/pool_native_source.py. Private engineering source.\n'+helpers+'\n'.join(parts))
 out.with_suffix('.json').write_text(json.dumps(dict(variant=variant,table_output_bits=chunk,source_sha256={p:hashlib.sha256(s.encode()).hexdigest() for p,s in texts.items()},generated_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),arithmetic_edges_added=0,maximum_reset_release_edges=6,original_lane_reset_edges=2,qualification='UNQUALIFIED until actual numeric and native outcomes'),indent=2)+'\n')
