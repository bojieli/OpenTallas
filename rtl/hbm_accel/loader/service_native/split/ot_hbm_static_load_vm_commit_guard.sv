`default_nettype none
// SOURCE-ONLY fixed-deadline native DQ completion audit. No wait/ready/credit.
// VMfault is each bank's status[17]|status[16], not merely a done pulse:
// invalid decoded writes can acknowledge with a zero write-mask.
// OWNERSHIP: vm_done_i must belong exclusively to this DMA's reserved slot6
// writes. Drain every prior DQ producer before start; grant sole DQ ownership
// through deadline/status settle. An untagged ACK from another producer cannot
// be distinguished here and could satisfy a pending count. Regional production
// routing must either preserve this calendar exclusion or return producer tags.
module ot_hbm_static_load_vm_commit_guard(
 input wire clk,rst_n,start_v_i,input wire[20:0]expected_words_i,input wire start_buffer_i,
 input wire[280:0]packet_i,input wire[31:0]vm_done_i,vm_fault_i,input wire deadline_v_i,
 input wire release_v_i,release_buffer_i,begin_v_i,begin_buffer_i,
 output reg active_o,done_o,fault_o,output wire release_safe_o,begin_safe_o
);
 reg buffer_q;reg[20:0]expected_q;reg[21:0]emitted_words;
 reg[21:0]pending[0:31];integer k;reg all_empty;
 wire[4:0]destination={packet_i[278:277],packet_i[266:264]};
 function automatic[3:0]pop8(input[7:0]mask);
 integer b;reg[3:0]s;begin s=0;for(b=0;b<8;b=b+1)s=s+{3'd0,mask[b]};pop8=s;end endfunction
 always @*begin all_empty=1;for(integer j=0;j<32;j=j+1)if(pending[j]!=0)all_empty=0;end
 assign release_safe_o=!(active_o&&release_buffer_i==buffer_q)&&!(start_v_i&&release_buffer_i==start_buffer_i)&&!(packet_i[280]&&release_buffer_i==buffer_q)&&!fault_o;
 assign begin_safe_o=!(active_o&&begin_buffer_i==buffer_q)&&!(start_v_i&&begin_buffer_i==start_buffer_i)&&!fault_o;
 always @(posedge clk)begin
 if(!rst_n)begin active_o<=0;done_o<=0;fault_o<=0;buffer_q<=0;expected_q<=0;emitted_words<=0;
 for(k=0;k<32;k=k+1)pending[k]<=0;
 end else begin
 done_o<=0;
 if(|vm_fault_i)fault_o<=1;
 if(release_v_i&&!release_safe_o)fault_o<=1;
 if(begin_v_i&&!begin_safe_o)fault_o<=1;
 if(start_v_i)begin
 if(active_o||packet_i[280]||(|vm_done_i)||expected_words_i==0)fault_o<=1;
 else begin active_o<=1;buffer_q<=start_buffer_i;expected_q<=expected_words_i;emitted_words<=0;
 for(k=0;k<32;k=k+1)pending[k]<=0;end
 end
 if(active_o)begin
 if(packet_i[280])begin
 if(packet_i[279]||packet_i[7:0]==0||emitted_words+{18'd0,pop8(packet_i[7:0])}>{1'b0,expected_q})fault_o<=1;
 emitted_words<=emitted_words+{18'd0,pop8(packet_i[7:0])};
 end
 for(k=0;k<32;k=k+1)begin
 if(vm_done_i[k]&&pending[k]==0)fault_o<=1;
 case({packet_i[280]&&destination==5'(k),vm_done_i[k]})
 2'b10:pending[k]<=pending[k]+22'd1;
 2'b01:pending[k]<=pending[k]-22'd1;
 default:begin end
 endcase
 end
 end else if(packet_i[280])fault_o<=1;
 if(deadline_v_i)begin
 if(!active_o||!all_empty||emitted_words!={1'b0,expected_q}||packet_i[280]||(|vm_done_i)||(|vm_fault_i)||fault_o)fault_o<=1;
 else done_o<=1;
 active_o<=0;
 end
 end end
endmodule
`default_nettype wire
