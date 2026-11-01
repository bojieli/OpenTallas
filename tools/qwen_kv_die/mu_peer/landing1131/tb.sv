module tb;
reg clk=0; always #5 clk=~clk;
reg por_n=0,warm_ready=0,begin_valid=0,dispatch_ready=0,terminal_valid=0,terminal_done=0,terminal_fault=0;
reg [58:0] begin_tag=0,terminal_tag=0;
reg [1:0] begin_generation=0,terminal_generation=0;
reg [7:0] request_valid=0;
reg [471:0] request_tag=0;
reg [15:0] request_generation=0;
reg kv_drained=1,vm_drained=1,collective_drained=1,host_drained=1,recovery_valid=0,links_drained=1,link_reset_seen=1,retraining_done=1;
wire [1:0] begin_ready,dispatch_valid,active,dispatched,identity_fault,terminal_accepted;
wire [7:0] request_credit[2],accepted_ranks[2];
wire [58:0] cohort_tag[2]; wire [1:0] cohort_generation[2];
`define PORTS(N) .clk(clk),.por_n(por_n),.warm_ready(warm_ready),.begin_valid(begin_valid),.begin_ready(begin_ready[N]),.begin_tag(begin_tag),.begin_generation(begin_generation),.request_valid(request_valid),.request_tag(request_tag),.request_generation(request_generation),.request_credit(request_credit[N]),.dispatch_valid(dispatch_valid[N]),.dispatch_ready(dispatch_ready),.cohort_tag(cohort_tag[N]),.cohort_generation(cohort_generation[N]),.accepted_ranks(accepted_ranks[N]),.active(active[N]),.dispatched(dispatched[N]),.identity_fault(identity_fault[N]),.terminal_valid(terminal_valid),.terminal_tag(terminal_tag),.terminal_generation(terminal_generation),.terminal_done(terminal_done),.terminal_fault(terminal_fault),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),.host_drained(host_drained),.terminal_accepted(terminal_accepted[N]),.recovery_valid(recovery_valid),.links_drained(links_drained),.link_reset_seen(link_reset_seen),.retraining_done(retraining_done)
ot_qwen_tp8_token_cohort_mu gold(`PORTS(0));
peer_profile gate(`PORTS(1));
wire [82:0] outg={begin_ready[0],request_credit[0],dispatch_valid[0],cohort_tag[0],cohort_generation[0],accepted_ranks[0],active[0],dispatched[0],identity_fault[0],terminal_accepted[0]};
wire [82:0] outp={begin_ready[1],request_credit[1],dispatch_valid[1],cohort_tag[1],cohort_generation[1],accepted_ranks[1],active[1],dispatched[1],identity_fault[1],terminal_accepted[1]};
reg [82:0] previous; integer checked=0,begin_n=0,dispatch_n=0,terminal_n=0;
function [58:0] tag(input integer u); tag=(59'(u)<<43)|(59'(256)<<19); endfunction
integer c,u,p,r;
initial begin
 previous='x;
 for(c=0;c<160;c=c+1) begin
  @(negedge clk);
  por_n=(c>=4 && !(c>=128 && c<132)); warm_ready=(c>=8); dispatch_ready=1;
  begin_valid=0;request_valid=0;terminal_valid=0;recovery_valid=0;
  if(c>=12 && c<108) begin
   u=((c-12)/12)%4; p=(c-12)%12;
   begin_tag=tag(u);terminal_tag=tag(u)|(59'(37)<<37);terminal_done=1;
   for(r=0;r<8;r=r+1) request_tag[59*r+:59]=tag(u);
   if(p==0)begin_valid=1;
   if(p==2)request_valid=8'hff;
   if(p==6)terminal_valid=1;
   if(p==9)recovery_valid=1;
  end
  @(posedge clk);
  if(dispatch_valid[0])dispatch_n=dispatch_n+1;
  #1;
  if(c>=5)begin
   if(outp !== previous)begin $display("MISMATCH cycle%0d goldprev%h candidate%h",c,previous,outp);$fatal(1);end
   checked=checked+1;
  end
  if(begin_valid && begin_ready[0])begin_n=begin_n+1;
  if(terminal_accepted[0])terminal_n=terminal_n+1;
  if(c>=8 && c<128 && identity_fault[0])$fatal(1,"native legal protocol fault at%0d",c);
  previous=outg;
 end
 if(checked<150 || dispatch_n<8 || terminal_n<8)$fatal(1,"insufficient protocol coverage %0d %0d %0d",checked,dispatch_n,terminal_n);
 $display("PASS checked%0d dispatch%0d terminal%0d full4user8rank protocol, +1 edge, reset replay",checked,dispatch_n,terminal_n);$finish;
end
endmodule
