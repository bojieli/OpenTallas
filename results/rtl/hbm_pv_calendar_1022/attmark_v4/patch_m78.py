import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a))
    s=s.replace(a,b)
rep(""" parameter integer OPEN_IL=0    
)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire reserve_v,output wire reserve_ready""",""" parameter integer OPEN_IL=0,
 parameter integer ATT_MARK=0
)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire reserve_v,output wire reserve_ready""")
rep(""" reg i8_r,i8_c,i8_p1,i8_p2,i8_p3,i8_f;reg[9:0]i8_t1,i8_t2;""",""" reg i8_r,i8_c,i8_p1,i8_p2,i8_p3,i8_f;reg[9:0]i8_t1,i8_t2;
 reg at_r,at_c,at_f;""")
rep("""  if(!stream_rst_n)begin programme_v_q<=0;inj_f<=0;i8_r<=0;i8_c<=0;i8_p1<=0;i8_p2<=0;i8_p3<=0;i8_f<=0;i8_t1<=0;i8_t2<=0;end""",
"""  if(!stream_rst_n)begin programme_v_q<=0;inj_f<=0;i8_r<=0;i8_c<=0;i8_p1<=0;i8_p2<=0;i8_p3<=0;i8_f<=0;i8_t1<=0;i8_t2<=0;
   at_r<=0;at_c<=0;at_f<=0;end""")
rep("""   if((i8_c&&(!raw_v||i8_p1))||(!i8_c&&raw_v&&i8_conv))i8_f<=1;
  end""","""   if((i8_c&&(!raw_v||i8_p1))||(!i8_c&&raw_v&&i8_conv))i8_f<=1;
   at_r<=(ATT_MARK!=0)&&(PREL!=0)&&word_v&&word[119];at_c<=at_r;
   if(at_c&&i8_c)at_f<=1;
  end""")
rep(""" ot_smh_static_feed_m78 consumer(
  .clk(stream_clk),.rst_n(stream_rst_n),.command(sm_command),.packet(s1_packet),""",""" wire[82:0]s1_command={sm_command[82:26],sm_command[25]&&!at_c,sm_command[24:0]};
 ot_smh_static_feed_m78 consumer(
  .clk(stream_clk),.rst_n(stream_rst_n),.command(s1_command),.packet(s1_packet),""")
rep(""" assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault||inj_f||i8_f;""",
""" assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault||inj_f||i8_f||at_f;""")
# group: bench enables ATT_MARK (slice.v passes no ATT_MARK; source default 0, die adoption sets 1)
rep(""" parameter integer OPEN_IL=0)(    
 input wire[1:0]id_stack""",""" parameter integer OPEN_IL=0,parameter integer ATT_MARK=1)(
 input wire[1:0]id_stack""")
rep(""".XSLOT(XSLOT),.OPEN_IL(OPEN_IL)) feed(""",""".XSLOT(XSLOT),.OPEN_IL(OPEN_IL),.ATT_MARK(ATT_MARK)) feed(""")
p.write_text(s);print("PATCHED")
