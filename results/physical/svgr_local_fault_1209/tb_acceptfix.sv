`timescale 1ns/1ps
module tb; parameter MUT=0,LOCAL=1; reg clk=0; always #5 clk=~clk; integer cyc=0,t=0,bad=0,statebad=0,mirrorbad=0,afterfault=0,reserves=0,words=0,faultrises=0; reg oldfault=0,accepted_before=0;
reg[1:0] id_stack=0;
reg[2:0] id_sm=0;
reg[0:0] stream_rst_n=0;
reg[0:0] hbm_rst_n=0;
reg[0:0] seam_h_fault=0;
reg[7:0] seam_complete=0;
reg[15:0] seam_complete_bank=0;
reg[7:0] seam_bfault=0;
reg[2047:0] seam_read_data=0;
reg[14:0] reserve_row_base=0;
reg[0:0] reserve_v=0;
reg[31:0] reserve_base=0;
reg[11:0] reserve_total=0;
reg[1:0] reserve_bank=0;
reg[15:0] reserve_epoch=0;
reg[0:0] start_v=0;
reg[1:0] start_bank=0;
reg[15:0] start_epoch=0;
wire[0:0] a_seam_res_v,b_seam_res_v;
wire[96:0] a_seam_res_word,b_seam_res_word;
wire[0:0] a_seam_s_fault,b_seam_s_fault;
wire[0:0] a_seam_stop,b_seam_stop;
wire[7:0] a_seam_read_v,b_seam_read_v;
wire[1:0] a_seam_read_bank,b_seam_read_bank;
wire[47:0] a_seam_read_row,b_seam_read_row;
wire[0:0] a_reserve_ready,b_reserve_ready;
wire[3:0] a_block_ready,b_block_ready;
wire[0:0] a_out_v,b_out_v;
wire[3:0] a_out_mask,b_out_mask;
wire[1023:0] a_out_data,b_out_data;
wire[10:0] a_out_ordinal,b_out_ordinal;
wire[1:0] a_out_bank,b_out_bank;
wire[15:0] a_out_epoch,b_out_epoch;
wire[0:0] a_out_last,b_out_last;
wire[0:0] a_fault,b_fault;
producer_gold #(.LBANKS(4),.OPEN_IL(1),.OREG(1)) gold(.stream_clk(clk),.id_stack(id_stack),.id_sm(id_sm),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.seam_h_fault(seam_h_fault),.seam_complete(seam_complete),.seam_complete_bank(seam_complete_bank),.seam_bfault(seam_bfault),.seam_read_data(seam_read_data),.reserve_row_base(reserve_row_base),.reserve_v(reserve_v),.reserve_base(reserve_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),.seam_res_v(a_seam_res_v),.seam_res_word(a_seam_res_word),.seam_s_fault(a_seam_s_fault),.seam_stop(a_seam_stop),.seam_read_v(a_seam_read_v),.seam_read_bank(a_seam_read_bank),.seam_read_row(a_seam_read_row),.reserve_ready(a_reserve_ready),.block_ready(a_block_ready),.out_v(a_out_v),.out_mask(a_out_mask),.out_data(a_out_data),.out_ordinal(a_out_ordinal),.out_bank(a_out_bank),.out_epoch(a_out_epoch),.out_last(a_out_last),.fault(a_fault));
producer_local #(.LBANKS(4),.OPEN_IL(1),.OREG(1),.LOCAL_FAULT(LOCAL),.FMUT(MUT)) dut(.stream_clk(clk),.id_stack(id_stack),.id_sm(id_sm),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.seam_h_fault(seam_h_fault),.seam_complete(seam_complete),.seam_complete_bank(seam_complete_bank),.seam_bfault(seam_bfault),.seam_read_data(seam_read_data),.reserve_row_base(reserve_row_base),.reserve_v(reserve_v),.reserve_base(reserve_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),.seam_res_v(b_seam_res_v),.seam_res_word(b_seam_res_word),.seam_s_fault(b_seam_s_fault),.seam_stop(b_seam_stop),.seam_read_v(b_seam_read_v),.seam_read_bank(b_seam_read_bank),.seam_read_row(b_seam_read_row),.reserve_ready(b_reserve_ready),.block_ready(b_block_ready),.out_v(b_out_v),.out_mask(b_out_mask),.out_data(b_out_data),.out_ordinal(b_out_ordinal),.out_bank(b_out_bank),.out_epoch(b_out_epoch),.out_last(b_out_last),.fault(b_fault));
initial begin integer k;for(cyc=0;cyc<20480;cyc=cyc+1)begin @(negedge clk);t=cyc%256;
id_stack=0;
id_sm=0;
stream_rst_n=0;
hbm_rst_n=0;
seam_h_fault=0;
seam_complete=0;
seam_complete_bank=0;
seam_bfault=0;
seam_read_data=0;
reserve_row_base=0;
reserve_v=0;
reserve_base=0;
reserve_total=0;
reserve_bank=0;
reserve_epoch=0;
start_v=0;
start_bank=0;
start_epoch=0;
stream_rst_n=(t>=8&&!(t>=200&&t<204));hbm_rst_n=(t>=8&&!(t>=128&&t<132));reserve_epoch=16'(cyc/256+1);start_epoch=reserve_epoch;reserve_total=8;
for(k=0;k<64;k=k+1)seam_read_data[k*32+:32]=$urandom;
if(t==16)begin reserve_v=1;reserve_bank=0;end
if(t==20)begin seam_complete=8'hff;seam_complete_bank=0;end
if(t==24)begin start_v=1;start_bank=0;end
if(t==40)begin start_v=1;start_bank=1;start_epoch=7;end
if(t==41)begin reserve_v=1;reserve_bank=1;reserve_total=4;end
if(t==44)begin seam_complete=8'hff;seam_complete_bank=16'h5555;end
if(t==48)begin start_v=1;start_bank=1;end
if(t==140)seam_h_fault=1;
if(t==141)begin seam_bfault=8'h24;reserve_v=1;reserve_bank=2;end
if(t>=150&&t<190)begin reserve_v=($urandom%3)==0;reserve_bank=$urandom;reserve_total=$urandom;reserve_base=$urandom;reserve_row_base=$urandom;start_v=($urandom%5)==0;start_bank=$urandom;start_epoch=$urandom;seam_complete=$urandom;seam_complete_bank=$urandom;seam_bfault=$urandom;seam_h_fault=$urandom;end
@(posedge clk);accepted_before=a_seam_res_v;#1; if(t>=12)begin
if(a_seam_res_v!==b_seam_res_v)begin bad++;if(bad<8)$display("DIFF seam_res_v cyc%0d a%h b%h",cyc,a_seam_res_v,b_seam_res_v);end
if(a_seam_res_word!==b_seam_res_word)begin bad++;if(bad<8)$display("DIFF seam_res_word cyc%0d a%h b%h",cyc,a_seam_res_word,b_seam_res_word);end
if(a_seam_s_fault!==b_seam_s_fault)begin bad++;if(bad<8)$display("DIFF seam_s_fault cyc%0d a%h b%h",cyc,a_seam_s_fault,b_seam_s_fault);end
if(a_seam_stop!==b_seam_stop)begin bad++;if(bad<8)$display("DIFF seam_stop cyc%0d a%h b%h",cyc,a_seam_stop,b_seam_stop);end
if(a_seam_read_v!==b_seam_read_v)begin bad++;if(bad<8)$display("DIFF seam_read_v cyc%0d a%h b%h",cyc,a_seam_read_v,b_seam_read_v);end
if(a_seam_read_bank!==b_seam_read_bank)begin bad++;if(bad<8)$display("DIFF seam_read_bank cyc%0d a%h b%h",cyc,a_seam_read_bank,b_seam_read_bank);end
if(a_seam_read_row!==b_seam_read_row)begin bad++;if(bad<8)$display("DIFF seam_read_row cyc%0d a%h b%h",cyc,a_seam_read_row,b_seam_read_row);end
if(a_reserve_ready!==b_reserve_ready)begin bad++;if(bad<8)$display("DIFF reserve_ready cyc%0d a%h b%h",cyc,a_reserve_ready,b_reserve_ready);end
if(a_block_ready!==b_block_ready)begin bad++;if(bad<8)$display("DIFF block_ready cyc%0d a%h b%h",cyc,a_block_ready,b_block_ready);end
if(a_out_v!==b_out_v)begin bad++;if(bad<8)$display("DIFF out_v cyc%0d a%h b%h",cyc,a_out_v,b_out_v);end
if(a_out_mask!==b_out_mask)begin bad++;if(bad<8)$display("DIFF out_mask cyc%0d a%h b%h",cyc,a_out_mask,b_out_mask);end
if(a_out_data!==b_out_data)begin bad++;if(bad<8)$display("DIFF out_data cyc%0d a%h b%h",cyc,a_out_data,b_out_data);end
if(a_out_ordinal!==b_out_ordinal)begin bad++;if(bad<8)$display("DIFF out_ordinal cyc%0d a%h b%h",cyc,a_out_ordinal,b_out_ordinal);end
if(a_out_bank!==b_out_bank)begin bad++;if(bad<8)$display("DIFF out_bank cyc%0d a%h b%h",cyc,a_out_bank,b_out_bank);end
if(a_out_epoch!==b_out_epoch)begin bad++;if(bad<8)$display("DIFF out_epoch cyc%0d a%h b%h",cyc,a_out_epoch,b_out_epoch);end
if(a_out_last!==b_out_last)begin bad++;if(bad<8)$display("DIFF out_last cyc%0d a%h b%h",cyc,a_out_last,b_out_last);end
if(a_fault!==b_fault)begin bad++;if(bad<8)$display("DIFF fault cyc%0d a%h b%h",cyc,a_fault,b_fault);end
for(k=0;k<4;k=k+1)begin
if(gold.allocated[k]!==dut.allocated[k]||gold.bank_epoch[k]!==dut.bank_epoch[k]||gold.bank_total[k]!==dut.bank_total[k]||gold.completed_q[k]!==dut.completed_q[k])statebad++;
if(LOCAL!=0&&dut.sf_bank[k]!==gold.stream_fault)mirrorbad++;
end
if(a_fault)afterfault++;if(a_fault&&!oldfault)faultrises++;oldfault=a_fault;reserves+=accepted_before;words+=a_out_v;end end
$display("SVGR_MIRROR MUT%0d LOCAL%0d bad%0d statebad%0d mirrorbad%0d afterfault%0d reserves%0d words%0d faultrises%0d",MUT,LOCAL,bad,statebad,mirrorbad,afterfault,reserves,words,faultrises);
if(MUT==0&&(bad||statebad||mirrorbad))$fatal(1,"exactness failed");if(MUT!=0&&bad+statebad+mirrorbad==0)$fatal(1,"mutant escaped");if(afterfault<10000||reserves<60||words<60||faultrises<50)$fatal(1,"coverage empty");$finish;end endmodule
