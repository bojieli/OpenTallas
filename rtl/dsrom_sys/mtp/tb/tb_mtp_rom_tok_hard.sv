`timescale 1ns/1ps
// Full 8-user x 16-slot lookup, 4-edge pipeline; writes are fenced before reads.
module tb_mtp_rom_tok_hard;
    parameter integer LOOKUP = 2; // 0 original,1 r3,2 HARD
    localparam integer EDGES = LOOKUP==0 ? 1 : LOOKUP==1 ? 2 : 4;
    reg clk=0; always #1 clk=~clk;
    reg rn=0, c_we=0, dw_v=0, pr_re=0;
    reg [1:0] c_sel=0; reg [9:0] c_user=0, pr_user=0;
    reg [20:0] c_pos=0,c_val=0,pr_pos=0; reg [3:0] pr_blk=0;
    reg [511:0] dw_d=0;
    wire [9:0] cu; wire [20:0] cp,cg,q; wire qk,ft;
    generate if (LOOKUP==0) begin : baseline
    ot_dsrom_wfc_tok dut(
        .clk(clk),.rst_n(rn),.c_we(c_we),.c_sel(c_sel),.c_user(c_user),.c_pos(c_pos),.c_val(c_val),
        .cfg_users(cu),.cfg_prompt_len(cp),.cfg_gen_len(cg),.dw_v(dw_v),.dw_d(dw_d),
        .pr_re(pr_re),.pr_user(pr_user),.pr_pos(pr_pos),.pr_blk(pr_blk),.pr_q(q),.pr_qk(qk),.fault(ft));
    end else begin : successor
    ot_dsrom_wfc_tok_r3 #(.HARD_READ(LOOKUP==2)) dut(
        .clk(clk),.rst_n(rn),.c_we(c_we),.c_sel(c_sel),.c_user(c_user),.c_pos(c_pos),.c_val(c_val),
        .cfg_users(cu),.cfg_prompt_len(cp),.cfg_gen_len(cg),.dw_v(dw_v),.dw_d(dw_d),
        .pr_re(pr_re),.pr_user(pr_user),.pr_pos(pr_pos),.pr_blk(pr_blk),.pr_q(q),.pr_qk(qk),.fault(ft));
    end endgenerate
    integer valid[0:127],prompt[0:127],pos[0:127],ep[0:127],tok[0:127];
    integer pv[0:3],pk[0:3],pt[0:3],reads=0,hits=0,stale=0,invalids=0,idle=0;
    integer i,j,u,b,k,ix,pass;
    task cwrite(input integer sel, usr, p, val);
        begin @(negedge clk); c_we=1;c_sel=sel;c_user=usr;c_pos=p;c_val=val;
            @(negedge clk);c_we=0;end
    endtask
    task tick(input integer ena,usr,p,epoch);
        integer t,x,known,value;
        begin
            @(negedge clk);pr_re=ena;pr_user=usr;pr_pos=p;pr_blk=epoch;
            known=0;value=0;
            if(usr<8) begin x=usr*16+(p%16);
                known=valid[x] && pos[x]==p && (prompt[x] || ep[x]==epoch);value=tok[x];end
            for(t=3;t>0;t=t-1)begin pv[t]=pv[t-1];pk[t]=pk[t-1];pt[t]=pt[t-1];end
            pv[0]=ena;pk[0]=known;pt[0]=value;
            @(posedge clk);#0.1;
            if(pv[EDGES-1])begin
                if(qk!==pk[EDGES-1][0] || (pk[EDGES-1] && q!==pt[EDGES-1][20:0]))begin
                    $display("MTP_TOK_HARD FAIL read=%0d got=%b/%0d expected=%0d/%0d",reads,qk,q,pk[EDGES-1],pt[EDGES-1]);$finish;end
                reads=reads+1;if(pk[EDGES-1])hits=hits+1;
            end
        end
    endtask
    initial begin
        for(i=0;i<128;i=i+1)begin valid[i]=0;prompt[i]=0;pos[i]=0;ep[i]=0;tok[i]=0;end
        for(i=0;i<4;i=i+1)begin pv[i]=0;pk[i]=0;pt[i]=0;end
        cwrite(0,0,0,8);cwrite(1,0,0,16);cwrite(2,0,0,200);
        for(u=0;u<8;u=u+1)for(k=0;k<16;k=k+1)begin
            cwrite(3,u,k,1000+u*16+k);ix=u*16+k;valid[ix]=1;prompt[ix]=1;pos[ix]=k;tok[ix]=1000+ix;
        end
        @(negedge clk);rn=1;
        repeat(3)@(posedge clk);
        // Prompt, invalid high user bits, bubbles, continuous II=1.
        for(i=0;i<256;i=i+1)begin
            u=i%8;k=(i/8)%16;tick(1,u,k,i%16);
            if(i%13==0)begin tick(1,u+256,k,i%16);invalids=invalids+1;end
            if(i%11==0)begin tick(0,0,0,0);idle=idle+1;end
        end
        repeat(4)tick(0,0,0,0);
        // Actual five-token DRAFT flit, full-position wrap and epoch mismatch.
        for(pass=0;pass<3;pass=pass+1)begin
            for(u=0;u<8;u=u+1)begin
                b=31+pass*65536+u*16;
                @(negedge clk);dw_v=1;dw_d=0;dw_d[16+:4]=4;dw_d[32+:8]=u;
                dw_d[40+:21]=b;dw_d[135+:4]=pass+3;dw_d[248+:3]=5;
                for(k=0;k<5;k=k+1)begin dw_d[256+k*21+:21]=90000+pass*1000+u*5+k;
                    ix=u*16+(b+k)%16;valid[ix]=1;prompt[ix]=0;pos[ix]=b+k;ep[ix]=pass+3;tok[ix]=90000+pass*1000+u*5+k;end
                @(negedge clk);dw_v=0;
            end
            repeat(4)@(posedge clk);
            for(u=0;u<8;u=u+1)for(k=0;k<5;k=k+1)begin
                b=31+pass*65536+u*16;
                tick(1,u,b+k,pass+3);tick(1,u,b+k,pass+4);stale=stale+1;
                tick(1,u,b+k+16,pass+3);
            end
            repeat(4)tick(0,0,0,0);
        end
        if(ft || hits<200 || reads<600 || stale!=120)begin $display("MTP_TOK_HARD FAIL coverage/fault");$finish;end
        $display("MTP_TOK_HARD PASS reads=%0d hits=%0d stale=%0d invalid_users=%0d bubbles=%0d latency_edges=%0d II=1",reads,hits,stale,invalids,idle,EDGES);
        $finish;
    end
endmodule
