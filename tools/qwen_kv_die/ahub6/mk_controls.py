#!/usr/bin/env python3
"""Private AHUB6 same-edge copies. Partial until mapped census is clean."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'rtl/hdc/nearhbm/qkd_ahub_static_dw_safe.sv'
OUT = BASE.with_name('qkd_ahub6_controls.sv')


def replace(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a))
    return s.replace(a, b)


def main():
    source = BASE.read_text()
    names = ('qkd_ahub_static_io_safe', 'qkd_ahub_static_dec_safe', 'qkd_ahub_static_core_la_safe')
    blocks = []
    for name in names:
        match = re.search(r'^module ' + name + r'\b.*?^endmodule', source, re.M | re.S)
        assert match, name
        blocks.append(match.group(0))
    io, dec, core = blocks
    io = replace(io, 'output reg           start,', 'output wire          start,\n    output wire [31:0] start_all,')
    io = replace(io, 'input  wire          rst_n,', 'input wire [3:0] rst_group,')
    io = replace(io, '    // KV-AHUBDW 10-18 (pin rule:', '    wire rst_n = rst_group[0];\n    assign start = start_all[0];\n    // KV-AHUBDW 10-18 (pin rule:')
    io = replace(io, "    always @(posedge ck or negedge rst_n)\n        if (!rst_n) start <= 1'b0; else start <= hs_start;", '''    for(genvar c=0;c<32;c=c+1) begin:g_start_copy
        ot_ahub6_async_copy #(.ID(c)) u_ff(.ck(ck),.rn(rst_group[c/8]),.d(hs_start),.q(start_all[c]));
    end''')
    io = io.replace('if (start) T_h <= T_p;', 'if (start_all[1]) T_h <= T_p;')
    io = io.replace('T = start ? T_p : T_h;', 'T = start_all[2] ? T_p : T_h;')
    io = replace(io, '    always @(posedge ck) if (start) tgt_q <= tgt_n;', '''    always @(posedge ck) begin
        if(start_all[3]) tgt_q[9:0] <= tgt_n[9:0];
        if(start_all[4]) tgt_q[18:10] <= tgt_n[18:10];
    end''')
    io = replace(io, '    always @(posedge ck) if (start) begin si_epoch <= {4{epoch}}; si_layer <= {4{layer}}; end', '''    for(genvar c=0;c<4;c=c+1) begin:g_identity
        always @(posedge ck) if(start_all[5+c]) si_epoch[16*c+:16] <= epoch;
        always @(posedge ck) if(start_all[9+c/2]) si_layer[6*c+:6] <= layer;
    end''')
    io = io.replace('wire [16:0] age_nx = start ?', 'wire [16:0] age_nx = start_all[11] ?')
    io = io.replace('bad_t  = start &&', 'bad_t  = start_all[11] &&')
    io = io.replace(" age <= 16'd0;", '').replace(" age <= 16'd1;", '')
    io = io.replace('                if (active) age <= age_nx[15:0];\n', '')
    io = replace(io, '    always @(posedge ck or negedge rst_n)\n        if (!rst_n) fault', '''    for(genvar c=0;c<2;c=c+1) begin:g_age
        always @(posedge ck or negedge rst_group[c])
            if(!rst_group[c]) age[8*c+:8]<=0;
            else if(start_all[30+c]) age[8*c+:8]<=(c==0)?8'd1:8'd0;
            else if(active) age[8*c+:8]<=age_nx[8*c+:8];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault''')
    io = replace(io, '    (* keep *) reg em_w;', '''    wire [19:0] em_w_copy;
    wire em_w = em_w_copy[0];
    for(genvar c=0;c<20;c=c+1) begin:g_export_copy
        ot_ahub6_async_copy #(.ID(64+c)) u_ff(.ck(ck),.rn(rst_group[1+c/8]),.d(em_d),.q(em_w_copy[c]));
    end''')
    io = io.replace(" em_w <= 1'b0;", '').replace('            em_w <= em_d;\n', '')
    io = replace(io, '''    always @(posedge ck)
        if (em_w) begin
            fr_rz    <= (MUT == 2) ? {rz_vector[127:64], rz_vector[31:0], rz_vector[63:32]} : rz_vector;
            fr_epoch <= (MUT == 3) ? prev_ep : rz_epoch;
            prev_ep  <= rz_epoch;
        end''', '''    wire [127:0] export_rz = (MUT == 2) ? {rz_vector[127:64], rz_vector[31:0], rz_vector[63:32]} : rz_vector;
    wire [15:0] export_epoch = (MUT == 3) ? prev_ep : rz_epoch;
    for(genvar c=0;c<16;c=c+1) begin:g_export_data
        always @(posedge ck) if(em_w_copy[c]) fr_rz[8*c+:8] <= export_rz[8*c+:8];
    end
    for(genvar c=0;c<2;c=c+1) begin:g_export_epoch
        always @(posedge ck) if(em_w_copy[16+c]) fr_epoch[8*c+:8] <= export_epoch[8*c+:8];
        always @(posedge ck) if(em_w_copy[18+c]) prev_ep[8*c+:8] <= rz_epoch[8*c+:8];
    end''')
    # Core command copies are the IO pin flops themselves, not an added stage.
    core = replace(core, 'input wire clk,rst_n,start,active_layer_parity,', 'input wire clk,rst_n,start,active_layer_parity,\n    input wire [31:0] start_all,')
    core = replace(core, '''    always @(posedge clk)if(start)
        {RZ_PUBLISH_AGE,RECIP_RETURN_AGE,RECIP_ISSUE_AGE,Z_START_AGE,LMAX_ISSUE_AGE,Z_IN_AGE,LMAX_IN_AGE}<=cal;''', '''    wire [207:0] held_cal;
    assign {RZ_PUBLISH_AGE,RECIP_RETURN_AGE,RECIP_ISSUE_AGE,Z_START_AGE,LMAX_ISSUE_AGE,Z_IN_AGE,LMAX_IN_AGE}=held_cal;
    for(genvar c=0;c<13;c=c+1) begin:g_calendar
        reg [15:0] word_q;
        always @(posedge clk) if(start_all[12+c]) word_q <= cal[16*c+:16];
        assign held_cal[16*c+:16]=word_q;
    end''')
    # The old declaration is changed to wires because held_cal owns storage.
    core = core.replace('reg [63:0] LMAX_IN_AGE,Z_IN_AGE;reg [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE;', 'wire [63:0] LMAX_IN_AGE,Z_IN_AGE;wire [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE;')
    # Separate the non-calendar command consumers from IO bookkeeping.
    core = re.sub(r'\bstart\b', 'start_all[25]', core)
    core = core.replace('clk,rst_n,start_all[25],active_layer_parity', 'clk,rst_n,start,active_layer_parity')
    # Distinct start_b copies feed the old clear groups. Later census drives
    # further bit partitioning; no pre-gate admission is implied here.
    core = replace(core, '    reg start_b;', '''    wire [19:0] start_b_copy;
    wire start_b = start_b_copy[0];
    for(genvar c=0;c<20;c=c+1) begin:g_start_b_copy
        ot_ahub6_async_copy #(.ID(128+c)) u_ff(.ck(clk),.rn(rn[7]),.d(start_all[26+c/5]),.q(start_b_copy[c]));
    end''')
    core = core.replace('start_b<=0;', '').replace('start_b<=start_all[25];', '')
    core = core.replace('else if(start_b)begin zseen[2]<=0;zseen[3]<=0;end', 'else if(start_b_copy[1])begin zseen[2]<=0;zseen[3]<=0;end')
    core = core.replace('zh_start<={4{start_b}};', 'zh_start<={4{start_b_copy[2]}};')
    core = replace(core, '''    wire [4:0] rn;
    ot_rst_pipe #(.REGIONS(5),.STAGES(2)) u_rr (.clk(clk),.rst_n_in(rst_n),.rst_n(rn));''', '''    wire [23:0] rn;
    ot_ahub6_reset_two #(.COPIES(24)) u_rr (.ck(clk),.d(rst_n),.q(rn));''')
    # Split the bookkeeping roots without changing their reset edge or data age.
    core = core.replace('age<=0;', '').replace('epoch<=0;parity<=0;layer<=0;', '')
    core = core.replace('age<=0;epoch<=request_epoch;parity<=active_layer_parity;layer<=active_layer;', '')
    core = core.replace('epoch<=request_epoch;parity<=active_layer_parity;layer<=active_layer;', '')
    core = core.replace("            else if(active && age!=16'hffff)age<=age+1'b1;", '')
    core = replace(core, '    always @(posedge clk)begin any_b<=si_any;', '''    always @(posedge clk or negedge rn[5])
        if(!rn[5])age<=0;else if(start_all[25])age<=0;else if(active && age!=16'hffff)age<=age+1'b1;
    always @(posedge clk or negedge rn[6])
        if(!rn[6])begin epoch<=0;parity<=0;layer<=0;end
        else if(start_all[25])begin epoch<=request_epoch;parity<=active_layer_parity;layer<=active_layer;end
    always @(posedge clk)begin any_b<=si_any;''')
    begin = core.index('    always @(posedge clk or negedge rn[1])\n        if(!rn[1])begin lany<=0;')
    end = core.index('    always @(posedge clk)for(integer a=0;a<4;a=a+1)if(lm_b[a])', begin)
    core = core[:begin] + '''    always @(posedge clk or negedge rn[1])
        if(!rn[1]) lany<=0;
        else if(start_b_copy[0]) lany<=0;
        else for(integer a=0;a<4;a=a+1) if(lm_b[a]) lany[4*a+hh_b[2*a+:2]]<=any_b[a];
    always @(posedge clk or negedge rn[2])
        if(!rn[2]) lm_seen<=0;
        else if(start_b_copy[1]) lm_seen<=0;
        else for(integer a=0;a<4;a=a+1) if(lm_b[a]) lm_seen[4*a+hh_b[2*a+:2]]<=1;
    always @(posedge clk or negedge rn[4])
        if(!rn[4]) done_seen<=0;
        else if(start_b_copy[2]) done_seen<=0;
        else for(integer a=0;a<4;a=a+1) if(done_slot[a]) done_seen[a]<=1;
    for(genvar sh=0;sh<4;sh=sh+1) begin:g_seen_head
        wire [23:0] local_hk;
        wire [3:0] local_z;
        ot_ahub6_word #(.W(24),.ID(200+sh)) u_hk(.ck(clk),.d({slot_h,slot_k}),.q(local_hk));
        ot_ahub6_async_word #(.W(4),.ID(220+sh)) u_z(.ck(clk),.rn(rn[16+sh]),.d(start_all[25]?4'd0:z_slot),.q(local_z));
        for(genvar c=0;c<4;c=c+1) begin:g_chunk
            ot_ahub6_seen_bits #(.HEAD(sh),.BASE(16*c),.ID(sh*4+c)) u_bits(
                .ck(clk),.rn(rn[8+sh*2+c/2]),.clear(start_b_copy[4+sh*4+c]),
                .z(local_z),.hk(local_hk),.q(zseen[sh][16*c+:16]));
        end
        // Original indices have a zero MSB; the upper half is reset-only zero.
        always @(posedge clk or negedge rn[20+sh])
            if(!rn[20+sh])zseen[sh][127:64]<=0;
            else if(start_b_copy[4+sh*4])zseen[sh][127:64]<=0;
    end
''' + core[end:]
    core = replace(core, '    reg first_q;', '''    wire [3:0] first_copy;
    wire first_q=first_copy[0];
    for(genvar c=0;c<4;c=c+1) begin:g_first_copy
        ot_ahub6_async_copy #(.ID(300+c),.INIT(1)) u_ff(.ck(clk),.rn(rn[0]),.d(start_all[25] || (first_q && !active)),.q(first_copy[c]));
    end''')
    core = core.replace('first_q<=1;', '').replace('            first_q<=start_all[25] || (first_q && !active);\n', '')
    core = core.replace('slot_h=first_q?', 'slot_h=first_copy[1]?').replace('slot_k=first_q?', 'slot_k=first_copy[2]?').replace('pair_base=first_q?', 'pair_base=first_copy[3]?')
    core = core.replace('always @(posedge clk or negedge rn[3])\n        if(!rn[3])begin tq<=0;', 'always @(posedge clk or negedge rn[20])\n        if(!rn[20])begin tq<=0;')
    core = replace(core, '''    always @(posedge clk)begin
        zh_we<=0;zh_sid<={4{data_b}};
        for(integer a=0;a<4;a=a+1)if(z_b[a])zh_we[128*hh_b[2*a+:2]+{1'b0,k_b[4*a+:4],2'(a)}]<=1;
    end''', '''    always @(posedge clk)zh_sid<={4{data_b}};
    for(genvar sh=0;sh<4;sh=sh+1)begin:g_write_head
        for(genvar c=0;c<4;c=c+1)begin:g_chunk
            ot_ahub6_write_bits #(.HEAD(sh),.BASE(16*c),.ID(sh*4+c)) u_bits(
                .ck(clk),.z(g_seen_head[sh].local_z),.hk(g_seen_head[sh].local_hk),.q(zh_we[128*sh+16*c+:16]));
        end
        always @(posedge clk)zh_we[128*sh+64+:64]<=0;
    end''')
    # Distribute same-edge command consumers; local one-hot computation is
    # shared only within one stack, rather than broadcasting a binary select.
    core=core.replace("lm_sel[ls][sl]<=4'd1<<(start_all[25]?", "lm_sel[ls][sl]<=4'd1<<(start_all[25+ls]?")
    core=core.replace("ret_sel[sl]<=4'd1<<(start_all[25]?", "ret_sel[sl]<=4'd1<<(start_all[28]?")
    core=core.replace('q_mh<=start_all[25]?', 'q_mh<=start_all[29]?').replace('q_rh<=start_all[25]?', 'q_rh<=start_all[29]?').replace('q_th<=start_all[25]?', 'q_th<=start_all[29]?')
    core=core.replace("q_rs<=4'd1<<(start_all[25]?", "q_rs<=4'd1<<(start_all[29]?")
    core=core.replace('else if(start_all[25])age<=0;', 'else if(start_all[26])age<=0;')
    core=core.replace('else if(start_all[25])begin epoch<=', 'else if(start_all[27])begin epoch<=')
    core=core.replace(".d(start_all[25]?4'd0:z_slot)", ".d(start_all[0]?4'd0:z_slot)")
    core=core.replace("zh_iv<=start_all[25]?", "zh_iv<=start_all[28]?")
    core=core.replace('m_issue&&!start_all[25]', 'm_issue&&!start_all[29]').replace('ma_v&&!start_all[25]', 'ma_v&&!start_all[29]').replace('mb_v&&!start_all[25]', 'mb_v&&!start_all[29]')
    core=core.replace('recip_issue&&!start_all[25]', 'recip_issue&&!start_all[29]').replace('recip_return&&!start_all[25]', 'recip_return&&!start_all[29]')
    core=core.replace('pub_hit && !start_all[25]', 'pub_hit && !start_all[29]')
    core=core.replace('    reg [31:0] lm[0:15];', '    wire [31:0] lm[0:15];')
    core=replace(core, '    always @(posedge clk)for(integer a=0;a<4;a=a+1)if(lm_b[a])lm[4*a+hh_b[2*a+:2]]<=data_b[32*a+:32];', '''    for(genvar a=0;a<4;a=a+1)begin:g_lm_store
        for(genvar h=0;h<4;h=h+1)begin:g_head
            for(genvar c=0;c<4;c=c+1)begin:g_chunk
                ot_ahub6_lm_word #(.HEAD(h),.ID(a*16+h*4+c)) u_word(
                    .ck(clk),.en(lm_b[a]),.head(hh_b[2*a+:2]),.d(data_b[32*a+8*c+:8]),.q(lm[4*a+h][8*c+:8]));
            end
        end
    end''')
    # Decoder active copies share the original update edge, not an added stage.
    core = replace(core, '    reg active,parity;', '''    wire [1:0] active_decode;
    for(genvar c=0;c<2;c=c+1) begin:g_active_copy
        ot_ahub6_async_copy #(.ID(440+c)) u_ff(.ck(clk),.rn(rn[0]),.d(start_all[25] || active),.q(active_decode[c]));
    end
    reg active,parity;''')
    core = core.replace('u_dn (.edge_age(e_next),.active(active),', 'u_dn (.edge_age(e_next),.active(active_decode[0]),')
    core = core.replace("u_d1 (.edge_age(17'd1),.active(active),", "u_d1 (.edge_age(17'd1),.active(active_decode[1]),")
    # A single age-subtractor/decode graph still has >32-load arithmetic nodes.
    # Partition by semantic output, with same-edge age/state copies per group.
    dec=replace(dec, 'parameter integer Z_LEVEL_GAP=10', 'parameter integer Z_LEVEL_GAP=10, GROUP=-1')
    dec=replace(dec, 'for(integer s=0;s<4;s=s+1)begin\n            if(active', 'for(integer s=0;s<4;s=s+1)begin\n          if(GROUP<0 || GROUP==s)begin\n            if(active')
    dec=replace(dec, '==nblk[s];\n        end\n    end', '==nblk[s];\n          end\n        end\n    end')
    for name,group in [('m_issue',4),('recip_issue',6),('recip_return',7),('pub_hit',8)]:
        dec=dec.replace('assign '+name+'=', 'assign '+name+'=(GROUP<0 || GROUP=='+str(group)+') && ')
    for name,rhs,group in [('mh','dmi[1:0]',4),('recip_head','dri[1:0]',6),('return_head','drr[1:0]',7)]:
        dec=dec.replace('assign '+name+'='+rhs+';', 'assign '+name+'=(GROUP<0 || GROUP=='+str(group)+')?'+rhs+':0;')
    dec=dec.replace('if(active && !dzs[17]', 'if((GROUP<0 || GROUP==5) && active && !dzs[17]')
    core=core.replace('wire [1:0] active_decode;', 'wire [8:0] active_decode;').replace('c<2;c=c+1) begin:g_active_copy', 'c<9;c=c+1) begin:g_active_copy')
    core=core.replace('wire [23:0] rn;', 'wire [31:0] rn;').replace('ot_ahub6_reset_two #(.COPIES(24))', 'ot_ahub6_reset_two #(.COPIES(32))')
    core=core.replace('    reg [15:0] age;', '    wire [15:0] age;')
    core=replace(core, '''    always @(posedge clk or negedge rn[5])
        if(!rn[5])age<=0;else if(start_all[26])age<=0;else if(active && age!=16'hffff)age<=age+1'b1;''', '''    wire [15:0] age_next=start_all[26]?16'd0:(active && age!=16'hffff)?age+16'd1:age;
    ot_ahub6_async_word #(.W(16),.ID(600)) u_age(.ck(clk),.rn(rn[5]),.d(age_next),.q(age));''')
    output_types={'lm_slot':4,'z_slot':4,'done_slot':4,'slot_h':8,'slot_k':16,'m_issue':1,'mh':2,'issue':4,'pair_base':6,'recip_issue':1,'recip_return':1,'recip_head':2,'return_head':2,'pub_hit':1}
    short={'lm_slot':'lm','z_slot':'z','done_slot':'dn','slot_h':'sh','slot_k':'sk','m_issue':'mi','mh':'mh','issue':'is','pair_base':'pa','recip_issue':'ri','recip_return':'rr','recip_head':'rh','return_head':'th','pub_hit':'pb'}
    gen=['    wire [16:0] decode_age[0:8];']
    for pre in ('n','o'):
        for name,w in output_types.items():gen.append(f'    wire [{w-1}:0] dec_{pre}_{name}[0:8];')
    gen.append('''    for(genvar dg=0;dg<9;dg=dg+1)begin:g_decode
        wire [15:0] local_age;
        if(dg<8)begin:g_age
            ot_ahub6_async_word #(.W(16),.ID(601+dg)) u_ff(.ck(clk),.rn(rn[24+dg]),.d(age_next),.q(local_age));
        end else begin:g_original assign local_age=age;end
        assign decode_age[dg]=(MUT==4)?{1'b0,local_age}+17'd1:(active_decode[dg] && local_age!=16'hffff)?{1'b0,local_age}+17'd2:{1'b0,local_age}+17'd1;
''')
    common=['.LMAX_IN_AGE(LMAX_IN_AGE)','.Z_IN_AGE(Z_IN_AGE)','.LMAX_ISSUE_AGE(LMAX_ISSUE_AGE)','.Z_START_AGE(Z_START_AGE)','.RECIP_ISSUE_AGE(RECIP_ISSUE_AGE)','.RECIP_RETURN_AGE(RECIP_RETURN_AGE)','.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE)','.nblk_v(nblk_q)']
    for pre,edge in [('n','decode_age[dg]'),('o',"17'd1")]:
        ports=[f'.edge_age({edge})','.active(active_decode[dg])']+common+[f'.{name}(dec_{pre}_{name}[dg])' for name in output_types]
        gen.append('qkd_ahub_static_dec_safe #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP),.GROUP(dg)) u_'+pre+'('+','.join(ports)+');')
    gen.append('end')
    for pre in ('n','o'):
        for name,w in output_types.items():
            out=pre+'_'+short[name]
            if name in ('lm_slot','z_slot','done_slot','slot_h','slot_k'):
                step=w//4
                for g in range(4):
                    sl=f'[{g}]' if step==1 else f'[{g*step}+:{step}]'
                    gen.append(f'assign {out}{sl}=dec_{pre}_{name}[{g}]{sl};')
            else:
                group={'m_issue':4,'mh':4,'issue':5,'pair_base':5,'recip_issue':6,'recip_head':6,'recip_return':7,'return_head':7,'pub_hit':8}[name]
                gen.append(f'assign {out}=dec_{pre}_{name}[{group}];')
    pat=r'    qkd_ahub_static_dec_safe #\(.*?\) u_dn \(.*?\);\n    qkd_ahub_static_dec_safe #\(.*?\) u_d1 \(.*?\);'
    core,n=re.subn(pat,'\n'.join(gen),core,flags=re.S)
    assert n==1,n
    core=core.replace('    reg [31:0] rz[0:3];', '    wire [31:0] rz[0:3];')
    core=replace(core, '''            always @(posedge clk)
                if(recip_return && ret_sel[sl][rh])rz[rh][8*sl+:8]<=rc_y[8*sl+:8];''', '''            ot_ahub6_rz_word #(.ID(rh*4+sl)) u_word(.ck(clk),.en(recip_return),.sel(ret_sel[sl][rh]),.d(rc_y[8*sl+:8]),.q(rz[rh][8*sl+:8]));''')
    result = '\n\n'.join((io, dec, core))
    for name in names:
        result = result.replace(name, name.replace('qkd_ahub_static_', 'qkd_ahub6_static_'))
    helper = '''
(* keep_hierarchy="yes" *)
module ot_ahub6_async_copy #(parameter integer ID=0,INIT=0)(input wire ck,rn,d,output wire q);
    (* keep=1 *) reg value;
    always @(posedge ck or negedge rn) if(!rn)value<=INIT;else value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_word #(parameter integer W=24,ID=0)(input wire ck,input wire [W-1:0] d,output wire [W-1:0] q);
    (* keep=1 *) reg [W-1:0] value;
    always @(posedge ck)value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_lm_word #(parameter integer HEAD=0,ID=0)(input wire ck,en,input wire [1:0] head,input wire [7:0] d,output wire [7:0] q);
    (* keep=1 *) reg [7:0] value;
    always @(posedge ck)if(en && head==2'(HEAD))value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_rz_word #(parameter integer ID=0)(input wire ck,en,sel,input wire [7:0] d,output wire [7:0] q);
    (* keep=1 *) reg [7:0] value;
    always @(posedge ck)if(en && sel)value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_head_copy #(parameter integer ID=0)(input wire ck,start,input wire [1:0] first,next_head,output wire [3:0] q);
    (* keep=1 *) reg [3:0] value;
    always @(posedge ck)value<=4'd1<<(start?first:next_head);
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_async_word #(parameter integer W=4,ID=0)(input wire ck,rn,input wire [W-1:0] d,output wire [W-1:0] q);
    (* keep=1 *) reg [W-1:0] value;
    always @(posedge ck or negedge rn)if(!rn)value<=0;else value<=d;
    assign q=value;
endmodule

module ot_ahub6_reset_two #(parameter integer COPIES=24)(input wire ck,d,output wire [COPIES-1:0] q);
    // Match ot_rst_pipe: asynchronous assertion, two synchronizer stages,
    // then the two plain regional stages. The consumers keep the original age.
    (* keep=1, dont_touch=1 *) reg s0,s1;
    always @(posedge ck or negedge d)
        if(!d)begin s0<=0;s1<=0;end else begin s0<=1;s1<=s0;end
    wire first;
    ot_pl_land_field_copy_bit #(.ID(14000)) u_first(.ck(ck),.d(s1),.q(first));
    for(genvar c=0;c<COPIES;c=c+1)begin:g_copy
        ot_pl_land_field_copy_bit #(.ID(14001+c)) u_ff(.ck(ck),.d(first),.q(q[c]));
    end
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_seen_bits #(parameter integer HEAD=0,BASE=0,ID=0)(
    input wire ck,rn,clear,input wire [3:0] z,input wire [23:0] hk,output reg [15:0] q
);
    for(genvar j=0;j<16;j=j+1)begin:g_bit
        localparam integer A=(BASE+j)%4;
        always @(posedge ck or negedge rn)
            if(!rn)q[j]<=0;
            else if(clear)q[j]<=0;
            else if(z[A] && hk[16+2*A+:2]==2'(HEAD) && hk[4*A+:4]==4'((BASE+j)/4))q[j]<=1;
    end
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_write_bits #(parameter integer HEAD=0,BASE=0,ID=0)(
    input wire ck,input wire [3:0] z,input wire [23:0] hk,output reg [15:0] q
);
    for(genvar j=0;j<16;j=j+1)begin:g_bit
        localparam integer A=(BASE+j)%4;
        always @(posedge ck)
            q[j]<=z[A] && hk[16+2*A+:2]==2'(HEAD) && hk[4*A+:4]==4'((BASE+j)/4);
    end
endmodule

module ot_ahub6_reset_pad #(parameter integer N=7,COPIES=4)(input wire ck,d,output wire [COPIES-1:0] q);
    wire prefix;
    ot_pl_pad #(.W(1),.N(N-1)) u_prefix(.ck(ck),.d(d),.q(prefix));
    for(genvar c=0;c<COPIES;c=c+1) begin:g_copy
        ot_pl_land_field_copy_bit #(.ID(12000+c)) u_ff(.ck(ck),.d(prefix),.q(q[c]));
    end
endmodule
'''
    OUT.write_text('// Generated AHUB6 private partial controls; native census and behavioral qualification mandatory.\n'+result+'\n'+helper)
    print(OUT)


if __name__ == '__main__':
    main()
