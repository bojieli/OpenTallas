`ifdef OT_VMFE_FLD_PARALLEL_RANKS
// Compute all six fixed priority rotations in parallel; select only the
// resulting grants. This removes pointer-driven request muxes before pick2.
`ifdef OT_VMFE_FLD_NZREG
// claude s81-grpA 10-14: routed SS ll_ptr/lc -> pick2 -> grant -> lc (+/-1) -> lc!=0 was one loop of ~20 levels
// (-269.51 ps at 833.333).  The request bit of each lane is now its own register, lc_nz == (lc != 0) every cycle,
// computed from the registered count and this cycle's (av_r, ll_tk) by a 2-level AND-OR: the 7-bit add/sub and the
// 7-input zero test leave the loop.  No cycle, no state meaning change (lc keeps its value; lc_nz is a copy).
reg [NLL-1:0] lc_nz;
always @(posedge clk) begin : p_lc_nz integer li;
    if (!rn) lc_nz <= {NLL{1'b0}};
    else for (li = 0; li < NLL; li = li + 1)
`ifdef OT_VMFE_FLD_NZREG_MUT
        lc_nz[li] <= (lc[li] > 7'd1) | ((lc[li] == 7'd1) & !ll_tk[li]) | ((lc[li] == 7'd0) & av_r[li]);   // MUTANT: drops av at 1
`else
        lc_nz[li] <= ((lc[li] > 7'd1) & !((lc[li] == 7'd127) & av_r[li] & !ll_tk[li]))
                   | ((lc[li] == 7'd1) & (av_r[li] | !ll_tk[li]))
                   | ((lc[li] == 7'd0) & av_r[li] & !ll_tk[li]);
`endif
end
wire [5:0] priority_req={lc_nz[9],lc_nz[8],lc_nz[7],lc_nz[6],lc_nz[1],lc_nz[0]};
wire [3:0] flow_req={lc_nz[5],lc_nz[4],lc_nz[3],lc_nz[2]};
`else
wire [5:0] priority_req={lc[9]!=0,lc[8]!=0,lc[7]!=0,lc[6]!=0,lc[1]!=0,lc[0]!=0};
wire [3:0] flow_req={lc[5]!=0,lc[4]!=0,lc[3]!=0,lc[2]!=0};
`endif
wire [3:0] flow_first,flow_second;
wire [35:0] ranks_first,ranks_second;
genvar rank;
generate for(rank=0;rank<6;rank=rank+1) begin:g_fixed_rank
    wire [5:0] rr,ff,ss;
    if(rank==0) begin:g_zero
        assign rr=priority_req;
        assign ranks_first[6*rank+:6]=ff;
        assign ranks_second[6*rank+:6]=ss;
    end else begin:g_rot
        assign rr={priority_req[rank-1:0],priority_req[5:rank]};
        assign ranks_first[6*rank+:6]={ff[5-rank:0],ff[5:6-rank]};
        assign ranks_second[6*rank+:6]={ss[5-rank:0],ss[5:6-rank]};
    end
    dsfd_vm_fld_pick2 #(.N(6)) u_rank(.req(rr),.first(ff),.second(ss));
end endgenerate
dsfd_vm_fld_pick2 #(.N(4)) u_flow(.req(flow_req),.first(flow_first),.second(flow_second));
reg [5:0] fixed_first,fixed_second;
`ifdef OT_VMFE_FLD_RANKSEL_REG
// claude s81-grpA 10-14: routed SS ll_ptr[1] -> (binary decode, fanout 13/11/9 x1 cells) -> rank mux -> g[4] -269.51 ps.
// ll_ptr is a free-running counter: its rank decode is registered one edge early (rk_sel), the mux is AND-OR.
reg [5:0] rk_sel;   // registered one-hot rank of the CURRENT ll_ptr (decoded from its next value one edge early)
function automatic [5:0] rk_dec(input [3:0] p);
 case(p) 0,10:rk_dec=6'b000001; 1,11:rk_dec=6'b000010; 7:rk_dec=6'b001000; 8:rk_dec=6'b010000; 9:rk_dec=6'b100000;
  default:rk_dec=6'b000100; endcase
endfunction
always @(posedge clk) begin
 if (!rn) rk_sel <= rk_dec(4'd0);
 else rk_sel <= rk_dec((ll_ptr == NLL - 1) ? 4'd0 : ll_ptr + 4'd1);
end
always @* begin : p_rk integer k;
  fixed_first=6'd0; fixed_second=6'd0;
  for(k=0;k<6;k=k+1) begin
`ifdef OT_VMFE_FLD_RANKSEL_MUT
   if(k!=3) begin   // MUTANT: rank 3 (ll_ptr 7) never selected
`else
   begin
`endif
    fixed_first=fixed_first|(ranks_first[6*k+:6]&{6{rk_sel[k]}});
    fixed_second=fixed_second|(ranks_second[6*k+:6]&{6{rk_sel[k]}});
   end
  end
 end
`else
always @* begin
 case(ll_ptr)
  0,10:begin fixed_first=ranks_first[0+:6];fixed_second=ranks_second[0+:6];end
  1,11:begin fixed_first=ranks_first[6+:6];fixed_second=ranks_second[6+:6];end
  7:begin fixed_first=ranks_first[18+:6];fixed_second=ranks_second[18+:6];end
  8:begin fixed_first=ranks_first[24+:6];fixed_second=ranks_second[24+:6];end
  9:begin fixed_first=ranks_first[30+:6];fixed_second=ranks_second[30+:6];end
  default:begin fixed_first=ranks_first[12+:6];fixed_second=ranks_second[12+:6];end
 endcase
end
`endif
wire[9:0] nonflow_first={fixed_first[5:2],4'b0,fixed_first[1:0]};
wire[9:0] nonflow_second={fixed_second[5:2],4'b0,fixed_second[1:0]};
`else
// Six unthrottled lanes in their exact cyclic order, then four fixed flow-controlled lanes.
wire[5:0] priority_req={lc[9]!=0,lc[8]!=0,lc[7]!=0,lc[6]!=0,lc[1]!=0,lc[0]!=0};
wire[3:0] flow_req={lc[5]!=0,lc[4]!=0,lc[3]!=0,lc[2]!=0};
reg[5:0] rotated_req, fixed_first,fixed_second;
wire[5:0] rotated_first,rotated_second;wire[3:0] flow_first,flow_second;
dsfd_vm_fld_pick2 #(.N(6)) u_priority(.req(rotated_req),.first(rotated_first),.second(rotated_second));
dsfd_vm_fld_pick2 #(.N(4)) u_flow(.req(flow_req),.first(flow_first),.second(flow_second));
always @* begin
 case(ll_ptr)
  0,10:rotated_req=priority_req;
  1,11:rotated_req={priority_req[0],priority_req[5:1]};
  7:rotated_req={priority_req[2:0],priority_req[5:3]};
  8:rotated_req={priority_req[3:0],priority_req[5:4]};
  9:rotated_req={priority_req[4:0],priority_req[5]};
  default:rotated_req={priority_req[1:0],priority_req[5:2]};
 endcase
 case(ll_ptr)
  0,10:begin fixed_first=rotated_first;fixed_second=rotated_second;end
  1,11:begin fixed_first={rotated_first[4:0],rotated_first[5]};fixed_second={rotated_second[4:0],rotated_second[5]};end
  7:begin fixed_first={rotated_first[2:0],rotated_first[5:3]};fixed_second={rotated_second[2:0],rotated_second[5:3]};end
  8:begin fixed_first={rotated_first[1:0],rotated_first[5:2]};fixed_second={rotated_second[1:0],rotated_second[5:2]};end
  9:begin fixed_first={rotated_first[0],rotated_first[5:1]};fixed_second={rotated_second[0],rotated_second[5:1]};end
  default:begin fixed_first={rotated_first[3:0],rotated_first[5:4]};fixed_second={rotated_second[3:0],rotated_second[5:4]};end
 endcase
end
wire[9:0] nonflow_first={fixed_first[5:2],4'b0,fixed_first[1:0]};
wire[9:0] nonflow_second={fixed_second[5:2],4'b0,fixed_second[1:0]};
`endif
wire[9:0] first_selected=(|fixed_first) ? nonflow_first : {4'b0,flow_first,2'b0};
wire[9:0] second_selected=(|fixed_second) ? nonflow_second : ((|fixed_first) ? {4'b0,flow_first,2'b0} : {4'b0,flow_second,2'b0});
always @* begin:p_parallel_grant integer li;
 ll_tk=first_selected|second_selected;
 lsel_v={|second_selected,|first_selected};lsel[0]=0;lsel[1]=0;
 for(li=0;li<NLL;li=li+1) begin
  lsel[0]=lsel[0]|(li[3:0]&{4{first_selected[li]}});
  lsel[1]=lsel[1]|(li[3:0]&{4{second_selected[li]}});
 end
`ifdef OT_VMFE_MUT_FLD_PARALLEL_ARB
 lsel[0]=lsel[0]^4'b0001;
`endif
end
