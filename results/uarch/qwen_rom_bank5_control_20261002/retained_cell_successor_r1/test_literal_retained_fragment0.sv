module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
 always @(posedge CLK or negedge RESETN or negedge SETN)
 if (!RESETN) QN<=1'b1; else if (!SETN) QN<=1'b0; else QN<=!D;
 endmodule
 module tb;
 localparam ROM_CONTROL_DISTRIBUTION=1,b=0,p=0,chunk=0;
 reg clk=0,bank_reset_n=0,mask_reset_n=0,wrom_re=0;
 reg [84:0] distributed_strobe_n=0;reg [79:0] distributed_hold_term=0;
 reg [4:0] code_rd_bank=0,code_sel_q=0;
 wire read_q,local_sel;
 generate begin:g_read
 
                wire read_q_n;
                // Actual RVT Liberty: QN next_state=!D, RESETN presets QN=1.
                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_read_ff
                    (.CLK(clk), .D(wrom_re), .RESETN(bank_reset_n), .SETN(1'b1), .QN(read_q_n));
                assign read_q = ~read_q_n;
             end begin:g_mask
 
                                wire local_sel_n;
                                reg local_next;
                                always @* begin
                                    local_next = local_sel;
                                    if (ROM_CONTROL_DISTRIBUTION != 0) begin
                                        if (!distributed_strobe_n[17*b+1+8*p+chunk])
                                            local_next = distributed_hold_term[16*b+8*p+chunk];
                                    end else if (code_rd_bank[b]) local_next = code_sel_q[b];
                                end
                                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_mask_ff
                                    (.CLK(clk), .D(local_next), .RESETN(mask_reset_n), .SETN(1'b1), .QN(local_sel_n));
                                assign local_sel = ~local_sel_n;
                             end endgenerate
 reg ref_read,ref_mask;
 always @(posedge clk or negedge bank_reset_n)
 if(!bank_reset_n) ref_read<=0;else ref_read<=wrom_re;
 always @(posedge clk or negedge mask_reset_n)
 if(!mask_reset_n) ref_mask<=0;
 else if(!distributed_strobe_n[1]) ref_mask<=distributed_hold_term[0];
 integer i,j,k;
 task tick;begin #1;clk=1;#1;
 if(read_q!==ref_read || local_sel!==ref_mask) $fatal(1,"literal mismatch");
 clk=0;#1;end endtask
 initial begin
 tick;bank_reset_n=1;mask_reset_n=1;
 for(i=0;i<3;i=i+1) for(j=0;j<3;j=j+1) for(k=0;k<3;k=k+1) begin
 case(i) 0:distributed_strobe_n[1]=0;1:distributed_strobe_n[1]=1;2:distributed_strobe_n[1]=1'bx;3:distributed_strobe_n[1]=1'bz;endcase
 case(j) 0:distributed_hold_term[0]=0;1:distributed_hold_term[0]=1;2:distributed_hold_term[0]=1'bx;3:distributed_hold_term[0]=1'bz;endcase
 case(k) 0:wrom_re=0;1:wrom_re=1;2:wrom_re=1'bx;3:wrom_re=1'bz;endcase
 tick;
 end
 mask_reset_n=0;bank_reset_n=0;#1;tick;
 $display("PASS_LITERAL_RETAINED_CELL_FOURSTATE_64_COMBINATIONS");$finish;
 end endmodule