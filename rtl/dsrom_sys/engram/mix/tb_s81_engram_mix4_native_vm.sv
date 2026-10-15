`timescale 1ns/1ps
// External fixture -> real SU preload -> MIX4 -> real VM128SRAM -> SU readback.
// All reference arrays below are testbench stimuli/scoreboards; none drive a DUT response.
module tb_s81_engram_mix4_native_vm #(parameter MUT=0, WRITE_COMMIT_LAT=11);
 localparam READ_PIPE=4, RL=16, MAXC=40000;
 // VM latency convention (S-ELEM-C 10-15, 7beb fault at cy961 = 'lost descriptor reply': dtag[VM_LAT+1] arrived one
 // edge before the registered return). RL counts from the edge that SAMPLES the request pin to the edge after which the
 // return is valid; the MIX4 VM_LAT counts from the edge that LAUNCHES the request pin, so VM_LAT = RL + 1.
 localparam integer MIX_VM_LAT=RL+1;
 // Calendar: the component bench measures 810 cycles / writes 639..798 at VM_LAT 1; each of the three VM round trips
 // (descriptor, REDUCE, ADD) adds VM_LAT-1 edges, completion waits WRITE_COMMIT_LAT-1 more. Checked exactly.
 localparam integer XTRA=3*(MIX_VM_LAT-1), EXPECTED_CYCLES=810+XTRA+(WRITE_COMMIT_LAT-1), FIRST_W=639+XTRA+1, LAST_W=798+XTRA+1;
 // (+1 on the write span only: this bench stamps a write with the blocking-incremented sampling edge cy, the component
 // bench with its pre-increment cyc; start/done are both read on a negedge, so the cycle count needs no offset.)
 reg ck=0; always #0.4167 ck=~ck;
 reg rss=0; reg [84:0] c_cmd=0; wire [8:0] c_done; wire [1:0] c_st; wire t_inp_su,t_inp_hc;
 reg [84:0] mix_cmd=0; wire [8:0] mix_done; wire [1:0] mix_st;
    reg  [15:0] su_rqv = 0; reg [223:0] su_rq = 0; wire [15:0] su_rsv; wire [8191:0] su_rs;
    reg  [15:0] su_wqv = 0; reg [223:0] su_wq = 0; reg [255:0] su_wqm = 0; reg [8191:0] su_wqd = 0;
    reg  [1:0] hc_rqv = 0; reg [27:0] hc_rq = 0; wire [1:0] hc_rsv; wire [1023:0] hc_rs;
    reg  [7:0] hc_wqv = 0; reg [111:0] hc_wq = 0; reg [127:0] hc_wqm = 0; reg [4095:0] hc_wqd = 0;
    reg  [19:0] pqx = 0; wire [2048:0] pq_o; reg [14:0] crq = 0; wire [512:0] crs;
    reg  [3:0] l_v = 0; reg [2047:0] l_d = 0; reg [2203:0] cvm = 0;
    wire [19:0] mx_rqv; wire [279:0] mx_rq; wire [19:0] mx_rsv; wire [10239:0] mx_rs;
    wire [3:0] mx_wqv; wire [55:0] mx_wq; wire [63:0] mx_wqm; wire [2047:0] mx_wqd;
    // Compatibility stimulus adapter for the core's explicit auxiliary and row-write ports.
    wire [7:0] xv; wire [4095:0] xd;
    reg [1:0] crlane [0:12+READ_PIPE]; integer ci;
    always @(posedge ck) begin
        crlane[0] <= crq[2:1];
        for (ci = 1; ci < 13+READ_PIPE; ci = ci + 1) crlane[ci] <= crlane[ci-1];
    end
    assign crs = {xd[512*crlane[12+READ_PIPE] +: 512], xv[crlane[12+READ_PIPE]]};
    wire [31:0] clt; wire [3:0] clv; wire [55:0] clr; wire [63:0] clm; wire [2047:0] cld;
    genvar cl;
    generate for (cl = 0; cl < 4; cl = cl + 1) begin
        assign clv[cl] = cvm[551*cl];
        assign clt[8*cl +: 8] = cvm[551*cl+543 +: 8];
        assign clr[14*cl +: 14] = cvm[551*cl+1 +: 14];
        assign clm[16*cl +: 16] = cvm[551*cl+15 +: 16];
        assign cld[512*cl +: 512] = cvm[551*cl+31 +: 512];
    end endgenerate
    wire vm_fault;
    dsfd_vm_static_core #(.READ_PIPE(READ_PIPE)) dut (.cks(ck), .rss(rss),
        .ck_read_data({64{ck}}), .ck_read_valid({8{ck}}), .rst_read_data_n({64{rss}}), .rst_read_valid_n({8{rss}}),
        .ck_rsched(ck), .ck_seq(ck), .ck_landing(ck),
        .ck_mem_fsr({16{ck}}), .ck_mem_return({16{ck}}), .ck_mem_bank({128{ck}}),
        .ck_mem_wcapture({128{ck}}), .ck_mem_wscatter({16{ck}}),
        .ck_mem_relay_req({48{ck}}), .ck_mem_relay_rsp({48{ck}}),
        .ck_write_control(ck), .ck_write_header(ck), .ck_write_payload({4{ck}}),
        .ck_write_dispatch({16{ck}}), .ck_write_stage({128{ck}}),
        .rst_rsched_n(rss), .rst_seq_n(rss), .rst_landing_n(rss),
        .rst_mem_fsr_n({16{rss}}), .rst_mem_return_n({4{rss}}), .rst_mem_bank_n({128{rss}}),
        .rst_mem_wcapture_n({128{rss}}), .rst_mem_wscatter_n({16{rss}}), .rst_mem_relay_n({48{rss}}),
        .rst_write_control_n(rss), .rst_write_header_n(rss), .rst_write_payload_n({4{rss}}),
        .rst_write_dispatch_n({16{rss}}), .rst_write_stage_n({128{rss}}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .t_inp_su(t_inp_su),
        .t_inp_hc(t_inp_hc), .f_su_rqv(su_rqv), .f_su_rq(su_rq), .t_su_rsv(su_rsv), .t_su_rs(su_rs), .f_su_wqv(su_wqv),
        .f_su_wq(su_wq), .f_su_wqm(su_wqm), .f_su_wqd(su_wqd), .f_hc_rqv(hc_rqv), .f_hc_rq(hc_rq), .t_hc_rsv(hc_rsv),
        .t_hc_rs(hc_rs), .f_hc_wqv(hc_wqv), .f_hc_wq(hc_wq), .f_hc_wqm(hc_wqm), .f_hc_wqd(hc_wqd), .f_pqx(pqx), .t_pqx(pq_o), .x_av({4'd0, (crq[0] ? (4'b1 << crq[2:1]) : 4'd0)}), .x_ar({56'd0, {4{crq[14:1]}}}), .x_rv(xv), .x_rd(xd), .nf_v(), .nf_d(),
        .f_mx_rqv(mx_rqv), .f_mx_rq(mx_rq), .t_mx_rsv(mx_rsv), .t_mx_rs(mx_rs),
        .f_mx_wqv(mx_wqv), .f_mx_wq(mx_wq), .f_mx_wqm(mx_wqm), .f_mx_wqd(mx_wqd),
        .l_v(l_v), .l_d(l_d), .cp_v(16'd0), .cp_row(224'd0), .cp_m(256'd0), .cp_d(8192'd0), .cl_t(clt), .cl_v(clv), .cl_row(clr), .cl_m(clm), .cl_d(cld), .wf_v(1'b0), .wf_row(14'd0), .wf_d(512'd0), .x_al(3'd0), .x_hdr(9'd0), .edge_f(3'd0), .vm_fault(vm_fault));


 dsfd_engram_mix4_c #(.MUT(MUT),.HLAYOUT(1),.VM_LAT(MIX_VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.RS(5)) mix(
  {149{ck}},rss,mix_cmd,mix_done,mix_st,1'b1,mx_rqv,mx_rq,mx_rsv,mx_rs,mx_wqv,mx_wq,mx_wqm,mx_wqd);
 reg [63:0] cfg[0:0]; reg [1023:0] hm[0:639],km[0:639],wm[0:639],vm[0:159],ym[0:639];
 reg [511:0] image[0:16383], expected_y[0:639]; reg used[0:16383];
 reg [19:0] ev[0:MAXC-1]; reg [10239:0] ed[0:MAXC-1];
 reg sev[0:MAXC-1]; reg [511:0] sed[0:MAXC-1];
 integer wc[0:16383]; reg [3:0] slices[0:16383],raw_slices[0:16383]; reg [7:0] wt[0:16383];
 wire [127:0] raw_v; wire [1151:0] raw_a; wire [511:0] raw_m; wire [1023:0] raw_t;
 integer raw_row,raw_slice;
 reg boot_done[0:16383];reg [31:0] boot_banks;integer boot_n;
 integer cy=0,reads=0,writes=0,commits=0,preloads=0,readbacks=0,answers=0,rawcommits=0;
 integer i,j,q,b,r,n,p,s,a,start,elapsed,first_w=-1,last_w=-1; string dir;
 function integer bank(input integer row); bank=(row&31)^(((row>>5)&7)<<2); endfunction
 function integer stripe(input integer base,input integer beat,input integer lane);
  integer target,addr;
  begin target=(( ((bank(256+4*beat)>>2)+1+(lane>>2))&7)<<2)|(lane&3);
   addr=(base>>5)+((base==13824)?(beat>>3):beat);stripe=(addr<<5)|(target^((addr&7)<<2));end
 endfunction
 task put(input integer row,input [511:0] data);begin
  if(used[row])$fatal(1,"fixture alias row=%0d",row);used[row]=1;image[row]=data;
 end endtask
 // cy names the positive sampling edge. Negative-edge checks see its settled outputs.
 always @(posedge ck)begin
  cy=cy+1;
  if(cy>=MAXC)$fatal(1,"timeout");
  if(rss)begin
   // Sample the actual SRAM w_ce address/mask/tag before this edge's NBA updates.
   // Baseline PIPE0 source pin P -> macro write-enable P+9 -> relayed cm_v P+11.
   for(integer k=0;k<128;k=k+1)if(raw_v[k])begin
    raw_slice=k/32;raw_row=(integer'(raw_a[9*k+:9])<<5)|((k%32)^((raw_a[9*k+:9]&7)<<2));
    if(wc[raw_row]<0 || cy-(wc[raw_row]-WRITE_COMMIT_LAT)!=9 || raw_slices[raw_row][raw_slice] ||
       raw_m[4*k+:4]!==4'hf || raw_t[8*k+:8]!==wt[raw_row])
     $fatal(1,"raw SRAM write timing/mask/tag mismatch row=%0d cy=%0d source=%0d",raw_row,cy,wc[raw_row]-WRITE_COMMIT_LAT);
    raw_slices[raw_row][raw_slice]=1;rawcommits=rawcommits+1;
   end
   if(mx_wqv!=0 && mx_wqv!==4'b1111)$fatal(1,"four writes required per active edge");
   for(integer l=0;l<20;l=l+1)if(mx_rqv[l])begin
    ev[cy+RL][l]=1;ed[cy+RL][512*l+:512]=image[mx_rq[14*l+:14]];reads=reads+1;
   end
   if(su_rqv[0])begin sev[cy+RL]=1;sed[cy+RL]=image[su_rq[0+:14]];end
   for(integer l=0;l<16;l=l+1)if(su_wqv[l])begin
    wt[su_wq[14*l+:14]]=l;wc[su_wq[14*l+:14]]=cy+WRITE_COMMIT_LAT;slices[su_wq[14*l+:14]]=0;raw_slices[su_wq[14*l+:14]]=0;
   end
   for(integer l=0;l<4;l=l+1)if(mx_wqv[l])begin
    r=mx_wq[14*l+:14];
    if(r<256||r>=896||mx_wqm[16*l+:16]!==16'hffff)$fatal(1,"invalid output row/mask");
    if(mx_wqd[512*l+:512]!==expected_y[r-256])$fatal(1,"numerical mismatch row=%0d",r);
    wt[r]=28+l;image[r]=mx_wqd[512*l+:512];wc[r]=cy+WRITE_COMMIT_LAT;slices[r]=0;raw_slices[r]=0;
    writes=writes+1;answers=answers+32;if(first_w<0)first_w=cy;last_w=cy;
   end
  end
 end
 always @(negedge ck)if(rss)begin
  if(vm_fault||mix_st[0])$fatal(1,"DUT fault cy=%0d vm=%b mix=%b",cy,vm_fault,mix_st);
  if(mx_rsv!==ev[cy])$fatal(1,"RL16 valid mismatch cy=%0d got=%h expected=%h",cy,mx_rsv,ev[cy]);
  for(integer l=0;l<20;l=l+1)if(ev[cy][l]&&mx_rs[512*l+:512]!==ed[cy][512*l+:512])$fatal(1,"MIX return data mismatch cy=%0d lane=%0d",cy,l);
  if(su_rsv!=={15'd0,sev[cy]})$fatal(1,"SU RL16 valid mismatch cy=%0d",cy);
  if(sev[cy])begin if(su_rs[0+:512]!==sed[cy])$fatal(1,"SRAM readback mismatch");readbacks=readbacks+1;end
  for(integer k=0;k<128;k=k+1)if(dut.cm_v[k])begin
   s=k/32;a=dut.cm_a[9*k+:9];r=(a<<5)|((k%32)^((a&7)<<2));
   if(wc[r]!=cy||slices[r][s]||dut.cm_m[4*k+:4]!==4'hf||dut.cm_t[8*k+:8]!==wt[r])$fatal(1,"commit timing/mask mismatch row=%0d cy=%0d expected=%0d",r,cy,wc[r]);
   slices[r][s]=1;commits=commits+1;
  end
 end
 // Observe actual macro write-enable sampling, separately from relayed cm_v.
 genvar gs,gb;generate for(gs=0;gs<4;gs=gs+1)begin:obs_slice
  for(gb=0;gb<32;gb=gb+1)begin:obs_bank
   assign raw_v[32*gs+gb]=dut.u_mem.slice[gs].u_slice.bank[gb].u_bank.wvq;
   assign raw_a[9*(32*gs+gb)+:9]=dut.u_mem.slice[gs].u_slice.bank[gb].u_bank.waq;
   assign raw_m[4*(32*gs+gb)+:4]=dut.u_mem.slice[gs].u_slice.bank[gb].u_bank.wmq;
   assign raw_t[8*(32*gs+gb)+:8]=dut.u_mem.slice[gs].u_slice.bank[gb].u_bank.wtq;
  end
 end endgenerate
 initial begin
  for(i=0;i<16384;i=i+1)begin used[i]=0;boot_done[i]=0;image[i]=0;wc[i]=-1;slices[i]=0;raw_slices[i]=0;end
  for(i=0;i<MAXC;i=i+1)begin ev[i]=0;ed[i]=0;sev[i]=0;sed[i]=0;end
  if(!$value$plusargs("dir=%s",dir))$fatal(1,"dir required");
  $readmemh({dir,"/cfg.mem"},cfg);$readmemh({dir,"/h.mem"},hm);$readmemh({dir,"/k.mem"},km);
  $readmemh({dir,"/w.mem"},wm);$readmemh({dir,"/v.mem"},vm);$readmemh({dir,"/y.mem"},ym);
  for(i=0;i<640;i=i+1)begin
   for(j=0;j<32;j=j+1)begin
    image[256+i][16*j+:16]=hm[160*(j%4)+(8*i+j/4)/32][32*((8*i+j/4)%32)+16+:16];
    expected_y[i][16*j+:16]=ym[160*(j%4)+(8*i+j/4)/32][32*((8*i+j/4)%32)+16+:16];
   end
   used[256+i]=1;
  end
  for(b=0;b<160;b=b+1)begin
   for(q=0;q<4;q=q+1)begin
    put(stripe(8192,b,5*q+1),km[160*q+b][0+:512]);put(stripe(8192,b,5*q+2),km[160*q+b][512+:512]);
    put(stripe(8192,b,5*q+3),wm[160*q+b][0+:512]);put(stripe(8192,b,5*q+4),wm[160*q+b][512+:512]);
   end
   put(stripe(13824,b,1),vm[b][0+:512]);put(stripe(13824,b,2),vm[b][512+:512]);
  end
  put(64,0);image[64][0+:32]=256|(1<<18);image[64][32+:32]=8192;image[64][64+:32]=8192;
  image[64][96+:32]=13824;image[64][128+:32]=256;image[64][160+:64]=cfg[0];
  repeat(5)@(negedge ck);rss=1;repeat(8)@(negedge ck);
  // Exceptional host boot uses a precomputed fixture-only bank-distinct batch on up to16 real SU ports.
  // No readiness, result or DUT state participates; each fixed batch is followed by three idle edges.
  while(preloads<3521)begin
   @(negedge ck);#0.01;su_wqv=0;boot_banks=0;boot_n=0;
   for(r=0;r<16384;r=r+1)if(used[r]&&!boot_done[r]&&!boot_banks[bank(r)]&&boot_n<16)begin
    su_wqv[boot_n]=1;su_wq[14*boot_n+:14]=r;su_wqm[16*boot_n+:16]=16'hffff;
    su_wqd[512*boot_n+:512]=image[r];boot_done[r]=1;boot_banks[bank(r)]=1;
    boot_n=boot_n+1;preloads=preloads+1;
   end
   if(boot_n==0)$fatal(1,"preload schedule incomplete");
   @(negedge ck);#0.01;su_wqv=0;repeat(2)@(negedge ck);
  end
  repeat(32)@(negedge ck);
  if(preloads!=3521||commits!=4*3521||rawcommits!=4*3521)$fatal(1,"preload commit count");
  wait(mix_st[1]);@(negedge ck);#0.01;start=cy;mix_cmd={1'b1,84'd0};mix_cmd[6:0]=53;mix_cmd[7+:14]=64;
  @(negedge ck);#0.01;mix_cmd=0;wait(mix_done[8]);@(negedge ck);#0.01;elapsed=cy-start;
  if(mix_done[7:0]!=53||writes!=640||reads!=4161||answers!=20480)$fatal(1,"completion/count mismatch writes=%0d reads=%0d answers=%0d",writes,reads,answers);
  // Fail explicitly on a timing-convention disagreement; never infer or retime the price.
  if(elapsed!=EXPECTED_CYCLES || first_w-start!=FIRST_W || last_w-start!=LAST_W || last_w-first_w!=159)
   $fatal(1,"fixed calendar mismatch cycles=%0d expected=%0d write_span=%0d..%0d",elapsed,EXPECTED_CYCLES,first_w-start,last_w-start);
  repeat(32)@(negedge ck);
  if(commits!=4*(3521+640)||rawcommits!=4*(3521+640))$fatal(1,"final commit count");
  for(i=0;i<640;i=i+1)begin @(negedge ck);#0.01;su_rqv=1;su_rq[0+:14]=256+i;end
  @(negedge ck);#0.01;su_rqv=0;repeat(50)@(negedge ck);
  if(writes!=640||readbacks!=640)$fatal(1,"repeat/readback count");
  $display("PASS MIX4_NATIVE_VM128 RL16 raw_write9 commit_return11 RS5 exact20480 writes640 reads4161 preloads3521 readbacks640 rawcommits=%0d returnedcommits=%0d write_span=%0d..%0d cycles=%0d",rawcommits,commits,first_w-start,last_w-start,elapsed);$finish;
 end
endmodule
