`timescale 1ps/1fs
module tb_hbm_accel_dskv_descriptor_guard #(parameter integer MUT=0);
 reg clk=0,rst_n=0;always #416.5 clk=~clk;
 reg[6:0] die=0;reg[19:0] pos=0;reg row_v=0,row_r2=0,sh_v=0,wq_r=1;
 reg[1:0] row_kind=0;reg[5:0] row_slot=0;reg[2:0] sh_slot=0;
 reg[4351:0] row_data=0,sh_data=0;reg[5:0] ack_n=0;
 wire row_r,sh_r,fault,wq_v,fence_ok;wire[1:0]wq_stk;
 wire[4:0]wq_pc,wq_bank,wq_col;wire[18:0]wq_row;wire[255:0]wq_data;
 wire[15:0]issued,acked;
 ot_hbm_accel_dskv_wb_sram #(.ENABLE(1),.ALL_STACKS(1)) dut(.*);
 integer writes=0,reads=0,posts=0,bad=0,cases=0,positive=0,nonowner=0;reg mask_inject=0;
 reg[4351:0] golden=0;
 always @(posedge clk)if(rst_n)begin
 if(dut.on.shadow_store.on.bank0.w_ce_in||dut.on.shadow_store.on.bank1.w_ce_in)writes++;
 if(dut.on.shadow_store.on.bank0.r_ce_in||dut.on.shadow_store.on.bank1.r_ce_in)reads++;
 if(!mask_inject&&dut.on.shadow_initialized!=0&&writes<17)begin bad++;$display("GUARD_ERROR premature initialization");end
 ack_n<=0;
 if(wq_v&&wq_r)begin
 if(positive)begin
 if(wq_data!==golden[256*posts+:256]||wq_stk!=0||wq_pc!=posts||wq_bank!=0||wq_row!=4014||wq_col!=0)begin
 bad++;$display("GUARD_ERROR positive address or byte mismatch");end
 end
 posts++;ack_n<=1;
 end
 end
 task automatic reset_case;
 @(negedge clk);rst_n=0;row_v=0;sh_v=0;positive=0;mask_inject=0;ack_n=0;
 repeat(3)@(negedge clk);writes=0;reads=0;posts=0;die=0;pos=0;row_slot=0;row_kind=0;sh_slot=0;rst_n=1;
 @(negedge clk);
 endtask
 task automatic invalid(input string name,input integer kind,slot,d,input bit shadow);
 integer beforebad;
 reset_case();beforebad=bad;die=7'(d);row_kind=2'(kind);row_slot=6'(slot);sh_slot=3'(slot);
 if(MUT&&!shadow)force dut.on.descriptor_bad=0;
 row_v=!shadow;sh_v=shadow;
 @(posedge clk);@(negedge clk);row_v=0;sh_v=0;
 if(MUT&&!shadow)release dut.on.descriptor_bad;
 repeat(16)begin
 @(negedge clk);
 if(!fault||row_r||sh_r||wq_v||fence_ok)bad++;
 end
 if(writes!=0||reads!=0||posts!=0||issued!=0||acked!=0)bad++;
 $display("GUARD_CASE name=%s fault=%0d writes=%0d reads=%0d posts=%0d verdict=%s",name,fault,writes,reads,posts,bad==beforebad?"PASS":"FAIL");
 cases++;
 endtask
 initial begin
 invalid("kind3",3,0,0,0);
 invalid("window40",0,40,0,0);invalid("window63",0,63,0,0);
 invalid("ckv8",1,8,0,0);invalid("ckv63",1,63,0,0);
 invalid("key8",2,8,0,0);invalid("key63",2,63,0,0);
 invalid("die96",0,0,96,0);invalid("die127",0,0,127,0);
 for(integer s=0;s<8;s++)invalid($sformatf("uninitialized%0d",s),2,s,0,0);
 invalid("shadow_die96",0,0,96,1);invalid("shadow_die127",0,0,127,1);
 reset_case();mask_inject=1;dut.on.shadow_initialized=8'h01;
 repeat(16)begin @(negedge clk);if(!fault||row_r||sh_r||wq_v||fence_ok)bad++;end
 if(writes||reads||posts)bad++;
 $display("GUARD_CASE name=initialized_mask_flip fault=%0d writes=%0d reads=%0d posts=%0d verdict=%s",fault,writes,reads,posts,(fault&&!writes&&!reads&&!posts)?"PASS":"FAIL");cases++;
 reset_case();die=1;row_kind=2;row_slot=7;row_v=1;
 @(posedge clk);@(negedge clk);row_v=0;
 repeat(16)@(negedge clk);
 if(fault||!fence_ok||writes||reads||posts||issued||acked)begin bad++;$display("GUARD_ERROR nonowner uninitialized key did not drop");end
 else nonowner=1;
 reset_case();
 for(integer b=0;b<544;b++)sh_data[8*b+:8]=8'(b*19+11);
 golden=sh_data;
 sh_slot=7;sh_v=1;@(posedge clk);@(negedge clk);sh_v=0;
 begin:preload_wait
 integer c;c=0;while(!sh_r&&c<128)begin @(negedge clk);c++;end
 if(!sh_r||writes!=17||dut.on.shadow_initialized!=8'h80)begin bad++;$display("GUARD_ERROR preload17 failed");end
 end
 positive=1;row_slot=7;row_kind=2;
 for(integer b=0;b<68;b++)begin row_data[8*b+:8]=8'(b*7+101);golden[8*b+:8]=row_data[8*b+:8];end
 row_v=1;@(posedge clk);@(negedge clk);row_v=0;
 begin:key_wait
 integer c;c=0;while(!fence_ok&&c<128)begin @(negedge clk);c++;end
 if(!fence_ok||fault||posts!=3||writes!=20||reads!=3||issued!=3||acked!=3)begin bad++;$display("GUARD_ERROR initialized key failed");end
 end
 $display("GUARD_METRICS cases=%0d positive_posts=%0d positive_writes=%0d positive_reads=%0d nonowner_drop=%0d bad=%0d",cases,posts,writes,reads,nonowner,bad);
 $display("GUARD_VERDICT %s",bad==0?"PASS":"FAIL");if(bad)$fatal(1,"descriptor guards failed");$finish;
 end
endmodule
