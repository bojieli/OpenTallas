#!/usr/bin/env python3
"""Exact selected control arithmetic/state transitions; private reset/output consumers."""
from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[3];D=R/'rtl/dsrom_sys/s81_dv/unit/bk/plana/n32';P=R/'results/arch/s81_topk_control_local_1021'
tile=(R/'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv').read_text()
pipe=(R/'rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv').read_text()
plan=[];used=0
def alloc(name,n):
 global used
 b=used;plan.append({'name':name,'first':b,'count':n});used+=n;return b

def state_machine(text,start,end,widths,reset_expr,allocfn,drop=()):
 a=text.index(start);b=text.index(end,a);block=text[a:b]
 reset,normal=block.split('        end else begin\n',1)
 normal=normal.rsplit('        end\n    end\n',1)[0]
 constants=dict(re.findall(r'\b(\w+)\s*<=\s*([^;]+);',reset))
 assert set(constants)==set(widths)|set(drop),(set(constants),set(widths),set(drop))
 for n in drop:normal=re.sub(r'\b'+n+r'\s*<=\s*[^;]+;','',normal)
 # Replace only nonblocking LHS: all RHS stay old-state, preserving NBA semantics.
 normal=re.sub(r'\b(\w+)(\[[^\]]+\])?\s*<=',lambda m:m[1]+'_d'+(m[2]or'')+' =',normal)
 decl='\n'.join(f'    reg[{w-1}:0]{n}_d;'for n,w in widths.items())+'\n'
 comb='    always @* begin\n'+''.join(f'      {n}_d={n};\n'for n in widths)+normal+'    end\n'
 flops=''
 for n,w in widths.items():
  nc=(w+15)//16;base=allocfn(n,nc)
  flops+=f'    localparam[{w-1}:0]N32_INIT_{n}={constants[n]};\n'
  flops+=f'''    generate for(genvar c=0;c<{nc};c=c+1)begin:g_n32_{n}
      localparam integer LO=c*16,SW=({w}-LO<16)?{w}-LO:16;
      always @(posedge {'ck[0]'if 'ck[0]'in start else 'clk'} or negedge {reset_expr}[{base}+c])
        if(!{reset_expr}[{base}+c]){n}[LO+:SW]<=N32_INIT_{n}[LO+:SW];
        else {n}[LO+:SW]<={n}_d[LO+:SW];
    end endgenerate
'''
 for n,w in widths.items():
  if w==1:flops=flops.replace(n+'[LO+:SW]',n).replace(n+'_d[LO+:SW]',n+'_d')
 return text[:a]+decl+comb+flops+text[b:]
# Selected controller: local same-edge reset leaves for every state group.
c=pipe[pipe.index('module ot_s81ph_sel_ctl_pipe'):]
c=c.replace('ot_s81ph_sel_ctl_pipe','ot_s81pa_sel_ctl').replace('ot_s81ph_sel_su_pipe','ot_s81pa_sel_su')
ctlused=1;ctlplan=[]
def ca(n,k):
 global ctlused
 b=ctlused;ctlplan.append({'name':n,'first':b,'count':k});ctlused+=k;return b
cw={'st':3,'wcnt':8,'hold_c':8,'hold_f':8,'kseen':1,'hf_seen':1,'bs_done':1,'bs':8,'ls':8,'m':11,'t':11,'eq':44,'c_T':16,'c_Bt':8,'c_fclr':1,'c_ing':1,'c_stop':1,'c_p2':1,'c_p3':1,'c_rep':1,'c_st':16,'c_rem':44,'c_hclr':1,'rep_req':1,'ovf':1,'kq':11,'qf':21}
c=state_machine(c,'    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin\n            st <=','    assign busy',cw,'rst_n_profile',ca)
c=c.replace('input  wire                    rst_n,',f'input wire[{ctlused-1}:0]rst_n_profile,')
c=c.replace('    // status inputs, registered','    wire rst_n=rst_n_profile[0]; // status group only,24 FF\n    // status inputs, registered')
c=c.replace('    assign busy =','    initial if(Q!=4||K!=512||KW!=10||CB!=11||XD!=17||PERM!=1||RQPIPE!=1||SLAT!=4)$fatal(1,"fixed selected n32 control shape");\n    assign busy =')
(D/'ot_s81pa_sel_ctl.sv').write_text('// Opt-in; generated from exact selected pipeline state transitions.\n'+'\n'.join(x.rstrip()for x in c.splitlines()).rstrip()+'\n')
# Outer control. Existing registered pipeline ages and all arithmetic unchanged.
s=tile[tile.index('module dsfd_selt_c #('):tile.index('// composition reference')]
s=s.replace('module dsfd_selt_c #(','module ot_s81pa_ctl #(')
# Fix selected parameters through the new master; assert unsupported choices.
s=s.replace('parameter integer MRG_PIPE = 0','parameter integer MRG_PIPE = 1').replace('parameter integer RQPIPE = 0','parameter integer RQPIPE = 1').replace('parameter integer SLAT = 0','parameter integer SLAT = 4').replace('parameter integer XDX = 0','parameter integer XDX = 15')
s=s.replace('input  wire [0:0]                rst,','input wire[__NR__-1:0]rst_profile,')
old='''    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];'''
assert old in s
alloc('status_vd',1)
s=s.replace(old,'''    wire[__NR__-1:0]rst_local;
    generate for(genvar r=0;r<__NR__;r=r+1)begin:g_rst
      ot_s81pa_rst_leaf #(.ID(r))u(.clk(ck[0]),.raw(rst_profile[r]),.q(rst_local[r]));
    end endgenerate
    wire rst_n=rst_local[0];''')
base=alloc('status_sq_chunks24',(4*865+23)//24)
old='    always @(posedge ck[0] or negedge rst_n) if (!rst_n) sq <= {Q*SB{1\'b0}}; else sq <= f_s;'
assert old in s
s=s.replace(old,f'''    generate for(genvar c=0;c<(Q*SB+23)/24;c=c+1)begin:g_sq
      localparam integer LO=c*24,SW=(Q*SB-LO<24)?Q*SB-LO:24;
      always @(posedge ck[0] or negedge rst_local[{base}+c])
        if(!rst_local[{base}+c])sq[LO+:SW]<=0;else sq[LO+:SW]<=f_s[LO+:SW];
    end endgenerate''')
a=s.index('    generate if (SEARCH_PIPE == 3)');b=s.index('    // command bundles',a)
cb=alloc('pipeline_controller',ctlused)
s=s[:a]+f'''    ot_s81pa_sel_ctl #(.Q(Q),.K(K),.KW(KW),.CB(CB),.XD(2+XDX),.PERM(1),.RQPIPE(RQPIPE),.SLAT(SLAT))u_ctl(
      .clk(ck[0]),.rst_n_profile(rst_local[{cb}+:{ctlused}]),.k_in(k_r),.k_ld(kld_r),.qs(qs),
      .s_gc(s_gc),.s_gf(s_gf),.s_bc(s_bc),.s_bf(s_bf),.s_last(s_last),.s_hfin(s_hfin),.s_stopped(s_stopped),.s_done2(s_done2),.s_emitted(s_emitted),.s_ovf(s_ovf),
      .c_T(c_T),.c_Bt(c_Bt),.c_fclr(c_fclr),.c_cg(c_cg),.c_fg(c_fg),.c_ing(c_ing),.c_stop(c_stop),.c_p2(c_p2),.c_p3(c_p3),.c_rep(c_rep),.c_st(c_st),.c_rem(c_rem),.c_hclr(c_hclr),.rep_req(rep_req),.ovf(ovf),.busy(busy));
''' +s[b:]
a=s.index('    generate for (g = 0; g < Q; g = g + 1) begin : g_c');b=s.index('    // ---- landing FIFOs',a)
bas=alloc('command_chunks24',4*3)
s=s[:a]+f'''    wire[Q*`SELT_CB-1:0]cmd_next;
    generate for(g=0;g<Q;g=g+1)begin:g_c
      assign cmd_next[`SELT_CB*g+:`SELT_CB]={{c_hclr,c_rem[(KW+1)*g+:KW+1],c_st,c_rep,c_p3,c_p2,c_stop,c_ing,c_fg,c_cg,c_fclr,c_Bt,c_T}};
      for(genvar c=0;c<3;c=c+1)begin:g_chunk
        localparam integer LO=c*24,SW=(`SELT_CB-LO<24)?`SELT_CB-LO:24;
        always @(posedge ck[0] or negedge rst_local[{bas}+g*3+c])
          if(!rst_local[{bas}+g*3+c])cmd[g][LO+:SW]<=0;else cmd[g][LO+:SW]<=cmd_next[`SELT_CB*g+LO+:SW];
      end
      assign t_c[`SELT_CB*g+:`SELT_CB]=cmd[g];
    end endgenerate
''' +s[b:]
a=s.index('    reg  [DW-1:0] lq');b=s.index('    reg [Q-1:0] crq;',a)
qb=alloc('queue_forwarding_flags',4*23)
s=s[:a]+f'''    wire[357:0]queue_head[0:3];wire[4*358-1:0]heads;
    wire[2:0]lc[0:3];wire[11:0]lc_next;
    reg[Q-1:0]lpop;wire[Q-1:0]lv;
    generate for(g=0;g<Q;g=g+1)begin:g_l
      assign lv[g]=(lc[g]!=0);
      assign lc_next[g*3+:3]=lc[g]+3'(oq[OB*g])-3'(lpop[g]);
      ot_s81pa_queue u_q(.clk(ck[0]),.rst_n(rst_local[{qb}+23*g+:23]),.push(oq[OB*g]),.pop(lpop[g]),
        .data({{pop16(oq[OB*g+1+320+:16]),oq[OB*g+1+:DW]}}),.head(queue_head[g]),.count(lc[g]));
      assign heads[358*g+:358]=queue_head[g];
    end endgenerate
''' +s[b:]
cr=alloc('credit',1)
s=s.replace("always @(posedge ck[0] or negedge rst_n) if (!rst_n) crq <= {Q{1'b0}}; else crq <= lpop;",f"always @(posedge ck[0] or negedge rst_local[{cr}]) if (!rst_local[{cr}]) crq <= {{Q{{1'b0}}}}; else crq <= lpop;")
s=s.replace('wire [DW-1:0] hd = lq[tsel][0];','wire [DW-1:0] hd = queue_head[tsel][0+:DW];')
s=s.replace('lqp[tsel][0]','queue_head[tsel][DW+:5]')
s=s.replace('    reg [511:0] o_d;','    wire [511:0] o_d;')
ow={'seg_open':1,'seg_k':10,'seg_tag':8,'flt':5,'e_coll':1,'e_kt':1,'k_r':10,'kld_r':1,'qs':8,'ovf_seen':1,'rep_pend':2,'rep_n':1,'cq':2,'done_pend':1,'cnt':10,'cnt_add':5,'flt_rep':5,'pc':2,'o_v':1}
s=state_machine(s,'    always @(posedge ck[0] or negedge rst_n) begin\n        if (!rst_n) begin\n            seg_open <=','`ifndef SYNTHESIS',ow,'rst_local',lambda n,k:alloc('outer_'+n,k),drop=('o_d',))
pb=alloc('packet_consumers',22*5)
insert=f'''    wire[52:0]packet_next={{{{f_s[3*SB+838],f_s[2*SB+838],f_s[SB+838],f_s[838]}},lc_next,seg_tag_d,flt_d,flt_rep_d,rep_pend_d,done_pend_d,pc_d,rep_n_d,cq_d,cnt_d,ovf_seen_d}};
    generate for(genvar c=0;c<22;c=c+1)begin:g_packet
      localparam integer LO=c*24,SW=(512-LO<24)?512-LO:24;
      ot_s81pa_packet #(.LO(LO),.SW(SW),.ID(c))u(.clk(ck[0]),.rst_n(rst_local[{pb}+5*c+:5]),.state_next(packet_next),.selector_next(ts),.heads(heads),.out(o_d[LO+:SW]));
    end endgenerate
    initial if(SEARCH_PIPE!=1||DM!=4||PACE!=2||MRG_PIPE!=1||RQPIPE!=1||SLAT!=4||XDX!=15)$fatal(1,"fixed selected n32 outer shape");
'''
s=s.replace('`ifndef SYNTHESIS',insert+'`ifndef SYNTHESIS',1)
nr=used;s=s.replace('__NR__',str(nr));(D/'ot_s81pa_ctl.sv').write_text('// Opt-in; exact state transitions, SRAM queues, same-edge local output consumers.\n'+'\n'.join(x.rstrip()for x in s.splitlines()).rstrip()+'\n')
# New wrapper; no old module or CLOSED view is overwritten.
w=(R/'rtl/dsrom_sys/s81_dv/unit/bk/plana/dsdv_bksel_q_pa.sv').read_text().split('module dsdv_bksel_c_pa',1)[1]
w='module dsdv_bksel_c_pa_n32'+w
w=w.replace('input wire ck,rst,',f'input wire ck,input wire[{nr-1}:0]rst_profile,')
w=re.sub(r'dsfd_selt_c #\(.*?\)u_c', 'ot_s81pa_ctl u_c',w)
w=w.replace('.rst(rst)', '.rst_profile(rst_profile)')
(D/'dsdv_bksel_c_pa_n32.sv').write_text('// New master; CLOSED c2 and old c_pa are untouched.\n'+w)
# Connected opt-in parent from exact canonical generated source. Only controller
# instance/reset branch changes; all224 landing instances and schedules retained.
f=R/'rtl/dsrom_sys/s81_dv/unit/bk/plana/lp/dsdv_bk_sel_pa_lp.sv';parent=f.read_text()
parent=parent.replace('module dsdv_bk_sel_pa_lp #(', 'module dsdv_bk_sel_pa_n32_lp #(')
parent=parent.replace('dsdv_bksel_c_pa u_c (.ck(ck_core), .rst(lpr_c_u_c),',f'dsdv_bksel_c_pa_n32 u_c (.ck(ck_core), .rst_profile(ctl_rst_profile),')
marker='    dsdv_bksel_c_pa_n32 u_c '
assert marker in parent
parent=parent.replace(marker,f'    wire[{nr-1}:0]ctl_rst_profile;\n    ot_s81pa_parent_rst #(.NR({nr}))u_ctl_rst(.clk(ck_core),.rst_raw(rst_n_core),.rst_profile(ctl_rst_profile));\n'+marker)
parent=parent.replace('// GENERATED by tools/landed_parent/lp.py','// DERIVED by tools/s81_dv/topk_control_local_1021/build_control.py from exact tools/landed_parent/lp.py')
(D/'dsdv_bk_sel_pa_n32_lp.sv').write_text('// Opt-in parent successor; all224 seam instances unchanged.\n'+parent)
(P/'reset_profile.json').write_text(json.dumps({'raw_parent_port':'rst_n_core','parent_stages':4,'child_stages':2,'NR':nr,'parent_first_fanout':(nr+31)//32,'parent_FF':1+(nr+31)//32+2*nr,'child_reset_FF':2*nr,'profile':plan,'controller_subprofile':ctlplan,'ledger':'6total edges, equal original4+2; provisional until production+causal release proof','source':{'tile_sha256':hashlib.sha256(tile.encode()).hexdigest(),'pipeline_sha256':hashlib.sha256(pipe.encode()).hexdigest(),'canonical_parent_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}},indent=2)+'\n')
print('new control reset profile',nr,'parentFF',1+(nr+31)//32+2*nr,'childresetFF',2*nr,'controllerleaves',ctlused)
