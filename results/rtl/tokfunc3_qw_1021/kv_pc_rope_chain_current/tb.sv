module tb;
reg ck=0; always #5 ck=~ck;
reg rst_n=0; reg [779:0] di=0; reg [260:0] land_er=0;
wire [287:0] land_es; wire issue,ret,cap,trn,fault; wire [17:0] token; wire [15:0] epoch;
wire scale;
qkd_kvpc_s_chain dut(.ck(ck),.rst_n(rst_n),.pc(5'd24),.cfg_stack(2'd0),.di(di),.land_er(land_er),
 .land_es(land_es),.emb_issue_v(issue),.emb_return_slot(ret),.capture_slot(cap),.transfer_slot(trn),.fault(fault),
 .emb_token(token),.emb_epoch(epoch),.emb_scale(scale));
integer ni,nr,nc,nt,nb; integer cycle=0;
task tick; begin @(posedge ck); #1; cycle=cycle+1; if(fault)$fatal(1,"chain fault at %0d",cycle);
 if(issue)begin ni=ni+1;if(!scale||token!=384||epoch!=16'hcafe)$fatal(1,"wrong identity/scale");end
 if(ret)nr=nr+1;if(cap)nc=nc+1;if(trn)nt=nt+1;if(land_es[0])nb=nb+1;
end endtask
task cold; begin @(negedge ck);rst_n=0;di=0;land_er=0; ni=0;nr=0;nc=0;nt=0;nb=0;repeat(5)tick();@(negedge ck);rst_n=1;repeat(5)tick();end endtask
task cfg(input integer k,input integer v);begin @(negedge ck);di=0;di[754]=1;di[755+:5]=24;di[760+:3]=k;di[763+:16]=v;tick();@(negedge ck);di=0;tick();end endtask
task run_token(input integer tok,input integer want);begin
 @(negedge ck);di=0;di[719]=1;di[720+:18]=tok;di[738+:16]=16'hcafe;tick();@(negedge ck);di=0;repeat(25)tick();
 if(ni!=want||nr!=want||nc!=want||nt!=want)$fatal(1,"TOKEN_COUNTS tok=%0d got=%0d/%0d/%0d/%0d expected=%0d",tok,ni,nr,nc,nt,want);
 $display("CHAIN_TOKEN_PASS tok=%0d issue=%0d return=%0d capture=%0d transfer=%0d",tok,ni,nr,nc,nt);
 ni=0;nr=0;nc=0;nt=0;
end endtask
initial begin
 cold();for(integer k=0;k<8;k=k+1)cfg(k,k<4?65535:8+2*(k-4));repeat(5)tick();
 // A cold boot word lands exactly once and returns one credit.
 @(negedge ck);di=0;di[779]=1;di[2+:5]=24;di[12+:256]=256'h12345678;di[524+:29]=29'h13;tick();@(negedge ck);di=0;repeat(3)tick();
 if(nb!=1||land_es[287:1]!={1'b1,1'b1,29'h13,256'h12345678})$fatal(1,"boot landing mismatch");
 @(negedge ck);land_er[259]=1;tick();@(negedge ck);land_er=0;repeat(4)tick();
 run_token(384,1);run_token(151936,0);
 cold();for(integer k=0;k<8;k=k+1)cfg(k,k<4?65535:8+2*(k-4));repeat(5)tick();run_token(151936,0);run_token(384,1);
 $display("CHAIN_COLD_RESET_BOOT_ROPE_PASS");$finish;
end
endmodule
