`timescale 1ns/1ps
module tb_hbm_idx_ordered_candidate #(parameter integer MUT=0);
    reg ck=0; always #5 ck=~ck;
    reg rst=0;
    reg [89:0] fs=0;
    reg [2439:0] si=0;
    wire [71:0] co;
    reg coc=0;
    wire [1:0] ev; wire qlast;
    reg [1:0] selector_ev=0;
    ot_hbm_idx_ordered_candidate #(.MUT(MUT)) dut(.*,.co_quarter_last(qlast));
    reg [68:0] gold[0:3][0:170];
    integer nqs[0:3], sent[0:3], nbeats[0:3];
    integer due[0:7], dh, dt, outstanding;
    integer expect_q, expect_b, got, bad=0, cycle=0, start_cycle, done_seen;
    integer words=0, frames=0, delayed=0, first_output;
    reg checking=0;
    integer rank=23, position, n;
    function automatic [15:0] key(input [15:0] v);
        key=(v[14:0]==0)?16'h8000:v[15]?~v:{1'b1,v[14:0]};
    endfunction
    function automatic [15:0] score(input integer frame,q,b,l);
        case ((frame+q+b+l)%11)
          0:score=16'hff80;
          1:score=16'h8000;
          2:score=16'h0000;
          3:score=16'h7f80;
          default:score=16'((frame*47+q*13+b*7+l*3)%256+16'h3e00);
        endcase
        if(frame%5==0 && b%7==0) score=16'hff80;
    endfunction
    always @(posedge ck) begin
        cycle=cycle+1;
        if(checking) begin
            if(co[0]) begin
                reg [68:0] g;
                g=gold[expect_q][expect_b];
                if(co[71:38]!==g[68:35] || co[37:6]!==g[34:3] || co[5:4]!==g[2:1] ||
                   co[3:2]!==2'(expect_q) || co[1]!== (g[0]&&expect_q==3) || qlast!==g[0]) begin
                    if(bad<8) $display("ORDERED mismatch frame%0d q%0d beat%0d got%h gold%h",frames,expect_q,expect_b,co,g);
                    bad=bad+1;
                end
                if(first_output==0) first_output=cycle;
                words=words+int'(co[4])+int'(co[5]);
                got=got+1; outstanding=outstanding+1;
                if(outstanding>8) begin $display("ORDERED credit overflow"); bad=bad+1; end
                due[dt%8]=cycle+3+($urandom%14); dt=dt+1;
                if(g[0]) begin expect_q=expect_q+1; expect_b=0; end
                else expect_b=expect_b+1;
            end
            if(ev[1]) begin $display("ORDERED unexpected fault frame%0d",frames); bad=bad+1; end
            if(ev[0]) done_seen=1;
        end
    end
    task automatic frame(input integer f,input integer nn);
        integer q,b,l,bl,global_id,off; reg [609:0] beat;
        reg [15:0] maximum[0:1]; reg [1:0] vl; reg [33:0] ids;
        begin
            checking=0; rst=0; fs=0; si=0; coc=0; selector_ev=0; repeat(5) @(negedge ck);
            rst=1; repeat(3) @(negedge ck);
            n=nn; frames=f; position=((23+96*(nn==0?0:((nn-1)/8)))*8)+(f%8);
            // Half the frames name a foreign owner's newest key; no local pin.
            if(f%2==0) position=position+8;
            position=position&1048575;
            got=0; expect_q=0; expect_b=0; dh=0; dt=0; outstanding=0; done_seen=0;
            first_output=0;
            for(q=0;q<4;q=q+1) begin
                nqs[q]=(nn<=2736*q)?0:((nn-2736*q>=2736)?2736:nn-2736*q);
                nbeats[q]=(nqs[q]==0)?1:(nqs[q]+15)/16; sent[q]=0;
                for(b=0;b<nbeats[q];b=b+1) begin
                    vl=0; ids=0;
                    for(bl=0;bl<2;bl=bl+1) begin
                        maximum[bl]=16'hff80;
                        ids[17*bl +:17]=17'(rank+96*(q*342+b*2+bl));
                        for(l=0;l<8;l=l+1) begin
                            off=b*16+bl*8+l;
                            if(off<nqs[q]) begin
                                if(l==0) vl[bl]=1;
                                if(key(score(f,q,b,bl*8+l))>key(maximum[bl])) maximum[bl]=score(f,q,b,bl*8+l);
                            end
                        end
                        if(vl[bl] && ids[17*bl +:17]==position/8) maximum[bl]=16'h7f80;
                        if(maximum[bl]==16'hff80) vl[bl]=0;
                    end
                    gold[q][b]={ids,maximum[1],maximum[0],vl,b==nbeats[q]-1};
                end
            end
            start_cycle=cycle; checking=1;
            fs={1'b0,1'b1,10'd512,14'(nn),7'(rank),20'(position),4'd0,32'd55,1'b1};
            @(negedge ck); fs=0; repeat(3) @(negedge ck);
            while(!done_seen && cycle-start_cycle<6000) begin
                si=0;
                selector_ev=(cycle-start_cycle==500)?2'd1:2'd0;
                for(q=0;q<4;q=q+1) if(sent[q]<nbeats[q] && ($urandom%4!=0)) begin
                    b=sent[q]; beat=0; beat[0]=1; beat[1]=(b==nbeats[q]-1);
                    for(l=0;l<16;l=l+1) begin
                        global_id=(rank+96*(q*342+b*2+l/8))*8+l%8;
                        beat[34+l*16 +:16]=score(f,q,b,l);
                        beat[290+l*20 +:20]=20'(global_id);
                        beat[18+l]=(b*16+l<nqs[q]);
                    end
                    si[610*q +:610]=beat; sent[q]=sent[q]+1;
                end
                coc=0;
                // Frame zero retains all four full quarters before releasing
                // credits, forcing all actual SRAM stores beyond their heads.
                if(dt>dh && due[dh%8]<=cycle && (f!=1 || cycle-start_cycle>800)) begin
                    coc=1; dh=dh+1; outstanding=outstanding-1;
                end
                @(negedge ck);
            end
            si=0; coc=0; checking=0;
            if(!done_seen || expect_q!=4) begin $display("ORDERED timeout f%0d got%0d expectq%0d",f,got,expect_q); bad=bad+1; end
            $display("ORDERED frame%0d n%0d beats%0d cycles%0d first%0d",f,nn,got,cycle-start_cycle,first_output-start_cycle);
        end
    endtask
    task automatic fault_case(input integer kind);
        reg [609:0] beat;
        begin
            checking=0; rst=0; fs=0; si=0; coc=0; selector_ev=0;
            repeat(4) @(negedge ck); rst=1; repeat(3) @(negedge ck);
            fs={1'b0,1'b1,10'd512,14'd16,7'd23,20'd40000,4'd0,32'd56,1'b1};
            @(negedge ck); fs=0; repeat(3) @(negedge ck);
            beat=0; beat[0]=1; beat[1]=1; beat[33:18]=16'hffff;
            for(integer l=0;l<16;l=l+1) begin
                beat[34+16*l +:16]=16'h3f80;
                beat[290+20*l +:20]=20'((23+96*(l/8))*8+l%8);
            end
            if(kind==0) beat[2]=1; // a refused valid score
            if(kind==1) beat[290 +:20]=20'd0; // false global ID
            if(kind==2) beat[1]=0; // missing required quarter tail
            if(kind==3) selector_ev=2'd2; // selector fault must propagate
            si[609:0]=beat;
            @(negedge ck); si=0; selector_ev=0; repeat(12) @(negedge ck);
            if(!ev[1]) begin $display("ORDERED fault%0d missed",kind); bad=bad+1; end
            else $display("ORDERED fault%0d observed",kind);
        end
    endtask
    initial begin
        frame(1,10944); frame(2,0); frame(3,1); frame(4,8); frame(5,9);
        frame(6,15); frame(7,16); frame(8,17); frame(9,2735); frame(10,2736);
        frame(11,2737); frame(12,5473); frame(13,8209); frame(14,10944);
        for(integer f=15;f<47;f=f+1) frame(f,int'($urandom%10945));
        for(integer k=0;k<4;k=k+1) fault_case(k);
        $display("ORDERED MUT=%0d frames=46 words=%0d errors=%0d %s",MUT,words,bad,bad==0?"PASS":"FAIL");
        $finish;
    end
endmodule
