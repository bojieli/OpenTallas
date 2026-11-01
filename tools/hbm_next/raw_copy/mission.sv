 // Both actual targets are configured before ONE global launch. The first
 // command establishes COPY ownership before ROLE's fixed fill event. Dates
 // are fixed programme reservations, never shifted by block_ready.
 for(phase=0;phase<4;phase=phase+1)begin
 epoch=16'(7+phase);ebank=phase==2;
 for(integer rb=0;rb<8;rb=rb+1)raw_seen[rb]=0;
 cfg_target=58;desc_limit=118;
 for(integer ci=0;ci<118;ci=ci+1)begin
 cal_entry=0;cal_entry[255:240]=16'hc7a1;cal_entry[239:224]=16'(ci);
 if(ci==100&&phase!=1)begin cal_entry[0]=1;cal_entry[1]=ebank;cal_entry[17:2]=epoch;cal_entry[84:70]=15'd20752;end
 if(ci==116)begin cal_entry[52]=1;cal_entry[53]=ebank;cal_entry[69:54]=epoch;cal_entry[84:70]=15'd20752;end
 write_word(12'(ci),cal_entry);
 end
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!cal_configured)$fatal(1,"RAW_COPY_ROLE_NOT_ARMED");
 final_drain=6000;
 if(phase<3)begin
 cfg_target=106;desc_limit=15;at_date=32;
 for(di=0;di<14;di=di+1)begin
 issue_date=di==0?(mut_early!=0?800:4096):at_date+8;
 drain_date=issue_date+integer'(steps[di])+20;
 command=0;command[31:0]=32'(issue_date);command[63:32]=32'(drain_date);command[290:64]=descs[di];command[291]=ebank;command[307:292]=epoch;
 entry={command,32'(at_date)};
 write_word(12'h800+12'(di*2),entry[255:0]);write_word(12'h801+12'(di*2),{172'd0,entry[339:256]});at_date=drain_date+8;
 end
 issue_date=at_date+8;drain_date=issue_date+112;
 command=0;command[31:0]=32'(issue_date);command[63:32]=32'(drain_date);
 command[290:64]=227'd1|(227'd5<<2)|(227'd8192<<5)|(227'd1<<77)|(227'd5<<95)|((227'd2<<35|227'h2000000)<<98)|(227'd1<<170)|(227'd1<<186)|(227'd64<<206);
 command[291]=ebank;command[307:292]=epoch;entry={command,32'(at_date)};
 write_word(12'h81c,entry[255:0]);write_word(12'h81d,{172'd0,entry[339:256]});final_drain=drain_date;
 repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!configured)$fatal(1,"RAW_COPY_CP_NOT_ARMED");
 end
 if(!cal_configured)$fatal(1,"RAW_COPY_ROLE_LOST_ARM");
 fill_start=cyc;launch_v=1;tick();launch_v=0;
 // Fixed host-side reservation. It is a check, never a ready-driven launch.
 while(cyc-fill_start<3000)tick();
 if(phase!=1)begin
 for(integer rb=0;rb<8;rb=rb+1)if(!raw_ready[rb*2+integer'(ebank)])$fatal(1,"RAW_STATIC_START_MISSED leaf=%0d ready=%h",rb,raw_ready);
 cfg_target=58;desc_limit=1;
 cal_entry=0;cal_entry[255:240]=16'hc7a1;cal_entry[18]=1;cal_entry[19]=ebank;cal_entry[35:20]=epoch;cal_entry[51:36]=16'd0;
 write_word(12'd0,cal_entry);repeat(16)tick();desc_v=1;tick();desc_v=0;repeat(16)tick();
 if(!cal_configured)$fatal(1,"RAW_START_PAGE_NOT_ARMED");
 launch_v=1;tick();launch_v=0;
 end
 while(cyc-fill_start<final_drain+2048)tick();
 if(phase<3)begin
 if(store_completions!=phase+1||physical_WR!=(phase+1)*8)$fatal(1,"RAW_COPY_STORE_CONSERVATION cmds=%0d done=%0d WR=%0d",store_cmds,store_completions,physical_WR);
 if(got!=sent||got!=(phase+1)*896||busy_o||cp_active)$fatal(1,"RAW_COPY_DRAIN got=%0d sent=%0d busy=%b active=%b",got,sent,busy_o,cp_active);
 if(load_dones!=(phase+1)*14||vm_acks!=got)$fatal(1,"RAW_COPY_VM_DONE done=%0d ack=%0d packets=%0d",load_dones,vm_acks,got);
 for(read_j=phase*896;read_j<(phase+1)*896;read_j=read_j+1)begin
 for(k=0;k<32;k=k+1)rq0_bank[k]=0;
 read_bank=integer'({expected[read_j][278:277],expected[read_j][266:264]});
 rq0_bank[read_bank]={1'b1,expected[read_j][279:264]};read_cycle[read_sent]=cyc+1;read_sent=read_sent+1;tick();
 end
 for(k=0;k<32;k=k+1)rq0_bank[k]=0;repeat(16)tick();
 if(read_got!=read_sent)$fatal(1,"RAW_COPY_READBACK_DRAIN");
 end
 for(integer rb=0;rb<8;rb=rb+1)if(raw_seen[rb]!=(phase==1?0:128))$fatal(1,"RAW_EPOCH_CONSERVATION phase=%0d leaf=%0d sectors=%0d",phase,rb,raw_seen[rb]);
 $display("RAW_COPY_EPOCH phase=%0d elapsed=%0d raw_total=%0d copy_packets=%0d native_done=%0d load_done=%0d physical_RD=%0d physical_WR=%0d",phase,cyc-fill_start,raw_total,got,vm_acks,load_dones,dram_reads,physical_WR);
 repeat(24)tick();
 end
