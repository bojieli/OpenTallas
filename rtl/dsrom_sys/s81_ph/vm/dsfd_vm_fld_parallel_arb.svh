`ifdef OT_VMFE_FLD_PARALLEL_RANKS
// Compute all six fixed priority rotations in parallel; select only the
// resulting grants. This removes pointer-driven request muxes before pick2.
wire [5:0] priority_req={lc[9]!=0,lc[8]!=0,lc[7]!=0,lc[6]!=0,lc[1]!=0,lc[0]!=0};
wire [3:0] flow_req={lc[5]!=0,lc[4]!=0,lc[3]!=0,lc[2]!=0};
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
