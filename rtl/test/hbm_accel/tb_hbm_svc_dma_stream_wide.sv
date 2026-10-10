`timescale 1ns/1ps
module svc_stream_wide_checker #(parameter ID=0,MUT=0,READ_LATENCY=104,CREDIT_RTT=192,RATE_COMMANDS=512)(output reg done=0);
 localparam NL=32,TAGS=64,DEPTH=32;
 reg clk=0;always #5 clk=~clk;
 reg rst=1;reg[52:0]dq=0;wire dq_rdy;
 wire[8703:0]dd,dd_raw;reg[31:0]dd_cr=0;
 wire[31:0]pc_req_v,pc_rsp_ready;reg[31:0]pc_req_ready=0,pc_rsp_v=0,pc_rsp_fault=0;
 wire[1183:0]pc_req_addr;wire[127:0]pc_req_len;wire[543:0]pc_req_tag;
 reg[543:0]pc_rsp_tag=0;reg[127:0]pc_rsp_beat=0;reg[8191:0]pc_rsp_data=0;
 ot_hbm_svc_dma_stream_wide #(.ENABLE(1),.NC(32),.LANES(32),.TAGW(6),.WINDOW(16384),.INITIAL_CREDITS(256),.WRITE_COMMIT(3),.READ_PUBLICATION(5),.MUT_PC_MAP(MUT==4),.MUT_DROP(MUT==5),.MUT_DATA(MUT==6))dut(.dd(dd_raw),.*);
 generate for(genvar l=0;l<NL;l=l+1)begin
 wire[271:0]raw=dd_raw[l*272+:272];
 assign dd[l*272+:272]=raw^((raw[271]&&MUT==1)?272'(1):((raw[271]&&MUT==2)?(272'(1)<<256):((raw[271]&&MUT==3)?(272'(1)<<270):272'(0))));
 end endgenerate
 integer valid[0:31][0:31],wiretag[0:31][0:31],desc[0:31][0:31],sector[0:31][0:31],nbeat[0:31][0:31],beatnum[0:31][0:31],due[0:31][0:31];
 integer active[0:31],selected[0:31],selected_beat[0:31],last_req[0:31];
 integer credits[0:31],credit_due[0:31][0:RATE_COMMANDS*8+127],cr_head[0:31],cr_tail[0:31];
 integer count[0:63],issued[0:63],received[0:63],generation[0:63],next_lane[0:63][0:31],seen_i[0:63][0:255],seen_o[0:63][0:255];
 integer pending_command=-1;
 integer cyc=0,phase=0,next_command=0,completed=0,start_cycle=0,raw_count=0,bulk_raw_start=0;
 integer i,j,t,p,pc,entry,chosen,idx,ln,b,free_entry,position,budget,proposals,accepted;
 integer rate_bytes,rate_cycles;reg[36:0]absolute;reg[271:0]beat;
 function automatic[36:0]addr(input integer tag);addr=(37'(ID)<<35)+37'h001234000+37'(tag*8192)+(tag==1&&generation[tag]==1?37'(32):37'(0));endfunction
 function automatic integer channel(input reg[36:0]a);reg[29:0]s;begin s=a[34:5];channel=s[6:2]^s[11:7]^s[16:12];end endfunction
 function automatic[255:0]payload(input integer s,input integer tag);integer w;begin for(w=0;w<8;w=w+1)payload[w*32+:32]=32'h98bc3200^(ID<<24)^(tag<<12)^(generation[tag]<<16)^(s<<3)^w;end endfunction
 function automatic bit fault(input integer s,input integer tag);fault=((s+3*tag)%19==0);endfunction
 function automatic integer raw_budget(input integer cycle);
 // 593 sectors/24 cycles/stack =3162.6667B/cycle aggregate, below3.8TB/s at1.2GHz.
 begin raw_budget=(cycle%4==0)?24:25;if(cycle%24==23)raw_budget=raw_budget-1;end endfunction
 task command(input integer ordinal,input integer n);integer ct,z;begin
 ct=ordinal%TAGS;if(count[ct]!=0&&received[ct]!=count[ct])$fatal(1,"tag reuse before complete");
 count[ct]=n;issued[ct]=0;received[ct]=0;generation[ct]=ordinal;
 for(z=0;z<NL;z=z+1)next_lane[ct][z]=z;
 for(z=0;z<256;z=z+1)begin seen_i[ct][z]=0;seen_o[ct][z]=0;end
 dq<={1'b1,6'(ct),9'(n),addr(ct)};
 end endtask
 initial begin
 for(p=0;p<32;p=p+1)begin active[p]=0;last_req[p]=-1;selected[p]=-1;for(j=0;j<DEPTH;j=j+1)valid[p][j]=0;end
 for(i=0;i<NL;i=i+1)begin credits[i]=256;cr_head[i]=0;cr_tail[i]=0;end
 for(t=0;t<TAGS;t=t+1)begin count[t]=0;issued[t]=0;received[t]=0;generation[t]=0;for(i=0;i<NL;i=i+1)next_lane[t][i]=i;for(i=0;i<256;i=i+1)begin seen_i[t][i]=0;seen_o[t][i]=0;end end
 repeat(4)@(negedge clk);rst=0;command(0,256);
 end
 always @(negedge clk)if(!rst&&!done)begin
 if(!dq[52]&&pending_command>=0&&(count[pending_command%TAGS]==0||received[pending_command%TAGS]==count[pending_command%TAGS]))begin command(pending_command,256);pending_command=-1;end
 pc_req_ready=0;pc_rsp_v=0;pc_rsp_fault=0;pc_rsp_data=0;pc_rsp_tag=0;pc_rsp_beat=0;dd_cr=0;
 for(p=0;p<32;p=p+1)begin
 selected[p]=-1;pc_req_ready[p]=active[p]<DEPTH&&cyc+1>last_req[p]&&((phase==2)||(cyc%11!=p%11));
 // Rotate among eligible leases: tags complete out of issue order, while beats of a lease are exact.
 for(j=0;j<DEPTH;j=j+1)begin entry=(j+cyc*7+p*3)%DEPTH;if(selected[p]<0&&valid[p][entry]&&due[p][entry]<=cyc)selected[p]=entry;end
 if(selected[p]>=0)begin entry=selected[p];idx=sector[p][entry]+beatnum[p][entry];t=desc[p][entry];
 pc_rsp_tag[p*17+:17]=wiretag[p][entry]^(MUT==7?17'(1):17'(0));pc_rsp_beat[p*4+:4]=beatnum[p][entry]^(MUT==8?4'(1):4'(0));
 pc_rsp_data[p*256+:256]=payload(idx,t);pc_rsp_fault[p]=fault(idx,t);
 end end
 // Tags drive ready independently of valid. Publish only selected ready PC responses;
 // the CPU model retains each lease until its beat handshakes.
 #1;budget=raw_budget(cyc+1);proposals=0;
 for(p=0;p<32;p=p+1)begin pc=(p+cyc)%32;if(selected[pc]>=0&&proposals<budget&&(pc_rsp_ready[pc]||MUT==7||MUT==8))begin pc_rsp_v[pc]=1;proposals=proposals+1;end end
 if(MUT==9)begin for(p=0;p<32;p=p+1)if(selected[p]>=0)pc_rsp_v[p]=1;end
 for(i=0;i<NL;i=i+1)if(cr_head[i]<cr_tail[i]&&credit_due[i][cr_head[i]]<=cyc+1)dd_cr[i]=1;
 end
 always @(posedge clk)if(!rst&&!done)begin
 cyc=cyc+1;
 if(cyc>RATE_COMMANDS*256+20000)$fatal(1,"timeout stack=%0d phase=%0d completed=%0d",ID,phase,completed);
 if(dq[52]&&dq_rdy)begin dq[52]<=0;if(phase==2&&next_command<RATE_COMMANDS+1)begin next_command=next_command+1;pending_command=next_command;end end
 for(i=0;i<NL;i=i+1)if(dd_cr[i])begin credits[i]=credits[i]+1;cr_head[i]=cr_head[i]+1;end
 accepted=0;
 for(p=0;p<32;p=p+1)begin
 if(pc_rsp_v[p]&&pc_rsp_ready[p])begin
 accepted=accepted+1;entry=selected[p];if(entry<0)$fatal(1,"response without lease");
 beatnum[p][entry]=beatnum[p][entry]+1;
 if(beatnum[p][entry]==nbeat[p][entry])begin valid[p][entry]=0;active[p]=active[p]-1;end
 end
 if(pc_req_v[p]&&pc_req_ready[p])begin
 if(last_req[p]==cyc)$fatal(1,"request gap violated");last_req[p]=cyc;
 absolute=pc_req_addr[p*37+:37];t=(absolute-addr(0))/8192;idx=(absolute-addr(t))/32;ln=pc_req_len[p*4+:4];
 if(t<0||t>=TAGS||idx<0||idx+ln>count[t]||absolute[4:0]!=0||channel(absolute)!=p||ln<1||ln>4)$fatal(1,"bad request map/burst stack=%0d PC=%0d tag=%0d idx=%0d len=%0d",ID,p,t,idx,ln);
 free_entry=-1;for(j=0;j<DEPTH;j=j+1)if(!valid[p][j]&&free_entry<0)free_entry=j;
 if(free_entry<0)$fatal(1,"finite32PCleases exhausted");entry=free_entry;
 valid[p][entry]=1;wiretag[p][entry]=pc_req_tag[p*17+:17];desc[p][entry]=t;sector[p][entry]=idx;nbeat[p][entry]=ln;beatnum[p][entry]=0;
 due[p][entry]=cyc+READ_LATENCY+(phase==2?0:((idx*17+p*7+t)%23));if(phase==0&&idx==0)due[p][entry]=cyc+READ_LATENCY+180;
 active[p]=active[p]+1;if(active[p]>DEPTH)$fatal(1,"backend capacity overflow");
 for(b=0;b<ln;b=b+1)begin if(seen_i[t][idx+b])$fatal(1,"duplicate issue");seen_i[t][idx+b]=1;issued[t]=issued[t]+1;end
 end end
 if(accepted>raw_budget(cyc))$fatal(1,"RAW_ROOF exceeded calendar cycle=%0d accepted=%0d allowed=%0d",cyc,accepted,raw_budget(cyc));
 raw_count=raw_count+accepted;
 for(i=0;i<NL;i=i+1)begin beat=dd[i*272+:272];if(beat[271])begin
 idx=beat[263:256];t=beat[269:264];
 if(credits[i]<=0)$fatal(1,"credit overrun");credits[i]=credits[i]-1;credit_due[i][cr_tail[i]]=cyc+CREDIT_RTT;cr_tail[i]=cr_tail[i]+1;
 if(idx!=next_lane[t][i]||idx>=count[t]||seen_o[t][idx]||beat[270]!=fault(idx,t)||beat[255:0]!==payload(idx,t)||!seen_i[t][idx])$fatal(1,"wide scoreboard stack=%0d lane=%0d tag=%0d generation=%0d idx=%0d expected=%0d",ID,i,t,generation[t],idx,next_lane[t][i]);
 seen_o[t][idx]=1;next_lane[t][i]=next_lane[t][i]+NL;received[t]=received[t]+1;
 if(received[t]==count[t])begin if(issued[t]!=count[t])$fatal(1,"missing issue");completed=completed+1;end
 end end
 if(phase==0&&received[0]==256)begin phase=1;command(1,73);end
 else if(phase==1&&received[1]==73)begin phase=2;start_cycle=cyc;bulk_raw_start=raw_count;next_command=2;command(2,256);end
 else if(phase==2&&completed==RATE_COMMANDS+2)begin
 rate_bytes=RATE_COMMANDS*256*32;rate_cycles=cyc-start_cycle;
 $display("WIDE_BANDWIDTH stack=%0d bytes=%0d cycles=%0d raw_sectors=%0d nominal_bytes_per_cycle=833.333333 sustained_bytes_per_cycle=791.666667 calendar_bytes_per_cycle=790.666667",ID,rate_bytes,rate_cycles,raw_count-bulk_raw_start);
 done=1;
 end
 end
endmodule
module tb_hbm_svc_dma_stream_wide #(parameter MUT=0,READ_LATENCY=104,CREDIT_RTT=192,RATE_COMMANDS=512);
 wire[3:0]done;
 generate for(genvar s=0;s<4;s=s+1)begin svc_stream_wide_checker #(.ID(s),.MUT(MUT),.READ_LATENCY(READ_LATENCY),.CREDIT_RTT(CREDIT_RTT),.RATE_COMMANDS(RATE_COMMANDS))u(.done(done[s]));end endgenerate
 initial begin wait(&done);$display("PASS wide_four_stacks_32lanes_64slots_CPU_scoreboard_finite32leases_OOO_tags_raw_roof_calendar_bank_commit3_publication5");$finish;end
endmodule
