`timescale 1ns/1ps
`default_nettype none
// Source-real XIO partition: request +1core; collective total +3core; Q/G +4core/+3serial.
// All delays fixed, II unchanged, no credit/backpressure. Physical qualification pending.
module dsfd_vm_xio_request #(parameter integer RLAT=13)(
 input wire ck,rst_n,input wire n_v,input wire[83:0] n_d,input wire[14:0] f_crq,
 output reg[3:0] a_v,output reg[55:0] a_row,
 output wire[2:0] return_valid,output wire[5:0] return_lane,output reg fault
);
    reg [1:0] rq;
    always @(posedge ck or negedge rst_n) if (!rst_n) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // epoch sample index of the current edge (same convention as ot_s81_vm_x43: first edge after release = 0)
    reg [1:0] tp;
    always @(posedge ck or negedge rst_n) if (!rst_n) tp <= 2'd3; else tp <= tp + 2'd1;
    wire [1:0] tn = tp + 2'd1;
    reg [2:0] f_iss;

    // ---------------------------------------------------------------- command decode
    wire [2:0] code = n_d[30:28];
    wire is_st = n_v && code == 3'd4, is_cp = n_v && code == 3'd5, is_cf = n_v && code == 3'd7;
    wire is_cl = n_v && code == 3'd6 && n_d[27:24] == 4'd7;
    // Unit 0 names the direct collective lane; state is used only for Q/G (1/2).
    reg [2:0] act; reg [13:0] u_row [0:2]; reg [4:0] u_n [0:2];
    reg [3:0] stream_av; reg [55:0] stream_ar;
    // ---------------------------------------------------------------- issue (edge I)
    reg [2:0] go; reg [1:0] gl [0:2];
    always @* begin : p_go integer u;
        for (u = 0; u < 3; u = u + 1) begin
            go[u] = (u == 0) ? f_crq[0] : (act[u] && tn != 2'(15-RLAT));
            gl[u] = (u == 0) ? f_crq[2:1] : u_row[u][1:0];
        end
    end
    reg lane_bad;
    reg [2:0] go_ok;
    always @* begin
        lane_bad = 1'b0; go_ok = go;
        if (go[2] && go_ok[1] && gl[2] == gl[1]) begin lane_bad = 1'b1; go_ok[2] = 1'b0; end
    end
    // The direct collective lane is merged with the registered Q/G requests.
    // A collision faults and collective retains its reserved lane; nothing waits.
`ifdef OT_VM_XIO_MUT_REQUEST
    always @* begin
      a_v=stream_av;a_row=stream_ar;
      if(f_crq[0])begin a_v[f_crq[2:1]]=1'b1;a_row[14*f_crq[2:1]+:14]=f_crq[14:1];end
    end
`else
    always @(posedge ck) if (!rn) begin a_v <= 0; a_row <= 0; end else begin
        a_v <= stream_av; a_row <= stream_ar;
        if (f_crq[0]) begin
            a_v[f_crq[2:1]] <= 1'b1;
            a_row[14*f_crq[2:1] +: 14] <= f_crq[14:1];
        end
    end
`endif
    reg [RLAT:0] dC; reg [1:0] dlC [0:RLAT];
    reg [RLAT+1:0] dQ, dG; reg [1:0] dlQ [0:RLAT+1]; reg [1:0] dlG [0:RLAT+1];
    always @(posedge ck) begin : p_iss integer u, k; reg [3:0] av;
        if (!rn) begin
            act <= 3'd0; stream_av <= 4'd0; dC <= '0; dQ <= '0; dG <= '0;
            f_iss <= 3'd0;
        end else begin
            av = 4'd0;
            for (u = 1; u < 3; u = u + 1) if (go_ok[u]) av[gl[u]] = 1'b1;
            stream_av <= av;
            for (u = 1; u < 3; u = u + 1) if (go[u]) begin
                u_row[u] <= u_row[u] + 14'd1;
                if (u_n[u] == 5'd0) act[u] <= 1'b0; else u_n[u] <= u_n[u] - 5'd1;
            end
            if (lane_bad) f_iss[1] <= 1'b1;
            dC <= {dC[RLAT-1:0], f_crq[0]};
            dQ <= {dQ[RLAT:0], go_ok[1]}; dG <= {dG[RLAT:0], go_ok[2]};
            if (f_crq[0] && stream_av[f_crq[2:1]]) f_iss[1] <= 1'b1;
            if (is_cp || is_cf || is_cl) f_iss[2] <= 1'b1;
            if (is_st) begin
                if (n_d[27]) f_iss[2] <= 1'b1;
                else begin
                    if (act[1 + n_d[26]] && !(go[1 + n_d[26]] && u_n[1 + n_d[26]] == 5'd0)) f_iss[0] <= 1'b1;
                    act[1 + n_d[26]] <= 1'b1; u_row[1 + n_d[26]] <= n_d[25:12]; u_n[1 + n_d[26]] <= n_d[11:7];
                end
            end

        end
        for (k = 0; k < 4; k = k + 1)
            stream_ar[14*k +: 14] <= (go_ok[1] && gl[1] == k[1:0]) ? u_row[1] : u_row[2];
        dlC[0] <= f_crq[2:1]; dlQ[0] <= gl[1]; dlG[0] <= gl[2];
        for (k = 1; k <= RLAT+1; k = k + 1) begin
            dlQ[k] <= dlQ[k-1]; dlG[k] <= dlG[k-1];
        end
        for (k = 1; k <= RLAT; k = k + 1) dlC[k] <= dlC[k-1];
    end

 assign return_valid={dG[RLAT+1],dQ[RLAT+1],dC[RLAT]};
 assign return_lane={dlG[RLAT+1],dlQ[RLAT+1],dlC[RLAT]};
 always @(posedge ck) if(!rn)fault<=0;else fault<=|f_iss;
endmodule
module dsfd_vm_xio_return(
 input wire ck,rst_n,input wire[2:0] return_valid,input wire[5:0] return_lane,
 input wire[3:0] e_v,input wire[2047:0] e_d,input wire[10:0] f_xgo,
 output reg[512:0] t_crs,output wire q_v,output wire[511:0] q_d,
 output wire g_v,output wire[510:0] g_d,output reg fault
);
 reg[1:0] rq;
 always @(posedge ck or negedge rst_n)if(!rst_n)rq<=0;else rq<={rq[0],1'b1};
 wire rn=rq[1];
 reg[3:0] ev_pin;reg[2047:0] ed_pin;reg[2:0] valid_pin;reg[5:0] lane_pin;
 always @(posedge ck)begin ev_pin<=rn?e_v:0;ed_pin<=e_d;valid_pin<=rn?return_valid:0;lane_pin<=return_lane;end
 function automatic[511:0] lane512(input[2047:0] d,input[1:0] l);
  begin lane512=({512{l==0}}&d[0+:512])|({512{l==1}}&d[512+:512])|({512{l==2}}&d[1024+:512])|({512{l==3}}&d[1536+:512]);end
 endfunction
 wire rC=valid_pin[0],rQ=valid_pin[1],rG=valid_pin[2];
 wire[1:0]lC=lane_pin[1:0],lQ=lane_pin[3:2],lG=lane_pin[5:4];
 wire[3:0]expected=(rC?(4'b1<<lC):4'b0)|(rQ?(4'b1<<lQ):4'b0)|(rG?(4'b1<<lG):4'b0);
 wire[511:0]dCw=lane512(ed_pin,lC),dQw=lane512(ed_pin,lQ),dGw=lane512(ed_pin,lG);
 reg[2:0]qv,gv;reg[511:0]qd[0:2];reg[510:0]gd[0:2];
 assign q_v=qv[2];assign q_d=qd[2];assign g_v=gv[2];assign g_d=gd[2];
 reg[10:0]xq;always @(posedge ck)xq<=rn?f_xgo:0;
 reg[2:0]gn;reg[9:0]gph[0:3];reg[1:0]gw,gr;integer k;
 always @(posedge ck)begin: p_return
  reg push,pop;
  if(!rn)begin qv<=0;gv<=0;t_crs<=0;fault<=0;gn<=0;gw<=0;gr<=0;end
  else begin
   qv<={qv[1:0],rQ};gv<={gv[1:0],rG};
`ifdef OT_VM_XIO_MUT_RETURN
   t_crs<={dQw,rC};
`else
   t_crs<={dCw,rC};
`endif
   if(ev_pin!=expected)fault<=1;
   // Mirror the phase queue at the final real Q/G output edge, not before tail stages.
   push=gv[1]&&gd[1][1:0]==0;pop=xq[10];
   if(push)begin gph[gw]<=gd[1][58:49];gw<=gw+1'b1;end
   if(pop)begin
    if(gn==0&&!push)fault<=1;
    else if(gph[gr]!=xq[9:0])fault<=1;
    gr<=gr+1'b1;
   end
   gn<=gn+(push?3'd1:3'd0)-((pop&&(gn!=0||push))?3'd1:3'd0);
   if(push&&!pop&&gn==4)fault<=1;
  end
  qd[0]<=dQw;
`ifdef OT_VM_XIO_MUT_GATHER
  gd[0]<=dGw[510:0]^511'd4;
`else
  gd[0]<=dGw[510:0];
`endif
  for(k=1;k<3;k=k+1)begin qd[k]<=qd[k-1];gd[k]<=gd[k-1];end
 end
endmodule

module dsfd_vm_xio_serial(
 input wire ck,rst_n,input wire qo_v,qf,gf,input wire[2:0]qSWs,output reg fault
);
 reg[1:0]rq;reg[2:0]qs_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)rq<=0;else rq<={rq[0],1'b1};
 always @(posedge ck)begin
  qs_q<=qSWs;
  if(!rq[1])fault<=0;else if((qo_v&&!(qs_q[0]&&qs_q[1]))||qf||gf)fault<=1;
 end
endmodule

module dsfd_vm_xio_fault_join(
 input wire ck,rst_n,request_fault,return_fault,serial_valid,serial_level,transport_fault,output reg fault
);
 // Fixed exceptional initialization guard: old no-reset transport data must not
 // re-latch a prior epoch's diagnostic during common-epoch warm reset. Sticky
 // producers retain any new fault until this six-core-edge flush completes.
 reg[5:0] warm;
 always @(posedge ck or negedge rst_n)if(!rst_n)warm<=0;else warm<={warm[4:0],1'b1};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)fault<=0;
`ifndef OT_VM_XIO_MUT_WARM
  else if(!warm[5])fault<=0;
`endif
`ifdef OT_VM_XIO_MUT_FAULT
  else fault<=fault|request_fault|return_fault;
`else
  else fault<=fault|request_fault|return_fault|(serial_valid&&serial_level)|transport_fault;
`endif
 end
endmodule

module dsfd_vm_static_xio #(parameter integer RLAT = 13) (
    input wire ck_control_t, ck_control_s,
    input wire ck_return_t, rss_return_t, ck_fault_t, ck_fault_s, rss_fault_t, rst_fault_s,
    input wire ck_fault_join_t,rss_fault_join_t,
    input wire [1:0] ck_x43_t, ck_x43_s, // [0]query, [1]gather
    input wire rss_control_t, rst_control_s,
    input wire [1:0] rss_x43_t, rst_x43_s, // per-root active-low epoch resets
    // engine 12 native forward
    input  wire          n_v, input wire [83:0] n_d,
    // aux ports 4..7 to / from dsfd_vm_static_core
    output wire [3:0]    a_v, output wire [55:0] a_row,
    input  wire [3:0]    e_v, input wire [2047:0] e_d,
    // collective
    input  wire [2203:0] f_collective,
    input  wire [14:0]   f_crq,
    output wire [512:0]  t_crs,
    output reg  [3:0]    w_v, output reg [55:0] w_row, output reg [2047:0] w_d, output reg [63:0] w_m, output reg [31:0] w_t,
    // gather
    output wire [511:0]  t_gather,             // serial
    input  wire [10:0]   f_xgo,                // stream
    // scan query
    output wire [512:0]  qSW,                  // serial
    input  wire [2:0]    qSWs,                 // serial
    output wire          fault
);

 // Wires-only parent. Each hardened leaf receives its own measured phi-minus-R root.
 wire[2:0]return_valid;wire[5:0]return_lane;wire req_fault,ret_fault,serial_fault;
 wire q_v,g_v;wire[511:0]q_d;wire[510:0]g_d;
 dsfd_vm_xio_request #(.RLAT(RLAT))u_req(.ck(ck_control_t),.rst_n(rss_control_t),.n_v(n_v),.n_d(n_d),.f_crq(f_crq),.a_v(a_v),.a_row(a_row),.return_valid(return_valid),.return_lane(return_lane),.fault(req_fault));
 dsfd_vm_xio_return u_ret(.ck(ck_return_t),.rst_n(rss_return_t),.return_valid(return_valid),.return_lane(return_lane),.e_v(e_v),.e_d(e_d),.f_xgo(f_xgo),.t_crs(t_crs),.q_v(q_v),.q_d(q_d),.g_v(g_v),.g_d(g_d),.fault(ret_fault));
    // Compiler rows and masks are passed to the core without a landing pointer
    // or extra pin stage. Each lane's 8-bit tag remains part of f_collective ABI;
    // the wrapper/core associates these writes with fixed sources 44..47.
    always @* begin : p_land integer k;
        w_v = 4'd0; w_row = 56'd0; w_d = 2048'd0; w_m = 64'd0; w_t = 32'd0;
        for (k = 0; k < 4; k = k + 1) begin
            w_v[k] = f_collective[551*k];
            w_row[14*k +: 14] = f_collective[551*k+1 +: 14];
            w_m[16*k +: 16] = f_collective[551*k+15 +: 16];
            w_d[512*k +: 512] = f_collective[551*k+31 +: 512];
            `ifdef OT_VM_XIO_MUT_TAG
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8] ^ 8'd1;
`else
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8];
`endif
        end
    end
    // ---------------------------------------------------------------- serial-bound streams
    wire qo_v, go_v; wire [511:0] qo_d; wire [510:0] go_d; wire qf, gf;
    ot_s81_vm_x43 #(.W(512)) u_xq (.t_ck(ck_x43_t[0]), .t_rst_n(rss_x43_t[0]), .s_v(q_v), .s_d(q_d), .s_ck(ck_x43_s[0]), .s_rst_n(rst_x43_s[0]),
        .o_v(qo_v), .o_d(qo_d), .fault(qf));
    ot_s81_vm_x43 #(.W(511)) u_xg (.t_ck(ck_x43_t[1]), .t_rst_n(rss_x43_t[1]), .s_v(g_v), .s_d(g_d), .s_ck(ck_x43_s[1]), .s_rst_n(rst_x43_s[1]),
        .o_v(go_v), .o_d(go_d), .fault(gf));
    assign qSW = {qo_d, qo_v};
    assign t_gather = {go_d, go_v};

 dsfd_vm_xio_serial u_serial(.ck(ck_control_s),.rst_n(rst_control_s),.qo_v(qo_v),.qf(qf),.gf(gf),.qSWs(qSWs),.fault(serial_fault));
 wire[1:0]fb0,fb1,fb2;wire[2:0]fpar;wire fmark,fvalid,flevel,fxfault;
 ot_s81_vm_fault_x34_s_w1 u_fault_s(.s_ck(ck_fault_s),.s_rst_n(rst_fault_s),.s_v(1'b1),.s_d(serial_fault),.b0(fb0),.b1(fb1),.b2(fb2),.bpar(fpar),.s_mark(fmark));
 ot_s81_vm_fault_x34_t_w1 u_fault_t(.t_ck(ck_fault_t),.t_rst_n(rss_fault_t),.b0(fb0),.b1(fb1),.b2(fb2),.bpar(fpar),.s_mark(fmark),.o_v(fvalid),.o_d(flevel),.fault(fxfault));
 dsfd_vm_xio_fault_join u_fault(.ck(ck_fault_join_t),.rst_n(rss_fault_join_t),.request_fault(req_fault),.return_fault(ret_fault),.serial_valid(fvalid),.serial_level(flevel),.transport_fault(fxfault),.fault(fault));
endmodule
`default_nettype wire
