`timescale 1ns/1ps
`default_nettype none
// Opt-in wide successor. Raw272-bit transport is routed BEFORE local expansion.
// Default disabled; physical placement/adoption remains independently gated.
module ot_hgi_dma_front_wide #(
 parameter integer ENABLE=0,NS=4,NL=32,NB=512,LDEPTH=256,SBIT=35,
 parameter [35:0] STACK_BYTES=36'd22500000000,
 parameter integer IP=$clog2(NS*NL),LP=$clog2(LDEPTH)
)(input wire clk,rst_n,input wire mv_v,output wire mv_rdy,input wire[226:0]mv,
 output reg mv_done,mv_fault,
 output reg [NS*53-1:0]dq,input wire[NS-1:0]dq_rdy,
 input wire[NS*NL*272-1:0]dd,output reg[NS*NL-1:0]dd_cr,
 output wire[NB*283-1:0]wl,input wire[NB-1:0]wl_ready,wl_done);
 localparam integer NIN=NS*NL,NTILE=NB/4,LD=LDEPTH;
 initial if(NB!=512 || NS!=4 || LDEPTH<4 || (1<<LP)!=LDEPTH)$fatal(1,"wide front sized parameters");
    // ---------------------------------------------------------------- command station (registered)
    reg cv_q; reg [226:0] cm_q;
    reg busy; reg [2:0] sf; reg [1:0] ks;                  // ks = log2 K (destination sectors per source sector)
    reg [36:0] ra; reg [31:0] sst;                          // the current row's source byte address, row stride
    reg [31:0] rdw; reg [31:0] dst_w;                       // the current row's VM word address, row stride
    // rows are issued in windows of up to 4 (round robin chunk by chunk: rows striped over the stacks keep all stacks busy)
    reg [19:0] r_left;                                      // rows left after the current window
    reg [1:0] wi, wn;                                       // the window row being issued, the window's last row
    reg [36:0] wa; reg [31:0] wd;                           // that row's source byte address, VM word address
    reg [23:0] rsec, r_off;                                 // sectors a row, the chunk's first sector (all window rows)
    reg r_done;
    reg [31:0] issued, wrote;                               // destination sectors requested / acknowledged
    assign mv_rdy = ENABLE && !busy && !cv_q && !mv_fault;
    // ---------------------------------------------------------------- tags
    localparam integer NT = NS*64;
    reg [NT-1:0] tag_busy;
    reg [17:0] tg_dsec [0:NT-1];                              // the run's first VM sector
    reg [8:0]  tg_total [0:NT-1];                              // beats still to land
    reg [6:0] ft;
    function automatic integer tag_slot(input integer stack, tag);
        tag_slot = stack*64+tag;
    endfunction
    wire [36:0] next_addr = wa + {r_off[22:0], 5'd0};
    wire [1:0] next_stack = next_addr[SBIT +: 2];
    always @* begin
        ft = 7'd64;
        for (integer t = 63; t >= 0; t = t - 1)
            if (!tag_busy[tag_slot(next_stack,t)]) ft = 7'(t);
    end

 reg [255:0] tg_seen[0:NT-1],tg_seen_n[0:NT-1];
 reg [NT-1:0] tag_busy_n;
 reg [26:0] tg_meta_n[0:NT-1];
 reg [NIN*272-1:0]dd_r;
 // Finite reserved landing buffers; mirrored payload/control fails closed.
 // Actual protected macro realization remains a separate physical gate.
 reg [273:0] lq[0:NIN*LD-1],lq_nrail[0:NIN*LD-1];
 reg [LP-1:0] lq_h[0:NIN-1],lq_t[0:NIN-1];
 reg [LP:0]lq_n[0:NIN-1],lq_count_n[0:NIN-1];
 reg [NIN-1:0]cur_v;reg[17:0]cur_sec[0:NIN-1];reg[255:0]cur_d[0:NIN-1];
 reg [3:0]pending[0:NIN-1],gnt[0:NIN-1];
 reg [IP-1:0]rr_lane; reg [277:0]cur_rail[0:NIN-1];reg [NIN-1:0]cur_v_n;
 reg [3:0]trv[0:NTILE-1];wire[3:0]trr[0:NTILE-1];
 reg [71:0]trs[0:NTILE-1];reg[1023:0]trd[0:NTILE-1];
 reg [7:0]trf[0:NTILE-1];reg[15:0]trm[0:NTILE-1];
 wire[3:0]tbv[0:NTILE-1],tbr[0:NTILE-1];wire[71:0]tbs[0:NTILE-1];
 wire[1023:0]tbd[0:NTILE-1];wire[31:0]tbm[0:NTILE-1];wire[NTILE-1:0]tfault;
 generate for(genvar tile=0;tile<NTILE;tile=tile+1)begin:g_tile
 ot_hgi_dma_wide_convert_tile #(.ENABLE(ENABLE),.TILE(tile),.NB(NB))u_tile(
 .clk(clk),.rst_n(rst_n),.raw_v(trv[tile]),.raw_r(trr[tile]),.raw_sec(trs[tile]),.raw_data(trd[tile]),
 .raw_fmt(trf[tile]),.raw_piece_mask(trm[tile]),.bank_v(tbv[tile]),.bank_r(tbr[tile]),
 .bank_sec(tbs[tile]),.bank_data(tbd[tile]),.bank_word_mask(tbm[tile]),.fault(tfault[tile]));
 for(genvar bank=0;bank<4;bank=bank+1)begin:g_pin
 assign wl[(tile*4+bank)*283+:283]={tbv[tile][bank],tbs[tile][bank*18+:18],tbd[tile][bank*256+:256],tbm[tile][bank*8+:8]};
 assign tbr[tile][bank]=wl_ready[tile*4+bank];
 end end endgenerate
 integer ti,sl,li,jj,ix;reg[3:0]pieces;reg found;
 always @*begin
 for(li=0;li<NIN;li=li+1)gnt[li]=0;
 for(ti=0;ti<NTILE;ti=ti+1)begin
 trv[ti]=0;trs[ti]=0;trd[ti]=0;trf[ti]=0;trm[ti]=0;
 for(sl=0;sl<4;sl=sl+1)begin
 found=0;
 for(li=0;li<NIN;li=li+1)begin
 ix=(int'(rr_lane)+li)%NIN;pieces=0;
 for(jj=0;jj<4;jj=jj+1)
 if(pending[ix][jj] && !gnt[ix][jj] && ((int'(cur_sec[ix])+jj)%NB)/4==ti)pieces[jj]=1;
 if(ENABLE && !mv_fault && trr[ti][sl] && !found && cur_v[ix] && cur_v_n[ix]==!cur_v[ix] && cur_rail[ix]==~{cur_sec[ix],cur_d[ix],pending[ix]} && pieces!=0)begin
 trv[ti][sl]=1;trs[ti][sl*18+:18]=cur_sec[ix];trd[ti][sl*256+:256]=cur_d[ix];
 trf[ti][sl*2+:2]=(sf==1)?2'd1:(sf==2)?2'd2:2'd0;trm[ti][sl*4+:4]=pieces;
 gnt[ix]=gnt[ix]|pieces;found=1;
 end end end end
 end
 wire[NIN-1:0]pop;
 generate for(genvar lane=0;lane<NIN;lane=lane+1)begin:g_pop
 assign pop[lane]=ENABLE&&!mv_fault&&lq_n[lane]!=0&&(!cur_v[lane]||(pending[lane]&~gnt[lane])==0);
 end endgenerate
 wire[3:0]kmask=(ks==0)?4'b1:(ks==1)?4'b11:4'b1111;
 reg[255:0]arrived[0:NT-1];reg bad_arrival;
 integer ai,at;reg[271:0]incoming;reg[7:0]beat;
 always @*begin
 for(at=0;at<NT;at=at+1)arrived[at]=0;
 bad_arrival=0;
 for(ai=0;ai<NIN;ai=ai+1)begin
 incoming=dd_r[ai*272+:272];at=(ai/NL)*64+incoming[269:264];beat=incoming[263:256];
 if(incoming[271])begin
 if(incoming[270] || !tag_busy[at] || {1'b0,beat}>=tg_total[at] || tg_seen[at][beat] || arrived[at][beat] || (lq_n[ai]==LD&&!pop[ai]))bad_arrival=1;
 arrived[at][beat]=1;
 end end
 end
 integer i,s,t,k;reg[271:0]in;reg ok;reg[273:0]payload;integer nd;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
 cv_q<=0;busy<=0;mv_done<=0;mv_fault<=0;dq<=0;dd_cr<=0;dd_r<=0;tag_busy<=0;tag_busy_n<=~{NT{1'b0}};
 r_done<=1;cur_v<=0;cur_v_n<=~{NIN{1'b0}};rr_lane<=0;issued<=0;wrote<=0;
 for(i=0;i<NIN;i=i+1)begin lq_h[i]<=0;lq_t[i]<=0;lq_n[i]<=0;lq_count_n[i]<=~(LP+1)'(0);pending[i]<=0;cur_sec[i]<=0;cur_d[i]<=0;cur_rail[i]<=~278'd0;end
 for(t=0;t<NT;t=t+1)begin tg_seen[t]<=0;tg_seen_n[t]<=~256'd0;tg_total[t]<=0;tg_dsec[t]<=0;tg_meta_n[t]<=~27'd0;end
 end else begin
 mv_done<=0;dd_cr<=0;dd_r<=ENABLE?dd:0;
 if((|tfault)||bad_arrival||tag_busy_n!=~tag_busy)mv_fault<=1;
 for(s=0;s<NS;s=s+1)if(dq_rdy[s])dq[s*53+52]<=0;
            // ---- accept (command station, then the decode)
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (cv_q) begin
                if(cm_q[4:2]!=0 && cm_q[4:2]!=1 && cm_q[4:2]!=2 && cm_q[4:2]!=5)mv_fault<=1;
                cv_q <= 1'b0; busy <= 1'b1; sf <= cm_q[4:2];
                ks <= (cm_q[4:2] == 3'd0 || cm_q[4:2] == 3'd5) ? 2'd0 : (cm_q[4:2] == 3'd1) ? 2'd1 : 2'd2;
                ra <= cm_q[41:5]; sst <= cm_q[76:45]; rdw <= cm_q[129:98]; dst_w <= cm_q[169:138];
                // sectors a row = n x esize / 32
                rsec <= (cm_q[4:2] == 3'd0 || cm_q[4:2] == 3'd5) ? 24'(cm_q[226:206] >> 3) :
                        (cm_q[4:2] == 3'd1) ? 24'(cm_q[226:206] >> 4) : 24'(cm_q[226:206] >> 5);
                wn <= (cm_q[205:186] >= 20'd4) ? 2'd3 : 2'(cm_q[205:186] - 20'd1);
                r_left <= (cm_q[205:186] >= 20'd4) ? cm_q[205:186] - 20'd4 : 20'd0;
                wi <= 2'd0; wa <= cm_q[41:5]; wd <= cm_q[129:98]; r_off <= 24'd0;
                r_done <= (cm_q[205:186] == 20'd0) || (cm_q[226:206] == 21'd0);
                issued <= 32'd0; wrote <= 32'd0;
            end
            // ---- request generator: one request a cycle on a free tag
            if (ENABLE && !mv_fault && busy && !r_done && ft != 7'd64) begin : rq
                reg [36:0] a, e; reg [23:0] rem; reg [8:0] rn; reg [1:0] st;
                a = wa + {r_off[22:0], 5'd0};
                rem = rsec - r_off;
                rn = (rem > 24'd256) ? 9'd256 : rem[8:0];
                e = a + {19'd0, rn, 5'd0} - 37'd1;
                st = a[SBIT +: 2];
                if ((19'(wd>>3)+(19'(r_off)<<ks)+(19'(rn)<<ks))>19'd262144 || e[SBIT +: 2] != st || ({1'b0, a[SBIT-1:0]} + {{(SBIT-13){1'b0}}, rn, 5'd0}) > (SBIT+1)'(STACK_BYTES))
                    mv_fault <= 1'b1;
                else if (!dq[st*53 + 52] || dq_rdy[st]) begin
                    dq[st*53 +: 53] <= {1'b1, ft[5:0], rn, a};
                    tag_busy[int'(st)*64+int'(ft[5:0])] <= 1'b1;
                    tg_dsec[int'(st)*64+int'(ft[5:0])] <= 18'(wd >> 3) + (18'(r_off) << ks);
                    tg_total[int'(st)*64+int'(ft[5:0])] <= rn;
                    tg_seen[int'(st)*64+int'(ft[5:0])] <= 0;tg_seen_n[int'(st)*64+int'(ft[5:0])]<=~256'd0;
                    tg_meta_n[int'(st)*64+int'(ft[5:0])] <= ~{(18'(wd >> 3) + (18'(r_off) << ks)),rn};
                    tag_busy_n[int'(st)*64+int'(ft[5:0])] <= 0;
                    issued <= issued + ({23'd0, rn} << ks);
                    if (wi != wn) begin wi <= wi + 2'd1; wa <= wa + {5'd0,sst}; wd <= wd + dst_w; end
                    else if (r_off + {15'd0, rn} != rsec) begin            // next chunk of the window
                        wi <= 2'd0; wa <= ra; wd <= rdw; r_off <= r_off + {15'd0, rn};
                    end else begin                                         // next window
                        wi <= 2'd0; r_off <= 24'd0; ra <= wa + {5'd0,sst}; rdw <= wd + dst_w;
                        wa <= wa + {5'd0,sst}; wd <= wd + dst_w;
                        if (r_left == 20'd0) r_done <= 1'b1;
                        else begin
                            wn <= (r_left >= 20'd4) ? 2'd3 : 2'(r_left - 20'd1);
                            r_left <= (r_left >= 20'd4) ? r_left - 20'd4 : 20'd0;
                        end
                    end
                end
            end

 if(ENABLE&&!mv_fault)begin
 for(i=0;i<NIN;i=i+1)begin
 if(lq_count_n[i]!=~lq_n[i] || cur_v_n[i]!=!cur_v[i] || cur_rail[i]!=~{cur_sec[i],cur_d[i],pending[i]})mv_fault<=1;
 in=dd_r[i*272+:272];ok=in[271]&&!bad_arrival;
 t=(i/NL)*64+in[269:264];
 if(ok)begin
 payload={tg_dsec[t]+(18'(in[263:256])<<ks),in[255:0]};
 lq[i*LD+lq_t[i]]<=payload;lq_nrail[i*LD+lq_t[i]]<=~payload;lq_t[i]<=lq_t[i]+1'b1;
 end
 if(pop[i])begin
 payload=lq[i*LD+lq_h[i]];
 if(lq_nrail[i*LD+lq_h[i]]!=~payload)mv_fault<=1;
 {cur_sec[i],cur_d[i]}<=payload;lq_h[i]<=lq_h[i]+1'b1;dd_cr[i]<=1;pending[i]<=kmask;
 cur_rail[i]<=~{payload,kmask};end else begin pending[i]<=pending[i]&~gnt[i];cur_rail[i]<=~{cur_sec[i],cur_d[i],(pending[i]&~gnt[i])};end
 cur_v[i]<=pop[i]?1'b1:((pending[i]&~gnt[i])==0)?1'b0:cur_v[i];cur_v_n[i]<=!(pop[i]?1'b1:((pending[i]&~gnt[i])==0)?1'b0:cur_v[i]);
 lq_n[i]<=lq_n[i]+(LP+1)'(ok)-(LP+1)'(pop[i]);lq_count_n[i]<=~(lq_n[i]+(LP+1)'(ok)-(LP+1)'(pop[i]));
 end
 for(t=0;t<NT;t=t+1)begin
 if(tg_seen_n[t]!=~tg_seen[t] || tg_meta_n[t]!=~{tg_dsec[t],tg_total[t]})mv_fault<=1;
 if(arrived[t]!=0&&!bad_arrival)begin
 tg_seen[t]<=tg_seen[t]|arrived[t];tg_seen_n[t]<=~(tg_seen[t]|arrived[t]);k=0;
 for(i=0;i<256;i=i+1)if(tg_seen[t][i]||arrived[t][i])k=k+1;
 if(k==tg_total[t])begin tag_busy[t]<=0;tag_busy_n[t]<=1;end
 end end
 rr_lane<=rr_lane+1'b1;
 nd=0;for(t=0;t<NB;t=t+1)if(wl_done[t])nd=nd+1;
 if(wrote+32'(nd)>issued)mv_fault<=1;
 if(busy&&r_done&&wrote+32'(nd)==issued)begin busy<=0;mv_done<=1;wrote<=0;end
 else wrote<=busy?wrote+32'(nd):0;
 end
 end end
endmodule
`default_nettype wire
