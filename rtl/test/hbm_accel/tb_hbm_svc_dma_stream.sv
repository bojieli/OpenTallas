`timescale 1ns/1ps
module svc_stream_checker #(parameter ID=0, MUT=0, INITIAL_CREDITS=8, CREDIT_RTT=0, READ_LATENCY=1, REQUEST_GAP=1, RATE_COMMANDS=128, WINDOW=1024)(output reg done=0);
 reg clk=0; always #5 clk=~clk;
 reg rst=1; reg [50:0] dq=0; wire dq_rdy;
 wire [2159:0] dd; wire [2159:0] dd_raw; reg [7:0] dd_cr=0;
 wire [31:0] pc_req_v,pc_rsp_ready; reg [31:0] pc_req_ready=0,pc_rsp_v=0,pc_rsp_fault=0;
 wire [1183:0] pc_req_addr;wire [127:0] pc_req_len;
 wire [543:0] pc_req_tag; reg [543:0] pc_rsp_tag=0;
 reg [8191:0] pc_rsp_data=0;reg [127:0] pc_rsp_beat=0;
 ot_hbm_svc_dma_stream #(.ENABLE(1),.INITIAL_CREDITS(INITIAL_CREDITS),.WINDOW(WINDOW),.NC(32),.LANES(8),.MUT_PC_MAP(MUT==4),.MUT_DROP(MUT==5),.MUT_DATA(MUT==6)) dut(.dd(dd_raw),.*);
 generate for(genvar ml=0;ml<8;ml=ml+1)begin
 wire [269:0] raw=dd_raw[ml*270+:270];
 assign dd[ml*270+:270]=raw ^ ((raw[269]&&MUT==1)?(270'(1)<<0):((raw[269]&&MUT==2)?(270'(1)<<256):((raw[269]&&MUT==3)?(270'(1)<<268):270'(0))));
 end endgenerate
 integer qwiretag[0:31][0:8191],qlast[0:31][0:8191],outstanding[0:31],next_req_cycle[0:31];
 integer qidx[0:31][0:8191],qtag[0:31][0:8191],qbeat[0:31][0:8191],qdue[0:31][0:8191],head[0:31],tail[0:31];
 integer credit_due[0:7][0:8191],credit_head[0:7],credit_tail[0:7];
 integer credit[0:7],next_lane[0:15][0:7],seen_issue[0:15][0:255],seen_output[0:15][0:255];
 integer count[0:15],issued[0:15],received[0:15],generation[0:15];
 integer cyc=0,phase=0,next_command=0,start_cycle=0,last_cycle=0;
 integer i,j,p,idx,t,b,len,total_bytes=0,total_cycles=0,completed=0;
 reg [36:0] absolute,s,base;reg [269:0] beat;
 function automatic [36:0] addr(input integer tag);addr=(37'(ID)<<35)+37'h001234000+37'(tag*8192)+(tag==1&&generation[tag]==1?37'(32):37'(0));endfunction
 function automatic [255:0] payload(input integer sector,input integer tag);
 integer w;begin for(w=0;w<8;w=w+1)payload[w*32+:32]=32'h98bc3200^(ID<<24)^(tag<<12)^(generation[tag]<<16)^(sector<<3)^w;end endfunction
 function automatic bit fault(input integer sector,input integer tag);fault=((sector+3*tag)%19==0);endfunction
 function automatic integer channel(input reg [36:0] a);
 reg [29:0] sec;begin sec=a[34:5];channel=sec[6:2]^sec[11:7]^sec[16:12];end endfunction
 task automatic command(input integer tag,input integer n);
 integer ct,z;
 begin
 ct=tag%16;
 if(count[ct]!=0&&received[ct]!=count[ct])$fatal(1,"tag reused before completion tag=%0d",ct);
 count[ct]=n;issued[ct]=0;received[ct]=0;generation[ct]=tag;
 for(z=0;z<8;z=z+1)next_lane[ct][z]=z;
 for(z=0;z<256;z=z+1)begin seen_issue[ct][z]=0;seen_output[ct][z]=0;end
 dq<={1'b1,4'(ct),9'(n),addr(ct)};
 end endtask
 initial begin
 for(i=0;i<32;i=i+1)begin head[i]=0;tail[i]=0;outstanding[i]=0;next_req_cycle[i]=0;end
 for(i=0;i<8;i=i+1)begin credit[i]=INITIAL_CREDITS;credit_head[i]=0;credit_tail[i]=0;end
 for(t=0;t<16;t=t+1)begin count[t]=0;issued[t]=0;received[t]=0;generation[t]=0;for(i=0;i<8;i=i+1)next_lane[t][i]=i;for(i=0;i<256;i=i+1)begin seen_issue[t][i]=0;seen_output[t][i]=0;end end
 repeat(4)@(negedge clk);rst=0;command(0,256);
 end
 always @(negedge clk)if(!rst&&!done)begin
 pc_req_ready=0;pc_rsp_v=0;pc_rsp_data=0;pc_rsp_fault=0;pc_rsp_beat=0;pc_rsp_tag=0;dd_cr=0;
 for(p=0;p<32;p=p+1)begin
 pc_req_ready[p]=outstanding[p]<16 && cyc+1>=next_req_cycle[p] && ((phase==2)||(cyc%11!=p%11));
 if(head[p]<tail[p]&&qdue[p][head[p]]<=cyc)begin
 idx=qidx[p][head[p]];t=qtag[p][head[p]];
 pc_rsp_v[p]=1;pc_rsp_data[p*256+:256]=payload(idx,t);pc_rsp_fault[p]=fault(idx,t);pc_rsp_beat[p*4+:4]=qbeat[p][head[p]]^(MUT==8?4'(1):4'(0));pc_rsp_tag[p*17+:17]=qwiretag[p][head[p]]^(MUT==7?17'(1):17'(0));
 end end
 for(i=0;i<8;i=i+1)begin
 if(CREDIT_RTT==0)begin if(credit[i]<INITIAL_CREDITS&&(phase==2||((cyc+i)%13>=5)))dd_cr[i]=1;end
 else if(credit_head[i]<credit_tail[i]&&credit_due[i][credit_head[i]]<=cyc+1)dd_cr[i]=1;
 end
 end
 always @(posedge clk)if(!rst&&!done)begin
 cyc=cyc+1;
 if(cyc>40000)$fatal(1,"timeout stack=%0d phase=%0d completed=%0d",ID,phase,completed);
 if(dq[50]&&dq_rdy)begin
 if(phase==2&&next_command<RATE_COMMANDS+1)begin next_command=next_command+1;command(next_command,256);end
 else dq[50]<=0;
 end
 for(i=0;i<8;i=i+1)if(dd_cr[i])begin credit[i]=credit[i]+1;if(CREDIT_RTT!=0)credit_head[i]=credit_head[i]+1;end
 for(p=0;p<32;p=p+1)begin
 if(pc_rsp_v[p]&&pc_rsp_ready[p])begin if(qlast[p][head[p]])outstanding[p]=outstanding[p]-1;head[p]=head[p]+1;end
 if(pc_req_v[p]&&pc_req_ready[p])begin
 outstanding[p]=outstanding[p]+1;next_req_cycle[p]=cyc+REQUEST_GAP;
 if(outstanding[p]>16)$fatal(1,"backend outstanding overflow");
 absolute=pc_req_addr[p*37+:37];t=(absolute-addr(0))/8192;idx=(absolute-addr(t))/32;len=pc_req_len[p*4+:4];
 if(t<0||t>15||idx<0||idx+len>count[t]||absolute[4:0]!=0||channel(absolute)!=p||len<1||len>4)$fatal(1,"bad issue pc=%0d addr=%h tag=%0d idx=%0d len=%0d",p,absolute,t,idx,len);
 for(b=0;b<len;b=b+1)begin
 if(seen_issue[t][idx+b])$fatal(1,"duplicate issue tag=%0d generation=%0d idx=%0d phase=%0d next_command=%0d",t,generation[t],idx+b,phase,next_command);seen_issue[t][idx+b]=1;issued[t]=issued[t]+1;
 qwiretag[p][tail[p]]=pc_req_tag[p*17+:17];qlast[p][tail[p]]=(b==len-1);
 qidx[p][tail[p]]=idx+b;qtag[p][tail[p]]=t;qbeat[p][tail[p]]=b;
 qdue[p][tail[p]]=cyc+READ_LATENCY+(phase==2?0:((idx*17+p*7+t)%23));
 if(phase==0&&idx==0)qdue[p][tail[p]]=cyc+180;
 tail[p]=tail[p]+1;
 end end end
 for(i=0;i<8;i=i+1)begin
 beat=dd[i*270+:270];if(beat[269])begin
 idx=beat[263:256];t=beat[267:264];
 if(credit[i]<=0)$fatal(1,"credit overrun lane=%0d",i);credit[i]=credit[i]-1;
 if(CREDIT_RTT!=0)begin credit_due[i][credit_tail[i]]=cyc+CREDIT_RTT;credit_tail[i]=credit_tail[i]+1;end
 if(idx!=next_lane[t][i]||idx>=count[t]||seen_output[t][idx]||beat[268]!=fault(idx,t)||beat[255:0]!==payload(idx,t))$fatal(1,"scoreboard stack=%0d phase=%0d lane=%0d idx=%0d expected=%0d tag=%0d",ID,phase,i,idx,next_lane[t][i],t);
 if(!seen_issue[t][idx])$fatal(1,"output before issue");
 seen_output[t][idx]=1;next_lane[t][i]=next_lane[t][i]+8;received[t]=received[t]+1;
 if(received[t]==count[t])begin if(issued[t]!=count[t])$fatal(1,"missing issue");completed=completed+1;end
 end end
 if(phase==0&&received[0]==256)begin phase=1;command(1,73);end
 else if(phase==1&&received[1]==73)begin phase=2;start_cycle=cyc;next_command=2;command(2,256);end
 else if(phase==2&&completed==RATE_COMMANDS+2)begin
 total_bytes=RATE_COMMANDS*256*32;total_cycles=cyc-start_cycle;
 $display("BANDWIDTH stack=%0d bytes=%0d cycles=%0d peak_bytes_per_cycle=256",ID,total_bytes,total_cycles);
 done=1;
 end
 end
endmodule
module tb_hbm_svc_dma_stream #(parameter MUT=0, INITIAL_CREDITS=8, CREDIT_RTT=0, READ_LATENCY=1, REQUEST_GAP=1, RATE_COMMANDS=128, WINDOW=1024);
 wire[3:0]done;
 generate for(genvar s=0;s<4;s=s+1)begin svc_stream_checker #(.ID(s),.MUT(MUT),.INITIAL_CREDITS(INITIAL_CREDITS),.CREDIT_RTT(CREDIT_RTT),.READ_LATENCY(READ_LATENCY),.REQUEST_GAP(REQUEST_GAP),.RATE_COMMANDS(RATE_COMMANDS),.WINDOW(WINDOW))u(.done(done[s]));end endgenerate
 initial begin wait(&done);$display("PASS full_shape four_stacks arbitrary_PC_delays delayed_first_sector per_lane_order credit_backpressure");$finish;end
endmodule
