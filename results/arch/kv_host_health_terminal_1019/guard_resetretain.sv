// Separate candidate. Raw fault sources are sticky asynchronous single bits;
// event/payload buses are coherent in the compensated 833ps guard family.
module qkd_host_service_guard #(parameter SETTLE=4,MUT=0)(
 input wire ck_guard,rst_n,input wire[24:0]raw_faults,
 input wire[2:0]die_id,input wire[7:0]physical_faults,transport_faults,
 input wire accepted_ing_v,input wire[1:0]accepted_ing_cls,
 input wire[15:0]accepted_ing_header,input wire done_v,input wire[63:0]done_d,
 input wire boot_barrier_v,input wire[31:0]boot_barrier_target,
 input wire begin_v,input wire[15:0]begin_epoch,
 input wire pending_advertised,input wire[15:0]pending_epoch,
 input wire[92:0]local_tk,
 output reg[92:0]guarded_tk,output reg abort,service_ready,
 output reg[15:0]service_epoch,output reg[25:0]diag_raw,
 output reg[31:0]status,output reg[3:0]groups,
 output reg[7:0]physical_diag,transport_diag,
 input wire service_protocol_fault
);
 (* ASYNC_REG="TRUE" *)reg[24:0]fm,fs;
 reg protocol_pin_q;reg[2:0]role_q,role;reg role_valid,role_sampled;
 reg[7:0]pf_q,tf_q;reg[92:0]tk_q;
 reg iv,dv,bv,ev,av;reg[1:0]ic;reg[15:0]ih,ep,ap;
 reg[63:0]dd;reg[31:0]bt;
 always @(posedge ck_guard or negedge rst_n)if(!rst_n)begin
 protocol_pin_q<=0;fm<=0;fs<=0;role_sampled<=0;role_q<=0;pf_q<=0;tf_q<=0;tk_q<=0;
 iv<=0;dv<=0;bv<=0;ev<=0;av<=0;ic<=0;ih<=0;ep<=0;ap<=0;dd<=0;bt<=0;
 end else begin
 protocol_pin_q<=service_protocol_fault;fm<=raw_faults;fs<=fm;role_sampled<=1;role_q<=die_id;pf_q<=physical_faults;tf_q<=transport_faults;tk_q<=local_tk;
 iv<=accepted_ing_v;ic<=accepted_ing_cls;ih<=accepted_ing_header;
 dv<=done_v;dd<=done_d;bv<=boot_barrier_v;bt<=boot_barrier_target;
 ev<=begin_v;ep<=begin_epoch;av<=pending_advertised;ap<=pending_epoch;
 end
 reg[24:0]sticky;reg protocol_fault,wait_advert,epoch_dirty;
 reg[31:0]activity_gen,activity_closed,nadmit,nclosed,last_done,last_barrier;
 reg[7:0]quiet;
 wire fp=iv&&ic==1&&ih[7];wire np=iv&&ic==1&&!ih[7];
 wire mp=iv&&ic==0&&ih[7:0]==2;
 wire activity_admit=iv&&!mp;
 // This service candidate requires a genuine ordered BOOT_END for ALL ingest
 // activity. DONE never establishes payload ownership or closes readiness.
 wire unfenced_admit=np||(iv&&ic==0&&!mp)||(iv&&ic==2&&fc==0);
 wire ftv,mtv;wire[7:0]ft;wire[63:0]mt;
 wire[7:0]fc,mc;wire fo,fu,mo,mu;
 // Completion staging absorbs the four-edge bank prefetch startup.
 reg[39:0]dq[0:7];reg[31:0]bq[0:7];reg[2:0]dw,dr,bw,br;
 reg[3:0]dc,bc;
 wire dt=dc!=0&&ftv;wire mb=bc!=0&&mtv;
 wire dp=dv&&dd[63:56]==1&&dd[55:48]==0&&dd[39:32]==0;
 wire dbad=dv&&!dp;
 wire dop=dp&&(dc<8||dt);wire bop=bv&&(bc<8||mb);
 qkd_host_guard_fifo #(.W(8))fenced(ck_guard,rst_n,fp,ih[15:8],dt,ftv,ft,fc,fo,fu);
 qkd_host_guard_fifo #(.W(64))markers(ck_guard,rst_n,mp,{activity_gen,nadmit},mb,mtv,mt,mc,mo,mu);
 wire internal_bad=protocol_pin_q||fo||mo||dbad||(dp&&!dop)||(bv&&!bop)||
 (dc!=0&&fc==0&&!fp)||(bc!=0&&mc==0&&!mp)||
 (dt&&((MUT!=4&&dq[dr][39:32]!=ft)||dq[dr][31:0]<last_done))||
 (mb&&(bq[br]<last_barrier||mt[63:32]>activity_gen||mt[31:0]>nadmit))||
 (role_valid&&role_q!=role)||(activity_admit&&activity_gen==32'hffffffff)||(unfenced_admit&&nadmit==32'hffffffff)||
 (ev&&(ep<=service_epoch||wait_advert||fc!=0||mc!=0||nadmit!=nclosed||activity_gen!=activity_closed));
 wire[24:0]next_sticky=sticky|((MUT==1)?25'b0:fs);
 wire bad=protocol_fault||internal_bad||(|next_sticky);
 wire clean=(MUT==3)||(!epoch_dirty&&(fc==0)&&(mc==0)&&(dc==0)&&(bc==0)&&(nadmit==nclosed)&&((MUT==5)||(activity_gen==activity_closed)));
 wire activity=iv||dv||bv||ev||dt||mb;
 wire[3:0]g={ (|next_sticky[19:14]),(|next_sticky[13:12]),
 ((|next_sticky[11:6])||(|next_sticky[24:20])),(|next_sticky[5:0])};
 always @(posedge ck_guard or negedge rst_n)if(!rst_n)begin
 role<=0;role_valid<=0;sticky<=sticky;protocol_fault<=0;wait_advert<=0;epoch_dirty<=0;
 activity_gen<=0;activity_closed<=0;nadmit<=0;nclosed<=0;last_done<=0;last_barrier<=0;quiet<=0;
 dw<=0;dr<=0;bw<=0;br<=0;dc<=0;bc<=0;
 guarded_tk<=0;abort<=0;service_ready<=0;service_epoch<=0;diag_raw<=0;
 status<=0;groups<=0;physical_diag<=0;transport_diag<=0;
 end else begin
 if(!role_valid&&role_sampled)begin role<=role_q;role_valid<=1;end
 sticky<=next_sticky;protocol_fault<=protocol_fault||internal_bad;
 if(activity_admit)activity_gen<=activity_gen+1'b1;if(unfenced_admit)nadmit<=nadmit+1'b1;
 if(dop)begin dq[dw]<={dd[47:40],dd[31:0]};dw<=dw+1'b1;end
 if(bop)begin bq[bw]<=bt;bw<=bw+1'b1;end
 if(dt)begin dr<=dr+1'b1;last_done<=dq[dr][31:0];end
 if(mb)begin br<=br+1'b1;nclosed<=mt[31:0];last_barrier<=bq[br];
 if(mt[63:32]>activity_closed)activity_closed<=mt[63:32];end
 case({dop,dt})2'b10:dc<=dc+1'b1;2'b01:dc<=dc-1'b1;endcase
 case({bop,mb})2'b10:bc<=bc+1'b1;2'b01:bc<=bc-1'b1;endcase
 if(ev)begin service_epoch<=ep;wait_advert<=1;epoch_dirty<=1;end
 else if(mb)epoch_dirty<=0;
 if(!ev&&iv&&service_ready)wait_advert<=1;
 else if(!ev&&av&&ap==service_epoch)wait_advert<=0;
 if(activity||!clean||bad||wait_advert)quiet<=0;
 else if(quiet<SETTLE)quiet<=quiet+1'b1;
 service_ready<=clean&&!activity&&!bad&&!wait_advert&&((MUT==2)||quiet>=SETTLE);
 abort<=bad;diag_raw<={protocol_fault||internal_bad,next_sticky};groups<=g;
 guarded_tk<={tk_q[92:89],tk_q[88]|bad,tk_q[87:0]};
 physical_diag<=pf_q|((g[0]||protocol_fault||internal_bad)?(8'b1<<role):8'b0);
 transport_diag<=tf_q|(g[1]?(8'b1<<role):8'b0);
 status<={mc,quiet,fc,2'b0,wait_advert,((nadmit!=nclosed)||(activity_gen!=activity_closed)),protocol_fault||internal_bad,bad,service_ready,clean};
 end
 initial if(SETTLE<4||SETTLE>255)$fatal(1,"guard requires >=4 quiet edges");
endmodule
