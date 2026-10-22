#!/usr/bin/env python3
"""QKO-SLICE2-STN2 10-21: NATIVE32-safe private copies for qfd_dv_s8_station_tail1 (census b: 197 drivers > 32).
The CLOSED stnrgc g3 sources (qfd_dv_station_math_g.sv, qfd_dv_redstn2_gsafe.sv, qfd_dv_ring_delay.sv) stay
byte-identical; tail1 instantiates qfd_dv_s8s_* copies only.  No stage/edge change anywhere:
 - math netlist: every flop whose Q has >= SPLIT uses -> ceil(uses/PER) kept copies (distinct ID, same C/D/R, same edge);
   every ring_delay output bit with >= SPLIT uses -> ring_replicated COPIES (same writer, extra same-edge readers)
 - ring writer -> ot_pl_land_n32_chunk_w (kept one-hot selector copies; same slots/K/reset ages as phys_chunk_w)
 - sram_lookahead / sram_delay: one kept select / valid bit per 12 data bits (was 32)
 - station mode: two kept mode units per payload slot (16-bit fd mux split 8/8)"""
import re,math
from pathlib import Path
R=Path(__file__).resolve().parents[2]
S8=R/'rtl/qwen_dv/s5/s8'
SPLIT,PER=12,10
OUTPINS=('Q','Y','q','y')

def math_g():
    src=(R/'rtl/qwen_dv/qfd_dv_station_math_g.sv').read_text()
    parts=re.split(r'\n(?=(?:\(\* keep_hierarchy="yes" \*\) )?module )',src)
    out=[];stats=[]
    for m in parts:
        mm=re.search(r'module (\w+)',m)
        if not mm or 'data_g' not in mm.group(1):
            out.append(m);continue
        lines=m.split('\n')
        uses={};drv={}
        inst_re=re.compile(r'^((?:\(\*.*?\*\) )?)(\w+) (#\(.*?\) )?(u_\d+)\((.*)\);$')
        for i,l in enumerate(lines):
            if l.startswith('assign'):
                for n in re.findall(r'\bn_\d+\b',l.split('=',1)[1]):uses[n]=uses.get(n,0)+1
                continue
            im=inst_re.match(l)
            if not im:continue
            for p,v in re.findall(r'\.(\w+)\(([^()]*)\)',im[5]):
                ns=re.findall(r'\bn_\d+\b',v)
                if p in OUTPINS:
                    for b,n in enumerate(ns):drv[n]=(i,im[2],b)
                else:
                    for n in ns:uses[n]=uses.get(n,0)+1
        heavy={n:math.ceil(c/PER) for n,c in uses.items() if c>=SPLIT and n in drv and (('dff' in drv[n][1]) or drv[n][1]=='qfd_dv_ring_delay')}
        per={n:math.ceil(uses[n]/k) for n,k in heavy.items()}
        seen={n:0 for n in heavy}
        def cp(n,c):return n if c==0 else f'{n}_s{c}'
        def sub_rhs(txt):
            def f(mo):
                n=mo.group(0)
                if n not in heavy:return n
                c=seen[n]//per[n];seen[n]+=1;return cp(n,c)
            return re.sub(r'\bn_\d+\b',f,txt)
        new=[];newwires=[]
        for i,l in enumerate(lines):
            if l.startswith('assign'):
                lhs,rhs=l.split('=',1);new.append(lhs+'='+sub_rhs(rhs));continue
            im=inst_re.match(l)
            if not im:
                new.append(l);continue
            pre,typ,par,name,body=im[1],im[2],im[3] or '',im[4],im[5]
            def pins(body):
                return re.sub(r'\.(\w+)\(([^()]*)\)',lambda mo:f'.{mo[1]}({mo[2] if mo[1] in OUTPINS else sub_rhs(mo[2])})',body)
            body2=pins(body)
            qn=[n for p,v in re.findall(r'\.(\w+)\(([^()]*)\)',body) if p in OUTPINS for n in re.findall(r'\bn_\d+\b',v)]
            hk=max([heavy.get(n,1) for n in qn]+[1])
            if 'dff' in typ:
                t2=typ.replace('qfd_bmath_','qfd_s8s_bmath_')
                new.append(f'{pre}{t2} {par}{name}({body2});')
                if hk>1:
                    oid=int(re.search(r'\.ID\((\d+)\)',par)[1])
                    for c in range(1,hk):
                        p2=par.replace(f'.ID({oid})',f'.ID({1000000+16*oid+c})')
                        b2=re.sub(r'\.Q\((n_\d+)\)',lambda mo:f'.Q({cp(mo[1],c)})',body2)
                        new.append(f'{pre}{t2} {p2}{name}_s{c}({b2});');newwires.append(cp(qn[0],c))
                    stats.append((mm.group(1),name,uses[qn[0]],hk))
            elif typ=='qfd_dv_ring_delay':
                w=int(re.search(r'\.W\((\d+)\)',par)[1]);d=int(re.search(r'\.D\((\d+)\)',par)[1])
                rid=int(name[2:])
                if hk>1:
                    assert d>=3,(name,d)
                    qv=re.search(r'\.q\(([^()]*)\)',body2)[1]
                    bits=re.findall(r'\bn_\d+\b',qv)
                    cat=','.join(','.join(cp(b,c) for b in bits) for c in reversed(range(hk)))
                    for c in range(1,hk):newwires+= [cp(b,c) for b in bits]
                    b2=body2.replace(f'.q({qv})','.q({'+cat+'})')
                    new.append(f'qfd_dv_s8s_ring_replicated #(.W({w}),.D({d}),.COPIES({hk}),.ID({rid})) {name}({b2.replace(".clk(",".clk(")});')
                    stats.append((mm.group(1),name,max(uses.get(b,0) for b in bits),hk))
                else:
                    new.append(f'qfd_dv_s8s_ring_delay #(.W({w}),.D({d}),.ID({rid})) {name}({body2});')
            else:
                new.append(f'{pre}{typ.replace("qfd_bmath_","qfd_s8s_bmath_")} {par}{name}({body2});')
        for n,k in heavy.items():assert seen[n]==uses[n],(n,seen[n],uses[n])
        txt='\n'.join(new).replace(f'module {mm.group(1)}(',f'module {mm.group(1).replace("qfd_dv_","qfd_dv_s8s_")}(',1)
        if newwires:
            first=[i for i,l in enumerate(txt.split('\n')) if l.startswith('wire ')][0]
            tl=txt.split('\n');tl.insert(first,'wire '+', '.join(newwires)+';');txt='\n'.join(tl)
        out.append(txt)
    res='\n'.join(out)
    res=re.sub(r'module qfd_bmath_',r'module qfd_s8s_bmath_',res)
    assert 'qfd_bmath_' not in res
    res=dup_gates(res)
    (S8/'qfd_dv_s8_station_math_g.sv').write_text('// GENERATED by tools/qwen_dv/gen_s8_station_safe.py from rtl/qwen_dv/qfd_dv_station_math_g.sv: kept flop/ring copies <= %d uses each; no edge change.\n'%PER+res)
    return stats

# census b @a575cb86e: 6 combinational drivers left (50-64 loads), all in the mul netlist: OR-reduction outputs n_617 /
# n_650 (62 uses, ABC pushed onto n_4684 / AND3) and mux n_180 (31 uses).  Depth-1 kept duplicates: the driving gate is
# emitted as COPIES distinct keep_hierarchy cells (ID differs -> ABC cannot re-merge them); users split <= PER each.
# census @081f3e217: 2 left (36/51) downstream of n_782 / n_7387 -> every mul comb net with >= 24 uses duplicated too.
DUP={'qfd_dv_s8s_station_mul_data_g':['n_617','n_650','n_180','n_191','n_782','n_7147','n_4766','n_4771','n_7205','n_7208',
                                      'n_4989','n_7388','n_7387','n_7346','n_7345','n_7202']}
def dup_gates(res):
    mods=[]
    for mod,nets in DUP.items():
        a=res.index(f'module {mod}(');b=res.index('endmodule',a)
        body=res[a:b]
        for h in nets:
            m=re.search(rf'\nassign {h} = (.*);',body);assert m,h
            expr=m[1]
            # census @f8b1bebe9: an inverter copy is transparent to the census (n_7147 = ~n_7112 left 36 on n_7112):
            # fold the inverted gate into each kept copy so the copies are real gates on n_7112's inputs.
            mi=re.fullmatch(r'~\((n_\d+(?:_[gs]\d+)*)\)',expr.strip())
            if mi:
                md=re.search(r'\nassign '+mi[1]+r' = (.*);',body)
                if md:expr='~('+md[1]+')'
            ins=list(dict.fromkeys(re.findall(r'\bn_\d+(?:_[gs]\d+)*\b',expr)))
            uses=[]
            lines=body.split('\n')
            cnt=0
            for l in lines:
                if l.startswith('assign'):cnt+=len(re.findall(rf'\b{h}\b',l.split('=',1)[1]))
                elif re.match(r'(\(\*.*?\*\) )?\w+ (#\(.*?\) )?u_\d+',l):
                    cnt+=sum(len(re.findall(rf'\b{h}\b',v)) for p_,v in re.findall(r'\.(\w+)\(([^()]*)\)',l) if p_ not in OUTPINS)
            k=math.ceil(cnt/PER);per=math.ceil(cnt/k);seen=[0]
            def f(mo):
                c=seen[0]//per;seen[0]+=1;return f'{h}_g{c}'
            new=[]
            for l in lines:
                if l.startswith('assign') and not l.startswith(f'assign {h} '):
                    lhs,rhs=l.split('=',1);l=lhs+'='+re.sub(rf'\b{h}\b',f,rhs)
                elif re.match(r'(\(\*.*?\*\) )?\w+ (#\(.*?\) )?u_\d+',l):
                    hp=re.compile(r'\b'+h+r'\b')
                    l=re.sub(r'\.(\w+)\(([^()]*)\)',lambda mo:mo[0] if mo[1] in OUTPINS else '.'+mo[1]+'('+hp.sub(f,mo[2])+')',l)
                new.append(l)
            assert seen[0]==cnt,(h,seen[0],cnt)
            dm=f'qfd_s8s_dup_{h}'
            e2=expr
            for j,n in enumerate(ins):e2=re.sub(rf'\b{n}\b',f'i[{j}]',e2)
            mods.append(f'(* keep_hierarchy="yes" *) module {dm} #(parameter integer ID=0)(input wire [{len(ins)-1}:0] i,output wire y);\nassign y = {e2};\nendmodule')
            inst=[f'wire '+', '.join(f'{h}_g{c}' for c in range(k))+';']
            inst+=[f'(* keep_hierarchy="yes" *) {dm} #(.ID({c})) u_dup_{h}_{c}(.i({{{",".join(reversed(ins))}}}),.y({h}_g{c}));' for c in range(k)]
            body='\n'.join(new)
            i0=body.index(f'\nassign {h} = ')
            body=body[:i0]+'\n'+'\n'.join(inst[1:])+body[i0:]
            w0=body.index('\nwire ');body=body[:w0]+'\n'+inst[0]+body[w0:]
            print('DUP',mod,h,cnt,'uses ->',k,'copies')
        res=res[:a]+body+res[b:]
    return res+'\n'+'\n'.join(mods)+'\n'

SAFE=r'''`timescale 1ns/1ps
// GENERATED by tools/qwen_dv/gen_s8_station_safe.py: private NATIVE32-safe copies for qfd_dv_s8_station_tail1 only.
module qfd_dv_s8s_ring_delay #(parameter integer W=32,D=1,RESET=0,ID=0)(
 input wire clk,rst_n,input wire[W-1:0] d,output wire[W-1:0] q
);
 generate if(D==0) begin:g_wire assign q=d;
 end else if(D<=2) begin:g_short
  reg[W-1:0] p[0:D-1];
  always @(posedge clk) begin p[0]<=d;for(integer k=1;k<D;k=k+1)p[k]<=p[k-1];end
  assign q=p[D-1];
 end else begin:g_ring
  qfd_dv_s8s_ring_replicated #(.W(W),.D(D),.COPIES(1),.ID(ID)) u_r(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
 end endgenerate
`ifndef SYNTHESIS
 initial if(RESET!=0||W<1||W>32||D<0||D>12)$fatal(1,"SAFE_RING_DELAY unsupported shape");
`endif
endmodule
module qfd_dv_s8s_ring_replicated #(parameter integer W=1,D=7,COPIES=1,ID=0)(
 input wire clk,rst_n,input wire[W-1:0] d,output wire[COPIES*W-1:0] q
);
 localparam integer N=D/3,R=D%3,C=(W+23)/24;
 wire local_reset;
 qfd_dv_reset_tree #(.N(1)) u_rt(.ck(clk),.rst_n(rst_n),.q(local_reset));
 wire[W-1:0] stage[0:N];
 generate if(R==0) begin:g_no_prefix assign stage[0]=d;
 end else begin:g_prefix
  (* keep_hierarchy="yes" *) qfd_dv_ring_prefix #(.W(W),.D(R),.ID(ID)) u_p(.clk(clk),.d(d),.q(stage[0]));
 end
 for(genvar i=0;i<N;i=i+1) begin:g_stage
  wire[4*W-1:0] bank;wire[4*C-1:0] valid;wire[11:0] epo;
  // n32 writer: kept one-hot selector copy per 12 data bits; rq resets only copies + valid (census: rq 41-105 loads)
  ot_pl_land_n32_chunk_w #(.W(W),.D(4),.CHUNK_BITS(24)) u_w(.ck(clk),.rsi(local_reset),.i(stage[i]),.bank(bank),.epo(epo),.vld(valid));
  if(i<N-1) begin:g_middle
`ifndef OT_ASSERT
   ot_pl_land_phys_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24),.ID(0)) u_r(.ck(clk),.rsi(local_reset),.bank(bank),.vld(valid),.o(stage[i+1]));
`else
   ot_pl_land_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24)) u_r(.ck(clk),.rsi(local_reset),.bank(bank),.epo(epo),.vld(valid),.o(stage[i+1]));
`endif
  end else begin:g_final
   for(genvar o=0;o<COPIES;o=o+1) begin:g_copy
`ifndef OT_ASSERT
    ot_pl_land_phys_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24),.ID(o)) u_r(.ck(clk),.rsi(local_reset),.bank(bank),.vld(valid),.o(q[W*o+:W]));
`else
    ot_pl_land_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24)) u_r(.ck(clk),.rsi(local_reset),.bank(bank),.epo(epo),.vld(valid),.o(q[W*o+:W]));
`endif
   end
  end
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<1||W>32||D<3||D>12||COPIES<1||COPIES>8)$fatal(1,"SAFE_RING_REPLICATED unsupported shape");
`endif
endmodule
module qfd_dv_s8s_sram_lookahead #(parameter integer W = 512, parameter integer MUT = 0, parameter integer G = 12) (
    input wire ck, input wire write, input wire [4:0] wa, ra,
    input wire [W-1:0] wd, output wire [W-1:0] q
);
    wire same = write && wa == ra;
    wire [W-1:0] mq;
    reg [W-1:0] bypass_data;
    always @(posedge ck) bypass_data <= wd;
    qfd_dv_sram_bank64 #(.W(W)) u_m (.clk(ck), .r_ce_in(!same), .r_addr_in(ra), .rd_out(mq),
        .w_ce_in(write), .w_addr_in(wa), .wd_in(wd), .w_mask_in({W{1'b1}}));
    genvar g;
    generate for (g = 0; g < (W+G-1)/G; g = g + 1) begin : g_out
        localparam integer B = ((W-G*g) < G) ? W-G*g : G;
        wire sel;
        (* keep_hierarchy = "yes" *) qfd_dv_kept_bit #(.ID(g)) u_sel (.ck(ck), .d(same && MUT == 0), .q(sel));
        assign q[G*g +: B] = sel ? bypass_data[G*g +: B] : mq[G*g +: B];
    end endgenerate
`ifndef SYNTHESIS
    initial if (W > 546 || W < 1) $fatal(1, "SRAM_LOOKAHEAD_WIDTH");
`endif
endmodule
module qfd_dv_s8s_sram_delay #(parameter integer W = 514, parameter integer D = 14, parameter integer MUT = 0, parameter integer G = 12) (
    input wire ck, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    reg [4:0] wp;
    reg [D-2:0] valid;
    wire mask_reset;
    (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(2048)) u_mask_reset (.ck(ck),.rst_n(rst_n),.d(1'b1),.q(mask_reset));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin wp <= 0; valid <= 0; end
        else begin wp <= wp + 1'b1; valid <= {valid[D-3:0], 1'b1}; end
    wire [4:0] ra = wp - (D-1) + ((MUT != 0) ? 5'd1 : 5'd0);
    wire [W-1:0] mq;
    qfd_dv_sram_bank64 #(.W(W)) u_m (.clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mq),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(d), .w_mask_in({W{1'b1}}));
    genvar g;
    generate for (g = 0; g < (W+G-1)/G; g = g + 1) begin : g_out
        localparam integer B = ((W-G*g) < G) ? W-G*g : G;
        wire warm_q;
        (* keep_hierarchy = "yes" *) qfd_dv_kept_valid #(.ID(g)) u_v (.ck(ck), .rst_n(mask_reset), .d(valid[D-2]), .q(warm_q));
        assign q[G*g +: B] = warm_q ? mq[G*g +: B] : {B{1'b0}};
    end endgenerate
`ifndef SYNTHESIS
    initial if (D < 3 || D > 27 || W > 546) $fatal(1, "SRAM_DELAY_CONFIG");
`endif
endmodule
'''

def safe_sv():
    g=(R/'rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv').read_text()
    a=g.index('module qfd_dv_station_add_bounded');b=g.index('endmodule',g.index('module qfd_dv_station_mul_bounded'))+len('endmodule')
    blk=g[a:b]
    for x in ['station_add_bounded','station_mul_bounded','station_add_data_g','station_mul_data_g','ring_replicated','ring_delay']:
        blk=re.sub(rf'\bqfd_dv_{x}\b',f'qfd_dv_s8s_{x}',blk)
    (S8/'qfd_dv_s8_station_safe.sv').write_text(SAFE+blk+'\n')

def tail(path):
    s=path.read_text()
    for x in ['station_add_bounded','station_mul_bounded','sram_delay','sram_lookahead','ring_delay']:
        s=re.sub(rf'\bqfd_dv_{x}\b',f'qfd_dv_s8s_{x}',s)
    old=' (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(z),.USE2(z==0)) u_m(.ck(ck),.rst_n(sr_reset[22+z]),.cfg_v(cfg_final[z]),.mode(mode_payload[z]),.q(local_mode[z]));\n'
    assert s.count(old)==1
    s=s.replace(old,old+' // second kept mode unit, same cfg edge: fd mux bits [15:8] (census: used_q 33 loads)\n'
                ' (* keep_hierarchy="yes" *) qfd_dv_station_mode #(.ID(16+z),.USE2(z==0)) u_m2(.ck(ck),.rst_n(sr_reset[22+z]),.cfg_v(cfg_final[z]),.mode(mode_payload[z]),.q(local_mode2[z]));\n')
    s=s.replace('wire[3:0] local_mode[0:NZ-1];','wire[3:0] local_mode[0:NZ-1];\nwire[3:0] local_mode2[0:NZ-1];',1)
    old='assign fd[16*z+:16]=local_mode[z][0]?y7[16*z+:16]:local_mode[z][1]?y8[16*z+:16]:y9[16*z+:16];'
    assert s.count(old)==1
    s=s.replace(old,'assign fd[16*z+:8]=local_mode[z][0]?y7[16*z+:8]:local_mode[z][1]?y8[16*z+:8]:y9[16*z+:8];\n'
                '     assign fd[16*z+8+:8]=local_mode2[z][0]?y7[16*z+8+:8]:local_mode2[z][1]?y8[16*z+8+:8]:y9[16*z+8+:8];')
    path.write_text(s)

def main():
    st=math_g();safe_sv();tail(S8/'qfd_dv_s8_station_tail1.sv')
    import subprocess,sys;subprocess.run([sys.executable,str(R/'tools/qwen_dv/gen_s8_mul_cut.py'),'0.5','station'],check=True)  # QR-TAIL1: SCALE_LAT 7 encode cut
    for x in st:print('SPLIT',*x)
if __name__=='__main__':main()
