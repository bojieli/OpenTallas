`timescale 1ns/1fs
module tb_vq_k_transaction;
 reg ck=0;always #0.416500 ck=~ck;
 reg rst_n=0,yv=0,mv=0;reg[2:0]yi=0,ksel=0;reg[127:0]y=0;reg[3:0]sid=0;reg[7:0]index_=0;
 wire[2:0]v,s,f;wire[275:0]d[0:2];
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:instances
  ot_s81sl_vq #(.AQ_XMEM(2))u(.clk(ck),.rst_n(rst_n),.y_v(yv),.y_i(yi),.y(g==2?y^128'd1:y),.u_v(1'b0),.u_i(3'd0),.u(256'd0),.sid(sid),.k(g==0?3'd0:ksel),.m_v(mv),.m_q(1'b1),.m_b(1'b1),.m_i(index_),.um_v(1'b0),.um_q(1'b0),.um_b(1'b0),.um_i(8'd0),.xf_v(v[g]),.xf_s(s[g]),.xf(d[g]),.fault(f[g]));
 end endgenerate
 integer cyc=0,ph,which,k,l,errors=0,checks=0,fragments=0,changed=0,vectors=0,slot=0;
 reg hv[0:16],hs[0:16];reg[275:0]hd[0:16];reg[1103:0]assembled=0;
 function automatic[2:0]profile(input integer i);begin case(i)0:profile=2;1:profile=0;2:profile=1;3:profile=3;default:profile=4;endcase end endfunction
 function automatic[1023:0]expected(input integer i);begin for(integer j=0;j<64;j=j+1)expected[16*j+:16]=16'h3e00+16'(3*i+j);end endfunction
 always @(negedge ck)begin
  ph=cyc%256;which=cyc/256;index_=8'(which);sid=4'(which/5);ksel=profile(which%5);rst_n=(ph>=64);mv=(ph==80);yv=(ph>=100&&ph<108);yi=3'(ph-100);
  for(integer a=0;a<8;a=a+1)y[16*a+:16]=16'h3e00+16'(3*which+8*(ph-100)+a);
 end
 always @(posedge ck)begin cyc=cyc+1;#0.000001;
  for(integer a=16;a>0;a=a-1)begin hv[a]=hv[a-1];hs[a]=hs[a-1];hd[a]=hd[a-1];end
  hv[0]=v[0];hs[0]=s[0];hd[0]=d[0];
  if(rst_n)begin
   checks=checks+1;
   if(|f||v[1]!==hv[4*int'(ksel)]||(v[1]&&{s[1],d[1]}!=={hs[4*int'(ksel)],hd[4*int'(ksel)]}))begin errors=errors+1;if(errors<8)$display("BAD vector%0d phase%0d valid%b fault%b",which,ph,v,f);end
   if(v[1])begin fragments=fragments+1;if(d[2]!==d[1])changed=changed+1;end
   if(v[0])begin
    if(s[0])slot=0;
    assembled[276*slot+:276]=d[0];
    if(slot==3)begin
     if(assembled[20:13]!==8'(which)||assembled[12:9]!==4'(which/5))errors=errors+1;
     if(assembled[3:1]==3'd2)begin if(assembled[21+:1024]!==expected(which))errors=errors+1;vectors=vectors+1;end
    end
    slot=(slot+1)%4;
   end
  end
  if(cyc==80*256-1)begin
   $display("VQ_K_TRANSACTION checks%0d fragments%0d BF16vectors%0d mutant_changed%0d errors%0d clock_ps833",checks,fragments,vectors,changed,errors);
   if(errors==0&&fragments==640&&vectors==80&&changed>=80)$display("VQ_K_TRANSACTION_PASS");else $fatal(1,"VQ_K_TRANSACTION_FAIL");$finish;
  end
 end
endmodule
