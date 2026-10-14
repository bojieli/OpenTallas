`timescale 1ps/1fs
module tb_hgi_sv_native_write_owned;
`ifndef WMUT
 `define WMUT 0
`endif
 reg clk=0;always #500 clk=~clk;
 reg rst_n=0;reg[8960:0]legacy_q=0;wire[31:0]legacy_credit,legacy_done;
 reg[3:0]wgrant=0,wack=0;wire[3:0]wreq,drained,released;
 wire legacy_grant;wire[32*281-1:0]native_wq;reg[31:0]native_credit=0,native_done=0;wire[64:0]fault;
 ot_hgi_sv_native_write_owned #(.HARD_CLOCKS(1),.MUT(`WMUT))dut(.leaf_clk({64{clk}}),.*);
 integer cycle=0,errors=0,received=0,committed=0,legacy_committed=0,expected_total=0;
 integer sent[0:31],available[0:31],credited[0:31],done[0:31],actual_done[0:31];
 integer issued[0:31],cr_head[0:31],done_head[0:31];
 integer born[0:31][0:255],owners[0:31][0:255];
 reg[14:0]sectors[0:31][0:255];reg[255:0]data[0:31][0:255];reg[7:0]masks[0:31][0:255];
 reg[31:0]memory[0:32767][0:7],golden[0:32767][0:7];
 function automatic integer quota(input integer l);quota=17+(l*7)%31;endfunction
 function automatic[255:0]pattern(input integer l,input integer n);
  for(integer w=0;w<8;w++)pattern[w*32+:32]=32'h40000000+32'(n*1024+l*8+w);
 endfunction
 function automatic[14:0]sector(input integer l,input integer n);
  sector={(n<8)?2'b00:2'((n/2+l/8)%4),8'(n),5'(l)};
 endfunction
 function automatic[7:0]mask(input integer l,input integer n);mask=8'(n*13+l*11);endfunction
 task err(input string reason);begin errors++;if(errors<16)$display("ERR cycle%0d %s",cycle,reason);end endtask
 initial begin
  for(integer l=0;l<32;l++)begin
   sent[l]=0;available[l]=8;credited[l]=0;done[l]=0;actual_done[l]=0;issued[l]=0;cr_head[l]=0;done_head[l]=0;expected_total+=quota(l);
  end
  for(integer s=0;s<32768;s++)for(integer w=0;w<8;w++)begin memory[s][w]=32'hdead0000+32'(s*8+w);golden[s][w]=memory[s][w];end
  repeat(5)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(integer t=0;t<6000;t++)begin
   legacy_q=0;legacy_q[8960]=(received<expected_total);
   // Held all-SID ownership arrives after the real request. Never post before grant.
   if((|wreq)&&t>=8)begin wgrant=(t<10)?4'h1:(t<12)?4'h3:4'hf;wack=0;end
   if(legacy_grant||t<8)for(integer l=0;l<32;l++)if(sent[l]<quota(l)&&available[l]>0)begin
    legacy_q[l*280+:280]={1'b1,sector(l,sent[l]),pattern(l,sent[l]),mask(l,sent[l])};
   end
   @(posedge clk);cycle++;
   for(integer l=0;l<32;l++)begin
    if(legacy_q[l*280+279])begin
     reg[14:0]s;reg[255:0]d;reg[7:0]m;
     s=sector(l,sent[l]);d=pattern(l,sent[l]);m=mask(l,sent[l]);
     for(integer w=0;w<8;w++)if(m[w])golden[s][w]=d[w*32+:32];
     sent[l]++;available[l]--;
    end
    if(legacy_credit[l])begin credited[l]++;available[l]++;if(credited[l]>sent[l])err("unsolicited legacy credit");end
    if(legacy_done[l])begin done[l]++;legacy_committed++;if(done[l]>actual_done[l])err("legacy done preceded actual commit or wrong legacy lane");end
    if(available[l]<0||available[l]>8)err("legacy8slot reservation violated");
   end
   for(integer b=0;b<32;b++)if(native_wq[b*281+280])begin
    reg[14:0]s;reg[255:0]d;reg[7:0]m;integer l,n;
    s=native_wq[b*281+264+:15];d=native_wq[b*281+8+:256];m=native_wq[b*281+:8];l=int'(s[4:0]);n=int'(s[12:5]);
    if(native_wq[b*281+279]||int'(s[14:13])*8+int'(s[2:0])!=b)err("native mirror/SID/bank mapping");
    if(!wgrant[b/8])err("native request posted without its actual SID permit");
    if(n>=sent[l]||d!==pattern(l,n)||m!==mask(l,n))err("native write data/word mask association");
    if(issued[b]>=256)err("reference queue exhausted");
    born[b][issued[b]]=cycle;owners[b][issued[b]]=l;sectors[b][issued[b]]=s;data[b][issued[b]]=d;masks[b][issued[b]]=m;issued[b]++;received++;
   end
   #1;
   if(|fault)begin err("bridge fault");break;end
   @(negedge clk);native_credit=0;native_done=0;
   // Dequeue and commit independently delay each bank's FIFO head. Commit is
   // deliberately much later; simultaneous returns from4SIDs are serialized.
   for(integer b=0;b<32;b++)begin
    if(cr_head[b]<issued[b]&&cycle-born[b][cr_head[b]]>=3+(b%7))begin native_credit[b]=1;cr_head[b]++;end
    if(done_head[b]<cr_head[b]&&cycle-born[b][done_head[b]]>=23+(b%13))begin
     integer j,l,s;j=done_head[b];l=owners[b][j];s=int'(sectors[b][j]);
     for(integer w=0;w<8;w++)if(masks[b][j][w])memory[s][w]=data[b][j][w*32+:32];
     native_done[b]=1;done_head[b]++;actual_done[l]++;committed++;
    end
   end
   if(received==expected_total&&committed==expected_total&&legacy_committed==expected_total&&(&drained))begin
    native_credit=0;native_done=0;wgrant=0;repeat(4)@(negedge clk);wack=4'hf;repeat(3)@(negedge clk);
    if(released!=4'hf)err("all-SID drained ACK release");break;
   end
  end
  if(received!=expected_total||committed!=expected_total||legacy_committed!=expected_total)err("incomplete finite drain");
  for(integer l=0;l<32;l++)begin
   if(sent[l]!=quota(l)||credited[l]!=sent[l]||done[l]!=sent[l])err("lane credit/commit totals");
   for(integer n=0;n<quota(l);n++)for(integer w=0;w<8;w++)if(memory[sector(l,n)][w]!==golden[sector(l,n)][w])err("masked native memory mismatch");
  end
  if(errors==0)$display("SV_NATIVE_WRITE PASS writes=%0d commits=%0d cycles=%0d",received,committed,cycle);
  else $display("SV_NATIVE_WRITE FAIL errors=%0d writes=%0d commits=%0d/%0d",errors,received,committed,expected_total);
  $finish;
 end
endmodule
