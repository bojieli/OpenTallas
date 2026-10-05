`timescale 1ps/1ps
// Opt-in HBROM prototype, analytically admitted TP4/128 pairs/tile, 2026-10-05.
// Fixed dedicated return port: the SM reserves its ring slot before req acceptance.
// No response backpressure, ROM ECC, arbitrary address LUT, or ideal ROM bypass.
module ot_hbrom_rom_feed #(
    parameter integer ENABLE=0, PAIRS=128, PROTECT=1,
    parameter integer GROUPS=PAIRS/4,
    parameter integer LEVELS=($clog2(GROUPS)+1)/2,
    parameter integer LAT=6+LEVELS
)(
    input wire clk,rst_n,
    input wire cfg_valid, output wire cfg_ready,
    input wire [1:0] cfg_fmt,
    input wire [12:0] cfg_rows,
    input wire [7:0] cfg_groups,
    input wire cfg_group_slot,
    input wire [31:0] cfg_base_record,cfg_region_records,cfg_virtual_base,
    input wire [15:0] cfg_epoch,
    input wire req_v, output wire req_ready,
    input wire [31:0] req_addr, input wire [9:0] req_tag,
    output reg rsp_v, output reg [9:0] rsp_tag,
    output reg [1087:0] rsp_data,
    input wire cancel, output wire cancel_done, output wire idle,
    output reg fault,
    output wire [2*PAIRS-1:0] rom_ce,
    output wire [2*PAIRS*12-1:0] rom_addr,
    input wire [2*PAIRS*274-1:0] rom_q,
    output wire [2*PAIRS-1:0] capture_ce
);
    localparam integer GW=(GROUPS<=1)?1:$clog2(GROUPS);
    localparam integer MW=32+10+16;
    (* keep = "true", dont_touch = "true" *) reg configured,draining;
    (* keep = "true", dont_touch = "true" *) reg configured1,draining1;
    (* keep = "true", dont_touch = "true" *) reg [1:0] fmt0,fmt1;
    (* keep = "true", dont_touch = "true" *) reg [15:0] epoch0,epoch1;
    (* keep = "true", dont_touch = "true" *) reg [LAT-1:0] valid0,valid1;
    (* keep = "true", dont_touch = "true" *) reg [MW-1:0] meta0[0:LAT-1],meta1[0:LAT-1];
    (* keep = "true", dont_touch = "true" *) reg [1023:0] live0,live1;
    wire [31:0] phys0,phys1,expect0,expect1;
    wire exhausted0,exhausted1;
    wire [767:0] seal0,seal1;
    reg [1:0] launch_history0,launch_history1;
    wire launch_fire;
    wire pipe_bad;
    wire controller_bad=PROTECT && ((seal0!=seal1)||(fmt0!=fmt1)||(epoch0!=epoch1)||
                               (launch_history0!=launch_history1)||(configured!=configured1)||(draining!=draining1)||(valid0!=valid1)||(live0!=live1)||pipe_bad);
    wire [32:0] cfg_total={20'd0,cfg_rows}*{25'd0,cfg_groups}*33'd8;
    wire [32:0] cfg_end={1'b0,cfg_base_record}+{1'b0,cfg_region_records};
    wire cfg_bad=(cfg_rows==0)||(cfg_rows>4096)||(cfg_groups==0)||(cfg_groups>16)||
                 (cfg_fmt>2)||({1'b0,cfg_region_records}<cfg_total)||
                 (cfg_end>GROUPS*8192)||({1'b0,cfg_virtual_base}+cfg_total>33'h100000000);
    assign idle=!(|valid0)&&!rsp_v;
    assign cfg_ready=(ENABLE!=0)&&!fault&&!configured&&!draining&&idle;
    wire set_cfg=cfg_valid&&cfg_ready&&!cfg_bad;
    // Previous accepted request arrives at the macro one cycle before this one.
    // Different bank groups are different macros even when parity is identical.
    wire same_macro=valid0[0] && (meta0[0][MW-1 -:32]>>13==phys0>>13) &&
                    (meta0[0][29]==phys0[3]);
    wire bad_request=configured&&req_v&&((req_addr!=expect0)||exhausted0||live0[req_tag]);
    assign req_ready=(ENABLE!=0)&&configured&&!draining&&!cancel&&!fault&&!controller_bad&&
                     !same_macro&&!exhausted0&&!live0[req_tag]&&(req_addr==expect0);
    wire accept=req_v&&req_ready;
    (* keep_hierarchy = "yes", dont_touch = "true" *) ot_hbrom_feed_cursor u_cursor0(.clk(clk),.rst_n(rst_n),.load(set_cfg),.advance(accept),
        .rows(cfg_rows),.groups(cfg_groups),.group_slot(cfg_group_slot),
        .base(cfg_base_record),.virtual_base(cfg_virtual_base),
        .physical(phys0),.expected_addr(expect0),.exhausted(exhausted0),.seal(seal0));
    (* keep_hierarchy = "yes", dont_touch = "true" *) ot_hbrom_feed_cursor u_cursor1(.clk(clk),.rst_n(rst_n),.load(set_cfg),.advance(accept),
        .rows(cfg_rows),.groups(cfg_groups),.group_slot(cfg_group_slot),
        .base(cfg_base_record),.virtual_base(cfg_virtual_base),
        .physical(phys1),.expected_addr(expect1),.exhausted(exhausted1),.seal(seal1));
    wire [LAT-1:0] mismatch;
    genvar d;
    generate for(d=0;d<LAT;d=d+1) begin:g_compare
        assign mismatch[d]=valid0[d]&&(meta0[d]!=meta1[d]);
    end endgenerate
    assign pipe_bad=|mismatch;
    wire deliver=valid0[LAT-1]&&!fault&&!controller_bad&&!draining&&!cancel;
    assign cancel_done=draining&&idle;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            configured<=0;draining<=0;configured1<=0;draining1<=0;fmt0<=0;fmt1<=0;epoch0<=0;epoch1<=0;
            launch_history0<=0;launch_history1<=0;valid0<=0;valid1<=0;live0<=0;live1<=0;fault<=0;rsp_v<=0;rsp_tag<=0;
        end else begin
            if((cfg_valid&&cfg_ready&&cfg_bad)||bad_request||controller_bad) fault<=1;
            if(cancel) begin draining<=1;draining1<=1;end
            if(cancel_done) begin draining<=0;configured<=0;draining1<=0;configured1<=0;end
            if(set_cfg) begin configured<=1;configured1<=1;fmt0<=cfg_fmt;fmt1<=cfg_fmt;epoch0<=cfg_epoch;epoch1<=cfg_epoch; end
            if(configured&&exhausted0&&idle) begin configured<=0;configured1<=0;end
            launch_history0<={launch_history0[0],launch_fire};
            launch_history1<={launch_history1[0],launch_fire};
            valid0<={valid0[LAT-2:0],accept};
            valid1<={valid1[LAT-2:0],accept};
            if(accept) begin live0[req_tag]<=1;live1[req_tag]<=1;end
            if(valid0[LAT-1]) begin
                live0[meta0[LAT-1][25:16]]<=0;
                live1[meta1[LAT-1][25:16]]<=0;
            end
            rsp_v<=deliver;
            if(deliver) rsp_tag<=meta0[LAT-1][25:16];
        end
    end
    always @(posedge clk) begin
        meta0[0]<={phys0,req_tag,epoch0};meta1[0]<={phys1,req_tag,epoch1};
        for(k=1;k<LAT;k=k+1) begin meta0[k]<=meta0[k-1];meta1[k]<=meta1[k-1];end
    end
    wire [31:0] launch_phys=meta0[1][MW-1 -:32];
    wire [31:0] capture_phys=meta0[3][MW-1 -:32];
    (* keep = "true", dont_touch = "true" *) reg [273:0] captured[0:2*PAIRS-1];
    (* keep = "true", dont_touch = "true" *) reg [273:0] pair_word[0:PAIRS-1];
    assign launch_fire=(ENABLE!=0)&&valid0[1]&&!fault&&!controller_bad&&!draining&&!cancel;
    genvar p;
    generate for(p=0;p<2*PAIRS;p=p+1) begin:g_rom
        localparam integer BG=p/8,PAR=p%2;
        assign rom_ce[p]=launch_fire&&
                         (launch_phys>>13==BG)&&(launch_phys[3]==(PAR!=0));
        assign rom_addr[p*12 +:12]={launch_phys[12:4],launch_phys[2:0]};
        assign capture_ce[p]=(ENABLE!=0)&&launch_history0[1]&&!fault&&!controller_bad&&
                         (capture_phys>>13==BG)&&(capture_phys[3]==(PAR!=0));
        always @(posedge clk) if(capture_ce[p]) captured[p]<=rom_q[274*p +:274];
    end
    for(p=0;p<PAIRS;p=p+1) begin:g_pair
        always @(posedge clk) if(valid0[4])
            pair_word[p]<=meta0[4][29]?captured[2*p+1]:captured[2*p];
    end endgenerate
    // Registered four-way tree. Extra children of an incomplete level are +0.
    wire [1095:0] root_word;
    genvar s,l,n;
    generate for(s=0;s<4;s=s+1) begin:g_stream
        wire [273:0] tree[0:LEVELS][0:GROUPS-1];
        for(n=0;n<GROUPS;n=n+1) begin:g_leaf
            assign tree[0][n]=pair_word[4*n+s];
        end
        for(l=0;l<LEVELS;l=l+1) begin:g_level
            localparam integer NN=(GROUPS+(1<<(2*(l+1)))-1)>>(2*(l+1));
            localparam integer PRE=(GROUPS+(1<<(2*l))-1)>>(2*l);
            wire [1:0] sel=meta0[5+l][26+13+2*l +:2];
            for(n=0;n<NN;n=n+1) begin:g_node
                (* keep = "true", dont_touch = "true" *) reg [273:0] q;
                wire [273:0] a=tree[l][4*n];
                wire [273:0] b=(4*n+1<PRE)?tree[l][4*n+1]:274'd0;
                wire [273:0] c=(4*n+2<PRE)?tree[l][4*n+2]:274'd0;
                wire [273:0] e=(4*n+3<PRE)?tree[l][4*n+3]:274'd0;
                always @(posedge clk) if(valid0[5+l])
                    case(sel) 0:q<=a;1:q<=b;2:q<=c;3:q<=e;endcase
                assign tree[l+1][n]=q;
            end
        end
        assign root_word[274*s +:274]=tree[LEVELS][0];
    end endgenerate
    integer stream;
    (* keep = "true", dont_touch = "true" *) reg [1087:0] swizzled;
    always @* begin
        swizzled=0;
        for(stream=0;stream<4;stream=stream+1) begin
            if(fmt0==2) begin
                swizzled[256*stream +:128]=root_word[274*stream +:128];
                swizzled[256*stream+128 +:128]=root_word[274*stream+136 +:128];
                swizzled[1024+16*stream +:8]=root_word[274*stream+128 +:8];
                swizzled[1032+16*stream +:8]=root_word[274*stream+264 +:8];
            end else begin
                swizzled[256*stream +:256]=root_word[274*stream +:256];
                if(fmt0==1) swizzled[1024+8*stream +:8]=root_word[274*stream+256 +:8];
            end
        end
    end
    always @(posedge clk) if(deliver) rsp_data<=swizzled;
endmodule

// Sequential compact line request translator. Owns no weight payload or LUT.
module ot_hbrom_feed_cursor(
    input wire clk,rst_n,load,advance,
    input wire [12:0] rows,input wire [7:0] groups,input wire group_slot,
    input wire [31:0] base,virtual_base,
    output wire [31:0] physical,output reg [31:0] expected_addr,
    output wire exhausted, output wire [767:0] seal
);
    reg mode;
    (* keep = "true", dont_touch = "true" *) reg [7:0] gcount,g;
    (* keep = "true", dont_touch = "true" *) reg [2:0] t,slot;
    (* keep = "true", dont_touch = "true" *) reg [3:0] count;
    (* keep = "true", dont_touch = "true" *) reg [23:0] remaining;
    (* keep = "true", dont_touch = "true" *) reg [31:0] next_base,stride;
    (* keep = "true", dont_touch = "true" *) reg [31:0] bases[0:7];
    wire [23:0] initial_items=group_slot?({11'd0,rows}*{16'd0,groups}):{11'd0,rows};
    wire [23:0] remaining_next=remaining-{20'd0,count};
    wire [31:0] chosen=(mode&&(t==0))?next_base:bases[slot];
    assign physical=chosen+{29'd0,t}+(mode?32'd0:{21'd0,g,3'd0});
    assign exhausted=(remaining==0);
    assign seal={365'd0,mode,gcount,g,t,slot,count,remaining,next_base,stride,expected_addr,
                 bases[7],bases[6],bases[5],bases[4],bases[3],bases[2],bases[1],bases[0]};
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            mode<=0;gcount<=0;g<=0;t<=0;slot<=0;count<=0;remaining<=0;
            next_base<=0;stride<=0;expected_addr<=0;
            for(i=0;i<8;i=i+1) bases[i]<=0;
        end else if(load) begin
            mode<=group_slot;gcount<=groups;g<=0;t<=0;slot<=0;
            remaining<=initial_items;
            count<=(initial_items>=24'd8)?4'd8:initial_items[3:0];
            stride<={21'd0,groups,3'd0};next_base<=base;expected_addr<=virtual_base;
            for(i=0;i<8;i=i+1) bases[i]<=base+i*({24'd0,groups}<<3);
        end else if(advance) begin
            expected_addr<=expected_addr+1;
            if(mode&&t==0) begin bases[slot]<=next_base;next_base<=next_base+8;end
            if(slot+1<count) slot<=slot+1;
            else begin
                slot<=0;
                if(t!=7) t<=t+1;
                else begin
                    t<=0;
                    if(!mode&&g+1<gcount) g<=g+1;
                    else begin
                        g<=0;remaining<=remaining_next;
                        count<=(remaining_next>=24'd8)?4'd8:remaining_next[3:0];
                        if(!mode) for(i=0;i<8;i=i+1) bases[i]<=bases[i]+(stride<<3);
                    end
                end
            end
        end
    end
endmodule
