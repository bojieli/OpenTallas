`timescale 1ps/1ps
`default_nettype none
// Source-bound control oracle. Actual FR, FIN1 and FIN2; finite services,
// no arithmetic datapath or native throughput claim. Admission uses ret.ready only.
module tb_hgi_qdq_core_fin2_oracle;
 parameter integer MUT_CAND=0, CORE_SPANPIPE=1, FR_SPANPIPE=1;
 reg cf=0, cc=0, rst_n=0; reg [682:0] rec=0;
 initial begin #61; forever begin cf=1;#416;cf=0;#417;end end
 initial begin #487;forever begin cc=1;#416;cc=0;#417;end end
 wire sv1,sv3,nf;wire [189:0] s3;
 ot_hgi_qdq_fr #(.SPANPIPE(FR_SPANPIPE)) front(.clk(cf),.rst_n(rst_n),.rec(rec),.s1_v(sv1),.s3_v(sv3),.s3(s3),.nfault(nf));
 reg [7:0] cr=0,pop=0;reg grant=0,fire=0,fin=0,abad=0,wbad=0,aidle=1,widle=1;
 wire [2:0] ret0,ret1;wire [127:0] w0,w1;wire rg0,rg1,ar0,ar1,bv0,bv1,act0,act1;wire [39:0] bp0,bp1;
 ot_hgi_qdq_core #(.FIN_BYPASS(1),.SPANPIPE(CORE_SPANPIPE)) reference_core(
 .clk(cc),.rst_n(rst_n),.i_s1_v(sv1),.i_s3_v(sv3),.i_s3(s3),.i_nfault(nf),.ret(ret0),.wrq(w0),.wrq_cr(cr),.rg_req(rg0),.rg_gnt(grant),.asm_rst_n(ar0),.bp_v(bv0),.bp(bp0),.i_pop(pop),.i_fire(fire),.i_abad(abad),.i_aidle(aidle),.o_act(act0),.i_fin(fin),.i_wbad(wbad),.i_widle(widle));
 ot_hgi_qdq_core_fin2 #(.FIN_BYPASS(2),.SPANPIPE(CORE_SPANPIPE),.MUT(MUT_CAND)) candidate(
 .clk(cc),.rst_n(rst_n),.i_s1_v(sv1),.i_s3_v(sv3),.i_s3(s3),.i_nfault(nf),.ret(ret1),.wrq(w1),.wrq_cr(cr),.rg_req(rg1),.rg_gnt(grant),.asm_rst_n(ar1),.bp_v(bv1),.bp(bp1),.i_pop(pop),.i_fire(fire),.i_abad(abad),.i_aidle(aidle),.o_act(act1),.i_fin(fin),.i_wbad(wbad),.i_widle(widle));
 localparam integer CAP=8192;
 // Independent descriptor ledger from actual FR output; fields decoded by ABI.
 reg [189:0] packets[0:CAP-1];integer np=0,nret=0,walk=0,row=0,beat=0,enq_idx=0;integer packet_slot[0:CAP-1];reg [15:0] expected_dep;
 integer cycle=0,issued=0,fired=0,finished=0,credits=0,popped=0;
 integer retired_total=0,admitted_total=0,enqueues=0,wraps=0,concurrent=0,min_age=1000000;
 integer covraw=0,covwar=0,covwaw=0,covrej=0,covmult=0,covcreditstall=0,covbeatstall=0;
 integer mode=0;integer oldhd,oldqt;reg oldenq,oldrt; integer age[0:15];integer epoch=0;
 integer rdue[0:7][0:CAP-1],rh[0:7],rt[0:7],avail[0:7];
 integer bdue[0:CAP-1],bh=0,bt=0;reg [7:0] bhit[0:CAP-1];reg blast[0:CAP-1];
 integer fdue[0:CAP-1],fh=0,ft=0;
 reg resetting=1;integer delayc,delaya;reg [7:0] mask;reg readybeat;
 reg el;reg [17:0] al,ah,ol,oh;reg [14:0] as_,os_,rs_,ws_;reg [15:0] bpr;reg [2:0] nsl;reg [19:0] rows;reg [17:0] hdr;
 integer sec,nsec,osec,lane;reg last;reg [17:0] pal,pah,pol,poh;
 always @(posedge cc) begin
   oldhd=reference_core.hd;oldqt=reference_core.qt;oldenq=reference_core.s3_v;oldrt=reference_core.rt_ok;
   if(reference_core.rr_n[0] && sv3) begin
     if(np==CAP)$fatal(1,"ORACLE_DESCRIPTOR_CAPACITY");packets[np]=s3;np=np+1;
   end
 end
 always @(negedge cc) begin
   cycle=cycle+1;
   if(ret0!==ret1 || rg0!==rg1 || act0!==act1 || ar0!==ar1 || bv0!==bv1 || (bv0 && bp0!==bp1))
     $fatal(1,"CORE_FIN2_PORT_MISMATCH cycle=%0d ret=%b/%b bp=%h/%h",cycle,ret0,ret1,bp0,bp1);
   for(integer l=0;l<8;l=l+1)if(w0[l*16+15]!==w1[l*16+15] || (w0[l*16+15] && w0[l*16+:15]!==w1[l*16+:15]))
     $fatal(1,"CORE_FIN2_PORT_MISMATCH wrq lane=%0d cycle=%0d",l,cycle);
   cr=0;pop=0;fire=0;fin=0;grant=rg0 && cycle%11!=0 && cycle%11!=1;
   if(!ar0)begin
     np=0;nret=0;enq_idx=0;walk=0;row=0;beat=0;bh=0;bt=0;fh=0;ft=0;
     issued=0;fired=0;finished=0;credits=0;popped=0;
     for(integer l=0;l<8;l=l+1)begin rh[l]=0;rt[l]=0;avail[l]=0;end
     for(integer q=0;q<16;q=q+1)age[q]=-100000;
     aidle=1;widle=1;resetting=1;
   end else begin
     if(resetting)begin resetting=0;epoch=epoch+1;end
     if(MUT_CAND==0)begin
       if({reference_core.q_v,reference_core.qt,reference_core.rp,reference_core.hd,reference_core.occ,reference_core.fin_c,reference_core.bad} !==
          {candidate.q_v,candidate.qt,candidate.rp,candidate.hd,candidate.occ,candidate.fin_c,candidate.bad})$fatal(1,"CORE_FIN2_STATE_MISMATCH");
       for(integer q=0;q<16;q=q+1)if((reference_core.q_dep[q]&reference_core.q_v)!==(candidate.q_dep[q]&candidate.q_v))$fatal(1,"CORE_FIN2_LIVE_DEP_MISMATCH q=%0d",q);
       if((candidate.q_v&candidate.dep_clear)!=0)$fatal(1,"ORACLE_LIVE_PENDING_CLEAR");
     end
     if(oldenq)begin
       if(enq_idx>=np)$fatal(1,"ORACLE_ENQUEUE_WITHOUT_DESCRIPTOR");
       expected_dep=0;
       al=packets[enq_idx][188-:18];ah=packets[enq_idx][170-:18];ol=packets[enq_idx][152-:18];oh=packets[enq_idx][134-:18];
       for(integer p=0;p<enq_idx;p=p+1)if(p>=nret && packets[p][189] && packets[enq_idx][189] && !(oldrt && p==nret))begin
         pal=packets[p][188-:18];pah=packets[p][170-:18];pol=packets[p][152-:18];poh=packets[p][134-:18];
         if(al<=poh && pol<=ah)begin expected_dep[packet_slot[p]]=1;covraw=covraw+1;end
         if(ol<=pah && pal<=oh)begin expected_dep[packet_slot[p]]=1;covwar=covwar+1;end
         if(ol<=poh && pol<=oh)begin expected_dep[packet_slot[p]]=1;covwaw=covwaw+1;end
       end
       if(MUT_CAND==0 && (candidate.q_dep[oldqt]&candidate.q_v)!==expected_dep)$fatal(1,"ORACLE_SEMANTIC_DEP_MASK slot=%0d got=%h expected=%h",oldqt,candidate.q_dep[oldqt]&candidate.q_v,expected_dep);
       packet_slot[enq_idx]=oldqt;enq_idx=enq_idx+1;
       enqueues=enqueues+1;if(oldqt==15)wraps=wraps+1;
       if(cycle-age[oldqt]<2)$fatal(1,"ORACLE_REUSE_BEFORE_CLEAR slot=%0d age=%0d",oldqt,cycle-age[oldqt]);
       if(age[oldqt]>0 && cycle-age[oldqt]<min_age)min_age=cycle-age[oldqt];
     end
     if(ret0[1])begin
       if(!oldrt)$fatal(1,"ORACLE_RETIRE_PULSE");age[oldhd]=cycle;nret=nret+1;retired_total=retired_total+1;
       if(oldenq)begin concurrent=concurrent+1;if(oldhd==oldqt)$fatal(1,"ORACLE_SIMULTANEOUS_REUSE");end
     end
     if(reference_core.r_act && !reference_core.r_cr_ok)covcreditstall=covcreditstall+1;
     if(reference_core.b_used==32)covbeatstall=covbeatstall+1;
     // Returned credit is tied to one real issued request, in-order within each lane.
     for(integer l=0;l<8;l=l+1)if(rh[l]<rt[l] && rdue[l][rh[l]]<=cycle)begin
       cr[l]=1;rh[l]=rh[l]+1;avail[l]=avail[l]+1;credits=credits+1;
     end
     if(bv0)begin
       while(walk<np && !packets[walk][189])begin walk=walk+1;covrej=covrej+1;end
       if(walk>=np)$fatal(1,"ORACLE_BEAT_WITHOUT_DESCRIPTOR");
       {el,al,ah,ol,oh,as_,os_,rs_,ws_,bpr,nsl,rows,hdr}=packets[walk];
       sec=int'(as_)+row*int'(rs_)+beat*4;osec=int'(os_)+row*int'(ws_)+beat*4;
       nsec=(beat+1==bpr)?int'(nsl):4;lane=sec%8;last=(beat+1==bpr && row+1==rows);mask=0;
       for(integer x=0;x<nsec;x=x+1)mask[(lane+x)%8]=1;
       if(bp0!=={3'(lane),3'(nsec),15'(osec),last,hdr})$fatal(1,"ORACLE_BEAT_FIELDS record=%0d row=%0d beat=%0d",walk,row,beat);
       if(row==0 && beat==0)begin
         if(rows>1)covmult=covmult+1;
         for(integer p=0;p<walk;p=p+1)if(p>=nret && packets[p][189])begin
           pal=packets[p][188-:18];pah=packets[p][170-:18];pol=packets[p][152-:18];poh=packets[p][134-:18];
           if((al<=poh && pol<=ah)||(ol<=pah && pal<=oh)||(ol<=poh && pol<=oh))$fatal(1,"ORACLE_UNRETIRED_HAZARD record=%0d older=%0d",walk,p);
         end
       end
       delayc=(mode==1)?68:((mode==0)?2:(5+cycle%19));delaya=(mode==0)?68:2;
       for(integer l=0;l<8;l=l+1)begin
         if(w0[l*16+15]!==mask[l])$fatal(1,"ORACLE_REQUEST_MASK");
         if(mask[l])begin
           if(w0[l*16+:15]!==15'(sec+((l-lane+8)%8)))$fatal(1,"ORACLE_REQUEST_ADDRESS");
           if(rt[l]==CAP)$fatal(1,"ORACLE_RESPONSE_CAPACITY");rdue[l][rt[l]]=cycle+delayc;rt[l]=rt[l]+1;
         end
       end
       if(bt==CAP)$fatal(1,"ORACLE_BEAT_CAPACITY");bhit[bt]=mask;blast[bt]=last;bdue[bt]=cycle+delaya;bt=bt+1;issued=issued+1;
       if(beat+1==bpr)begin beat=0;if(row+1==rows)begin row=0;walk=walk+1;end else row=row+1;end else beat=beat+1;
     end else for(integer l=0;l<8;l=l+1)if(w0[l*16+15])$fatal(1,"ORACLE_REQUEST_WITHOUT_BEAT");
     // Pop only complete beats whose real lane responses exist.
     readybeat=bh<bt && bdue[bh]<=cycle && cycle%7<5;
     if(bh<bt)for(integer l=0;l<8;l=l+1)if(bhit[bh][l] && avail[l]==0)readybeat=0;
     if(readybeat)begin
       fire=1;pop=bhit[bh];for(integer l=0;l<8;l=l+1)if(pop[l])begin avail[l]=avail[l]-1;popped=popped+1;end
       if(blast[bh])begin if(ft==CAP)$fatal(1,"ORACLE_FIN_CAPACITY");fdue[ft]=cycle+2+cycle%16;ft=ft+1;end
       bh=bh+1;fired=fired+1;
     end
     if(fh<ft && fdue[fh]<=cycle)begin fin=1;fh=fh+1;finished=finished+1;end
     aidle=(bh==bt);widle=(bh==bt && fh==ft);
     if(fired>issued || popped>credits)$fatal(1,"ORACLE_FEEDBACK_UNDERFLOW");
   end
 end
 function automatic [255:0] descriptor(input integer base,nn,mm,stride);
   reg [255:0] d;begin d=0;d[1:0]=1;d[47:8]=40'(base);d[67:48]=20'(nn);d[87:68]=20'(mm);d[119:88]=32'(stride);descriptor=d;end
 endfunction
 integer prev_a=0,prev_o=0;
 task automatic drive(input integer k,input integer badcount=0);
   reg [127:0] h;reg [255:0] a,o;integer ab,ob,n,m,shape;
   begin
     // Each five-record group contains disjoint then RAW/WAR/WAW/exact-inplace.
     shape=k%10;n=32*(1+k%4);m=1+k%3;ab=8192+(k/10%64)*1024;ob=ab+512;
     if(shape==1)begin ab=prev_o;end
     if(shape==2)begin ob=prev_a;end
     if(shape==3)begin ob=prev_o;end
     if(shape==4)ob=ab;
     if(mode<2)begin shape=9;n=128;m=3;ab=8192+(k%128)*1024;ob=ab+512;end
     h=0;h[127:124]=4;h[123:118]=4+(k%2);h[99:93]=7'b0010001;h[71:64]=8'(k);
     a=descriptor(ab,n,m,n);o=descriptor(ob,n,m,n);
     case(shape)
       5:o[47:8]=40'(ab+8); // unsupported partial in-place overlap
       6:a[87:68]=0;
       7:h[127:124]=3;
       8:a[1:0]=2;
       default:begin end
     endcase
     prev_a=ab;prev_o=ob;rec={21'(n+badcount),21'(n),o,a,h,1'b1};admitted_total=admitted_total+1;
   end
 endtask
 task automatic send(input integer count);
   begin
     for(integer k=0;k<count;k=k+1)begin
       @(negedge cf);rec=0;while(!ret0[0])@(negedge cf);drive(k);
     end
     @(negedge cf);rec=0;
   end
 endtask
 task automatic drain(input integer count);
   integer start,bound;
   begin start=cycle;bound=count*(12*(68+5+17)+64)+256;
     while(nret<count)begin @(negedge cf);if(cycle-start>bound)$fatal(1,"ORACLE_BOUNDED_LIVENESS nret=%0d target=%0d",nret,count);end
     repeat(24)@(negedge cf);
     if(np!=count || nret!=count || bh!=bt || fh!=ft)$fatal(1,"ORACLE_DRAIN_LEDGER");
     for(integer l=0;l<8;l=l+1)if(rh[l]!=rt[l] || avail[l]!=0)$fatal(1,"ORACLE_RESPONSE_LEAK");
   end
 endtask
 task automatic reset_epoch;
   begin @(negedge cf);rec=0;rst_n=0;abad=0;wbad=0;repeat(16)@(negedge cf);rst_n=1;repeat(16)@(negedge cf);
     if(ret0[1] || bv0 || reference_core.q_v!=0 || candidate.q_v!=0)$fatal(1,"ORACLE_WARM_RESET_STALE");
   end
 endtask
 initial begin
   reset_epoch();mode=0;send(512);drain(512);
   reset_epoch();mode=1;send(512);drain(512);
   reset_epoch();mode=2;send(512);drain(512);
   // Reset in flight with accepted descriptors and finite outstanding work.
   reset_epoch();mode=1;send(3);repeat(8)@(negedge cf);
   if(np==nret)$fatal(1,"ORACLE_WARM_RESET_NOT_IN_FLIGHT");reset_epoch();send(96);drain(96);
   // Real record-count sticky nfault; do not counterfeit a control-level stub.
   reset_epoch();@(negedge cf);while(!ret0[0])@(negedge cf);drive(0,1);@(negedge cf);rec=0;repeat(48)@(negedge cf);
   if(!nf || !ret0[2] || !ret1[2])$fatal(1,"ORACLE_NFAULT_NOT_OBSERVED");
   reset_epoch();mode=1;send(3);@(negedge cf);abad=1;repeat(2)@(negedge cf);abad=0;drain(3);
   reset_epoch();mode=1;send(3);@(negedge cf);wbad=1;repeat(2)@(negedge cf);wbad=0;drain(3);
   if(wraps<64 || concurrent==0 || min_age<2 || covraw==0 || covwar==0 || covwaw==0 || covrej==0 || covmult==0 || covcreditstall==0)
     $fatal(1,"ORACLE_COVERAGE wraps=%0d concurrent=%0d min_age=%0d crstall=%0d",wraps,concurrent,min_age,covcreditstall);
   $display("PASS CORE_FIN2_ORACLE span=%0d epochs=%0d admitted=%0d retired=%0d enqueues=%0d wraps=%0d concurrent=%0d min_reuse_age=%0d RAW=%0d WAR=%0d WAW=%0d rejected=%0d multi=%0d credit_stall=%0d beat_stall=%0d",CORE_SPANPIPE,epoch,admitted_total,retired_total,enqueues,wraps,concurrent,min_age,covraw,covwar,covwaw,covrej,covmult,covcreditstall,covbeatstall);$finish;
 end
endmodule
`default_nettype wire
