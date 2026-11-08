`timescale 1ns/1ps
module tb_smh_fold2;
 parameter integer MUT=0;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg sv=0,pv=0,cv=0,csv=0;reg[6:0]nv=0;reg[2:0]lt=0;reg[31:0]scale=32'h3e800000,sink=32'h3f000000;
 reg[4:0]csi=0;reg[63:0]csd=0;reg[511:0]d=0;
 wire rev,rov,rdv,fev,fov,fdv;wire[511:0]re,fe;wire[255:0]ro,fo;wire[7:0]rf,ff;
 ot_s81_su_smh #(.DOP(2))R(.clk(clk),.rst_in(rst),.s_v(sv),.p_v(pv),.c_v(cv),.c_nv(nv),.c_lt(lt),.c_scale(scale),.c_sink(sink),
 .cs_v(csv),.cs_i(csi),.cs_d(csd),.d(d),.e_v(rev),.e_d(re),.o_v(rov),.o_d(ro),.den_v(rdv),.f(rf));
 ot_s81_su_smh_fold2 #(.DOP(2),.MUT(MUT))D(.clk(clk),.rst_in(rst),.s_v(sv),.p_v(pv),.c_v(cv),.c_nv(nv),.c_lt(lt),.c_scale(scale),.c_sink(sink),
 .cs_v(csv),.cs_i(csi),.cs_d(csd),.d(d),.e_v(fev),.e_d(fe),.o_v(fov),.o_d(fo),.den_v(fdv),.f(ff));
 reg[511:0]qe[$],qfe[$];reg[255:0]qo[$],qfo[$];reg[31:0]qd[$],qfd[$];
 integer err=0,checks=0,cyc=0;integer last_score=0,pvcycle=0,first_e=0,first_o=0;
 always @(negedge clk)if(rst)begin
 cyc++;
 if(rev)qe.push_back(re);if(fev)begin qfe.push_back(fe);if(first_e==0)begin first_e=cyc;$display("FOLD_LAT first_e%0d last_score%0d delta%0d",cyc,last_score,cyc-last_score);end end
 if(rov)qo.push_back(ro);if(fov)begin qfo.push_back(fo);if(first_o==0)begin first_o=cyc;$display("FOLD_LAT first_o%0d pvcycle%0d delta%0d",cyc,pvcycle,cyc-pvcycle);end end
 if(rdv)qd.push_back(R.rden);if(fdv)begin qfd.push_back(D.rden);$display("FOLD_LAT den%0d",cyc);end
 end
 task tick;begin @(posedge clk);#0.1;end endtask
 function automatic[31:0]val(input integer isscore,input integer k);
 if(isscore &&k%17==0)val=32'hff800000;else val={1'($urandom),8'(isscore?123+$urandom%5:118+$urandom%14),23'($urandom)};
 endfunction
 reg[511:0]a,b;reg[255:0]oa,ob;reg[31:0]da,db;
 integer j,k,l,seed=1108;
 task check;
 begin
 if(qe.size()!=qfe.size()||qo.size()!=qfo.size()||qd.size()!=qfd.size())begin $display("count mismatch e%0d/%0d o%0d/%0d d%0d/%0d",qe.size(),qfe.size(),qo.size(),qfo.size(),qd.size(),qfd.size());err++;end
 while(qe.size()&&qfe.size())begin a=qe.pop_front();b=qfe.pop_front();if(a!==b)begin if(err<12)$display("e mismatch %h %h",a,b);err++;end checks++;end
 while(qo.size()&&qfo.size())begin oa=qo.pop_front();ob=qfo.pop_front();if(oa!==ob)begin if(err<12)$display("o mismatch %h %h",oa,ob);err++;end checks++;end
 while(qd.size()&&qfd.size())begin da=qd.pop_front();db=qfd.pop_front();if(da!==db)begin $display("den mismatch %h %h",da,db);err++;end checks++;end
 end endtask
 initial begin
 seed=$urandom(seed);repeat(4)tick;rst=1;repeat(12)tick;
 for(j=0;j<3;j++)begin
 nv=(j==0)?1:(j==1)?8:40;lt=(j==0)?0:(j==1)?3:6;
 scale=32'h3e800000+(j<<20);sink=32'h3f000000+(j<<18);cv=1;tick;cv=0;repeat(8)tick;
 first_e=0;
 for(k=0;k<nv;k++)begin for(l=0;l<16;l++)d[32*l+:32]=val(1,16*k+l);sv=1;last_score=cyc;tick;sv=0;repeat(3)tick;end
 repeat(500)tick;
 for(k=0;k<32;k++)begin csv=1;csi=5'(k);csd={32'h3f000000+(k<<16),32'h3e000000+(k<<15)};tick;end
 csv=0;repeat(8)tick;first_o=0;pvcycle=cyc;
 for(k=0;k<32;k++)begin for(l=0;l<16;l++)d[32*l+:32]=val(0,l);pv=1;tick;pv=0;tick;end
 repeat(200)tick;check;
 end
 if((|ff)||(|rf))begin $display("fault ref%h fold%h",rf,ff);err++;end
 if(err)$fatal(1,"HEADFOLD2 FAIL checks%0d errors%0d MUT%0d",checks,err,MUT);
 $display("HEADFOLD2 PASS checks%0d MUT%0d",checks,MUT);$finish;
 end
endmodule
