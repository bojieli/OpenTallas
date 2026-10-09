`timescale 1ns/1ps
module tb_dsrom_engram_dead_source(input wire clk);
    reg rst_n=0,cv=0;reg [63:0] command_word=0;
    wire [1:0] co;wire [7:0] cu;wire [20:0] cp,ct;wire [2:0] ctype;
    ot_s81_source_command_decode decoder(.word(command_word),.op(co),.tag(),.user(cu),.pos(cp),.token(ct),.token_type(ctype));
    wire cr,active,hf,pf,lf,cplv;wire [91:0] cpl;wire [7:0] users,done,tu,pru;wire [20:0] plen,glen,eos,prp,prq,tp,ti;
    wire [21:0] maxl;wire eosen,prre,tv;
    wire [2:0] prtype,jtype;wire jv,jr;wire [11:0] ju;wire [20:0] jp,jt;
    reg iv=0;wire ir;reg [511:0] id=0;
    wire lv,lready,ld;wire [67:0] lids;wire [11:0] lu;wire [20:0] lp,lt;
    integer cy=0,mode=0,seen=0,errors=0,qw=0,qr=0,i,j,u,n;reg queue_phase=0;
    integer qage[0:511];reg [11:0] qu[0:511];reg [20:0] qp[0:511];
    reg [16:0] cmap[0:129279];reg [8191:0] dir;reg [67:0] want;reg blocked;
    reg [63:0] command_mem[0:257];reg [8191:0] command_path;
    wire lr=(cy%11)>3;
    assign jr=lready && (cy%13)>3;
    ot_s81_host_cq #(.TOKEN_TYPES(1),.MAXU(64),.PMAX(8),.NW(21),.CQ_DEPTH(512)) h(
        .clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_ready(cr),.cmd_op(co),.cmd_tag(8'd1),.cmd_user(cu),
        .cmd_pos(cp),.cmd_token(ct),.cmd_token_type(ctype),.cpl_valid(cplv),.cpl_ready(1'b1),.cpl_data(cpl),
        .cfg_users(users),.cfg_prompt_len(plen),.cfg_gen_len(glen),.cfg_max_len(maxl),.cfg_eos_en(eosen),.cfg_eos_id(eos),
        .boot_ok(1'b1),.pr_re(prre),.pr_user(pru),.pr_pos(prp),.pr_q(prq),.pr_token_type(prtype),
        .tok_valid(tv),.tok_user(tu),.tok_pos(tp),.tok_id(ti),.users_done(done),.stall_cause(32'b0),.active(active),.fault(hf));
    ot_s81_pkg_ctrl #(.TOKEN_TYPES(1),.SOURCE(1),.MAXU(64),.NW(21),.RXW(1)) p(
        .clk(clk),.rst_n(rst_n),.cfg_users(users),.cfg_prompt_len(plen),.cfg_gen_len(glen),.cfg_max_len(maxl),
        .cfg_eos_en(eosen),.cfg_eos_id(eos),.boot_ok(1'b1),.in_valid(iv),.in_ready(ir),.in_data(id),.in_last(1'b1),
        .job_v(jv),.job_rdy(jr),.job_user(ju),.job_pos(jp),.job_tok(jt),.job_token_type(jtype),.job_done(1'b0),
        .pr_re(prre),.pr_user(pru),.pr_pos(prp),.pr_q(prq),.pr_token_type(prtype),
        .tok_valid(tv),.tok_user(tu),.tok_pos(tp),.tok_id(ti),.users_done(done),.proto_fault(pf));
    ot_dsrom_engram_lead_producer #(.PROTECT_HISTORY(0)) l(
        .clk(clk),.rst_n(rst_n),.t_v(jv && jr),.t_ready(lready),.t_user(ju),.t_pos(jp),.t_tok(jt),
        .t_first(jp==0),.t_dead(jtype!=7),.t_slot(1'b0),.rb_v(1'b0),.rb_user(12'b0),.rb_n(3'b0),
        .out_v(lv),.out_ready(lr),.out_ids(lids),.out_dead(ld),.out_user(lu),.out_pos(lp),.out_tok(lt),.fault(lf));
    function integer raw(input integer who,input integer position);
        if(position==0) raw=who%5==0?129264:20+who;
        else if(position==3) raw=60+who;else raw=129264;
    endfunction
    function integer typ(input integer who,input integer position);
        if(position==0) typ=who%5==0?who%4:7;
        else if(position==1) typ=who%4;
        else if(position==2) typ=(who+1)%4;else typ=7;
    endfunction
    task step;begin @(negedge clk);end endtask
    task command(input integer op,input integer usr,input integer position,input integer token,input integer tt);
        begin while(!cr) step();command_word={1'b0,3'(tt),21'(token),21'(position),8'(usr),8'd1,2'(op)};
            if(mode==3 && op==1) command_word[63]=1;cv=1;step();cv=0;end
    endtask
    always @(posedge clk) begin
        cy<=cy+1;if(cy>20000) $fatal(1,"timeout seen%0d done%0d",seen,done);
        if(rst_n && (hf || pf || lf)) $fatal(1,"source fault");
        if(cplv && cpl[91:90]==3) errors<=errors+1;
        if(lv && lr) begin
            if(mode || lt!=raw(lu,lp) || ld!=(typ(lu,lp)!=7)) $fatal(1,"source type identity user%0d pos%0d tok%0d dead%0d",lu,lp,lt,ld);
            blocked=0;want=0;
            for(j=0;j<4;j=j+1) begin
                blocked=blocked || lp<j;
                if(lp>=j) blocked=blocked || typ(lu,lp-j)!=7;
                want[17*j +:17]=blocked?17'd2:cmap[raw(lu,lp-j)];
            end
            if(lids!==want) $fatal(1,"released window source");
            qu[qw]=lu;qp[qw]=lp;qage[qw]=cy;qw=qw+1;seen<=seen+1;
        end
        if(iv && ir) qr=qr+1;
    end
    always @(negedge clk) begin
        iv=0;id=0;
        if(queue_phase && qr<qw && cy-qage[qr]>8 && cy%4==0) begin
            iv=1;id[24 +:4]=2;id[40 +:12]=qu[qr];id[52 +:21]=qp[qr];id[73 +:21]=129264;
        end
    end
    initial begin
        if(!$value$plusargs("OT_ROM_DIR=%s",dir)) $fatal(1,"images");$readmemh({dir,"/expected.hex"},cmap);
        if(!$value$plusargs("MODE=%d",mode)) mode=0;
        repeat(4) step();rst_n=1;step();
        if(mode==0) begin
            if(!$value$plusargs("COMMANDS=%s",command_path)) $fatal(1,"prepared SOURCE commands");
            $readmemh(command_path,command_mem);
            for(i=0;i<258;i=i+1) begin while(!cr) step();command_word=command_mem[i];cv=1;step();cv=0;end
        end else begin
            for(u=0;u<64;u=u+1) command(1,u,0,mode==2?22:raw(u,0),mode==1?4:mode==2?0:typ(u,0));
            command(2,64,1,1,7);
        end
        if(mode) begin repeat(30) step();if(active || seen || errors!=65) $fatal(1,"typed prompt negative errors%0d",errors);$display("ENGRAM_DEAD_SOURCE NEG mode%0d rejected64+launch",mode);$finish;end
        queue_phase=1;
        while(done!=64 || active) step();repeat(12) step();
        if(seen!=320 || errors) $fatal(1,"source count%0d errors%0d",seen,errors);
        $display("ENGRAM_DEAD_SOURCE PASS users64 prompt256 windows320 all4imageTypes firstDEAD generatedImageRawTEXT stalls feedbackqueue");$finish;
    end
endmodule
