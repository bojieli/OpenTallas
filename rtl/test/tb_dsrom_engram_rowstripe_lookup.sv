`timescale 1ns/1ps
module tb_dsrom_engram_rowstripe_lookup(input wire clk);
    reg rst_n=0,win=0,oc=0;
    reg layer=0;reg [1:0] rank=0;
    wire wc,hqv,hqc,hrv,ov,stv,stbad,lfault,sfault;
    wire [30:0] hqa;wire [2:0] hqt,hrt,ob,os,sts;
    wire [3:0] hri;wire [255:0] hrd;wire [4:0] col;wire [263:0] od;
    wire [64*341-1:0] rq;reg [17791:0] rd=0;
    reg [255:0] atoms[0:53];reg [263:0] beats[0:47];reg [63:0] expected_rq[0:5];
    integer pending[0:63],nextidx[0:63],delay[0:63];reg [16:0] identity[0:63];
    integer cycle=0,got=0,statuses=0,requests=0,credit_pending=0,take_credit,p,j,index,base,lpc,c;
    reg [47:0] seen=0;reg [340:0] word;
    string file_atoms,file_beats,file_rq;
    dsfd_engram_lkp #(.ROWSTRIPE(1),.PIPE(1),.NSLOT(8),.HQ_CRED(8),.O_CRED(16)) lookup(
        .ck(clk),.rst_n(rst_n),.cfg_layer(layer),.cfg_rank(rank),.win_v(win),.win_ids({17'd1,17'd2,17'd3,17'd4}),.win_cred(wc),.rel(4'b0),
        .hq_v(hqv),.hq_atom(hqa),.hq_tag(hqt),.hq_cred(hqc),.hr_v(hrv),.hr_tag(hrt),.hr_idx(hri),.hr_d(hrd),
        .o_v(ov),.o_col(col),.o_beat(ob),.o_slot(os),.o_d(od),.o_cred(oc),.st_v(stv),.st_slot(sts),.st_bad(stbad),.fault(lfault));
    ot_dsrom_engram_rowstripe_service service(.ck(clk),.rst_n(rst_n),.hq_v(hqv),.hq_atom(hqa),.hq_tag(hqt),.hq_cred(hqc),
        .rq(rq),.rd(rd),.hr_v(hrv),.hr_tag(hrt),.hr_idx(hri),.hr_d(hrd),.fault(sfault));
    initial begin
        if($value$plusargs("LAYER=%d",layer)) begin end
        if($value$plusargs("RANK=%d",rank)) begin end
        if(!$value$plusargs("ATOMS=%s",file_atoms) || !$value$plusargs("BEATS=%s",file_beats) || !$value$plusargs("RQ=%s",file_rq)) $fatal(1,"missing vectors");
        $readmemh(file_atoms,atoms);$readmemh(file_beats,beats);$readmemh(file_rq,expected_rq);
        for(p=0;p<64;p=p+1) begin pending[p]=-1;nextidx[p]=0;delay[p]=0;identity[p]=0;end
    end
    always @(posedge clk) begin
        cycle=cycle+1;
        rst_n<=cycle>=10;win<=cycle==20;
        rd<=0;
        if(rst_n) begin
            if(lfault || sfault) $fatal(1,"lookup/service fault");
            if(cycle>10000) $fatal(1,"lookup service drain");
            take_credit=(cycle%2==0 && credit_pending>0);
            oc<=take_credit;credit_pending<=credit_pending+ov-take_credit;
            if(ov) begin
                c=col-rank*6;index=c*8+ob;
                if(c<0 || c>=6 || os!=0 || seen[index] || od!==beats[index]) $fatal(1,"golden lookup payload/column/beat identity");
                seen[index]=1;got=got+1;
            end
            if(stv) begin
                if(stbad || sts!=0) $fatal(1,"lookup CRC/status mismatch");statuses=statuses+1;
            end
            for(p=0;p<64;p=p+1) begin
                word=rq[p*341+:341];
                if(word[0]) begin
                    j=word[38:36];
                    if(j>=6 || p!=expected_rq[j][37:32] || word[31:2]!=expected_rq[j][29:0] || word[1]!=0 || word[35:32]!=8 || pending[p]>=0) $fatal(1,"golden lookup request address/PC");
                    pending[p]=j;identity[p]=word[52:36];nextidx[p]=0;delay[p]=20+p%5;requests=requests+1;
                end
                if(pending[p]>=0) begin
                    if(delay[p]>0) delay[p]=delay[p]-1;
                    else begin
                        index=(nextidx[p]*5)%9;base=(p/32)*8896;lpc=p%32;
                        rd[base+lpc*256+:256]<=atoms[pending[p]*9+index];
                        rd[base+8192+lpc*17+:17]<=identity[p];rd[base+8736+lpc*4+:4]<=index;
                        rd[base+8864+lpc]<=1;
                        nextidx[p]=nextidx[p]+1;if(nextidx[p]==9) pending[p]=-1;
                    end
                end
            end
            if(got==48 && statuses==6 && cycle%16==0) begin
                if(requests!=6 || seen!={48{1'b1}}) $fatal(1,"lookup fullshape accounting");
                $display("ENGRAM_ROWSTRIPE_LOOKUP PASS layer=%0d rank=%0d rows=6 atoms=54 beats=48 crc=6 golden=1 cycles=%0d",layer,rank,cycle);$finish;
            end
        end
    end
endmodule
