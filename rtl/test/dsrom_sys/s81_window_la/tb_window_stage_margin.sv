`timescale 1ns/1ps
// Derived from tb_window_stage_read_qualification for the default-off MARGIN stage
// (claude/takeover-window-stage-20261006).  MARGIN = 0 reproduces the original oracle
// exactly.  MARGIN = 1: the request is evaluated at its effective edge RD = 3 cycles after
// the pin (pin register, per-bank copy, per-column register) and answered one edge later
// than the original (per-bank column-output register): the witnesses are the owner,
// completion and payload state at that effective edge, the same rule as the original.
module tb_window_stage_margin #(parameter integer SPLIT_COLUMNS=0, parameter integer MARGIN=0);
    localparam integer RD = MARGIN ? 3 : 0, ED = MARGIN ? 3 : 2;
    localparam integer NPC=32, NSECT=2176, ROWB=4224;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, job_v=0, req_v=0;
    reg [9:0] job_user=0, req_user=0;
    reg [20:0] job_first=0, req_first_row=0;
    reg [7:0] job_count=128;
    reg [3:0] req_mask=0;
    reg [31:0] in_v=0;
    reg [415:0] in_tag=0;
    reg [127:0] in_beat=0;
    reg [8191:0] in_data=0;
    wire [31:0] in_rdy,acc_v;
    wire [415:0] acc_tag;
    wire [127:0] acc_beat;
    wire [8191:0] acc_data;
    wire all_rows,fault,req_ready,rsp_v,rsp_fault;
    wire [11:0] sectors_landed;
    wire [9:0] rsp_user;
    wire [20:0] rsp_first_row;
    wire [3:0] rsp_mask,rsp_valid_mask;
    wire [4*ROWB-1:0] rsp_rows;
    ot_dsrom_window_stage_pipeline #(.NPC(NPC), .SPLIT_COLUMNS(SPLIT_COLUMNS), .MARGIN(MARGIN)) dut (.*);
    // Request as seen at its effective (witness) edge.
    reg q_v [0:3]; reg [9:0] q_u [0:3]; reg [20:0] q_f [0:3]; reg [3:0] q_m [0:3];
    wire e_v = RD ? q_v[RD-1] : req_v;
    wire [9:0] e_u = RD ? q_u[RD-1] : req_user;
    wire [20:0] e_f = RD ? q_f[RD-1] : req_first_row;
    wire [3:0] e_m = RD ? q_m[RD-1] : req_mask;

    reg [ROWB-1:0] golden[0:127];
    reg [NSECT-1:0] landed=0;
    integer g_user=0,g_first=0,g_count=0,writes=0;
    integer checked=0,valid_lanes=0,denied=0,completion_races=0;
    reg [3:0] ev=0;
    reg [9:0] eu[0:3];
    reg [20:0] er[0:3];
    reg [3:0] em[0:3],eg[0:3];
    reg ef[0:3];
    reg [4*ROWB-1:0] ed[0:3];
    integer a,l,w,s,slot,highest;
    reg [3:0] good;
    reg bad;
    reg [4*ROWB-1:0] data_expected;
    string rows_path;

    function automatic [255:0] sector_data(input integer sec);
        integer row,col;
        begin
            row=sec/17; col=sec%17;
            if(col==16) sector_data={128'b0,golden[row][4096+:128]};
            else sector_data=golden[row][256*col+:256];
        end
    endfunction

    // Check after NBA, but derive request witnesses before writes/job updates.
    // This covers the real last-sector/read collision and accepted old owners.
    always @(posedge clk) begin
        if(!rst_n) begin
            ev=0; landed=0; writes=0; g_user=0; g_first=0; g_count=0;
            for(a=0;a<4;a=a+1) q_v[a]=0;
        end else begin
            good=0; data_expected=0;
            highest=e_m[3]?3:e_m[2]?2:e_m[1]?1:0;
            bad=!(e_m==1 || e_m==3 || e_m==7 || e_m==15) ||
                (22'(e_f)+highest)>=1048576;
            for(l=0;l<4;l=l+1) begin
                w=22'(e_f)+l; slot=w%128;
                if(e_m[l] && w<1048576 && w>=g_first &&
                   w-g_first<g_count && e_u==g_user &&
                   (&landed[slot*17+:17])) begin
                    good[l]=1;
                    data_expected[l*ROWB+:ROWB]=golden[slot];
                end
            end
            for(a=3;a>0;a=a-1) begin
                ev[a]=ev[a-1]; eu[a]=eu[a-1]; er[a]=er[a-1];
                em[a]=em[a-1]; eg[a]=eg[a-1]; ef[a]=ef[a-1]; ed[a]=ed[a-1];
            end
            ev[0]=e_v; eu[0]=e_u; er[0]=e_f;
            em[0]=e_m; eg[0]=good;
            ef[0]=bad || ((e_m & ~good)!=0); ed[0]=data_expected;
            for(a=3;a>0;a=a-1) begin q_v[a]=q_v[a-1]; q_u[a]=q_u[a-1]; q_f[a]=q_f[a-1]; q_m[a]=q_m[a-1]; end
            q_v[0]=req_v; q_u[0]=req_user; q_f[0]=req_first_row; q_m[0]=req_mask;
            if(job_v) begin
                g_user=job_user; g_first=job_first; g_count=job_count;
                landed=0; writes=0;
            end else for(a=0;a<NPC;a=a+1) if(acc_v[a]) begin
                s=4*acc_tag[a*13+:13]+acc_beat[a*4+:4];
                if(s>=NSECT || landed[s] || acc_data[a*256+:256]!==sector_data(s))
                    $fatal(1,"landing identity/payload mismatch sector=%0d",s);
                landed[s]=1; writes=writes+1;
            end
        end
        #1;
        if(!rst_n) begin
            if(rsp_v!==0 || rsp_valid_mask!==0 || rsp_rows!==0)
                $fatal(1,"reset leaked pending/uninitialized payload");
        end else begin
            if(rsp_v!==ev[ED]) $fatal(1,"read latency changed expected=%b actual=%b",ev[ED],rsp_v);
            if(ev[ED]) begin
                if(rsp_user!==eu[ED] || rsp_first_row!==er[ED] || rsp_mask!==em[ED] ||
                   rsp_valid_mask!==eg[ED] || rsp_fault!==ef[ED] || rsp_rows!==ed[ED])
                    $fatal(1,"golden read mismatch row=%0d mask=%h good=%h/%h fault=%b/%b",
                        er[ED],em[ED],eg[ED],rsp_valid_mask,ef[ED],rsp_fault);
                checked=checked+1;
                if(ef[ED]) denied=denied+1;
                for(l=0;l<4;l=l+1) if(eg[ED][l]) valid_lanes=valid_lanes+1;
            end
            if(fault) $fatal(1,"unexpected stage landing fault");
        end
    end

    task automatic open_job(input integer user_id,input integer first);
        begin
            @(negedge clk); req_v=0; job_v=1;
            job_user=10'(user_id); job_first=21'(first);
            @(negedge clk); job_v=0;
        end
    endtask
    task automatic fill_window;
        integer cursor[0:NPC-1];
        integer p,tick,absolute_slot0;
        reg [31:0] takes;
        reg raced;
        begin
            for(p=0;p<NPC;p=p+1) cursor[p]=p;
            raced=0; tick=0;
            absolute_slot0=job_first+((128-job_first[6:0])%128);
            // Shape-derived bound: all2176 sectors plus finite pipeline slots.
            while(writes<NSECT && tick<NSECT+NPC*9+128) begin
                @(negedge clk); in_v=0; req_v=0;
                for(p=0;p<NPC;p=p+1) if(cursor[p]<NSECT) begin
                    in_v[p]=1;
                    in_tag[p*13+:13]=13'(cursor[p]/4);
                    in_beat[p*4+:4]=4'(cursor[p]%4);
                    in_data[p*256+:256]=sector_data(cursor[p]);
                end
                if(!raced && acc_v[16] &&
                   (4*acc_tag[16*13+:13]+acc_beat[16*4+:4])==16) begin
                    req_v=1; req_user=job_user;
                    req_first_row=21'(absolute_slot0); req_mask=1;
                    raced=1; completion_races=completion_races+1;
                end
                @(posedge clk); takes=in_v & in_rdy;
                #2;
                for(p=0;p<NPC;p=p+1) if(takes[p]) cursor[p]=cursor[p]+NPC;
                tick=tick+1;
            end
            @(negedge clk); in_v=0; req_v=0;
            repeat(MARGIN) @(negedge clk);
            if(writes!=NSECT || !all_rows || !raced)
                $fatal(1,"full-shape fill/collision failed writes=%0d all=%b",writes,all_rows);
        end
    endtask
    // Column-conflict fill: pc p owns slots p, p+32, p+64, p+96 and sends each slot's 17 sectors in
    // column order, so the 8 pcs of a bank target the same column together: every landing waits on the
    // lowest-pc winner and the decode/input queues fill (back-pressure through in_rdy).
    integer stalls=0;
    task automatic fill_window_conflict;
        integer cursor[0:NPC-1];
        integer p,tick,sec;
        reg [31:0] takes;
        begin
            for(p=0;p<NPC;p=p+1) cursor[p]=0;
            tick=0;
            while(writes<NSECT && tick<64*NSECT) begin
                @(negedge clk); in_v=0; req_v=0;
                for(p=0;p<NPC;p=p+1) if(cursor[p]<4*17) begin
                    sec=(p+32*(cursor[p]/17))*17+(cursor[p]%17);
                    in_v[p]=1;
                    in_tag[p*13+:13]=13'(sec/4);
                    in_beat[p*4+:4]=4'(sec%4);
                    in_data[p*256+:256]=sector_data(sec);
                end
                @(posedge clk); takes=in_v & in_rdy;
                #2;
                for(p=0;p<NPC;p=p+1) begin
                    if(takes[p]) cursor[p]=cursor[p]+1;
                    else if(in_v[p]) stalls=stalls+1;
                end
                tick=tick+1;
            end
            @(negedge clk); in_v=0; req_v=0;
            repeat(MARGIN) @(negedge clk);
            if(writes!=NSECT || !all_rows || stalls<100)
                $fatal(1,"conflict fill failed writes=%0d all=%b stalls=%0d",writes,all_rows,stalls);
        end
    endtask
    task automatic read_one(input integer user_id,input integer first,input integer mask);
        begin
            @(negedge clk); req_v=1;
            req_user=10'(user_id); req_first_row=21'(first); req_mask=4'(mask);
        end
    endtask
    task automatic drain_reads;
        begin @(negedge clk); req_v=0; repeat(4+RD+MARGIN) @(negedge clk); end
    endtask

    integer i;
    initial begin
        if(!$value$plusargs("rows=%s",rows_path)) $fatal(1,"released rows required");
        $readmemh(rows_path,golden);
        repeat(3) @(negedge clk); rst_n=1;
        open_job(18,0); fill_window;
        for(i=0;i<128;i=i+1) read_one(18,i,(1<<(i%4+1))-1);
        read_one(19,31,15); read_one(18,10,0); read_one(18,10,2);
        read_one(18,10,5); read_one(18,10,10); read_one(18,1048575,15);
        drain_reads;
        // Cancel a valid pending read with an asynchronous reset between edges.
        read_one(18,76,15);
        @(negedge clk); rst_n=0; req_v=0;
        repeat(2) @(negedge clk); rst_n=1;
        open_job(52,97); fill_window;
        for(i=0;i<128;i=i+1) read_one(52,97+i,(1<<(i%4+1))-1);
        read_one(52,95,15); read_one(52,223,15); read_one(18,125,15);
        drain_reads;
        // Original request wins its preedge context; later owner cannot rewrite
        // the accepted witnesses, while a new owner cannot reuse old landings.
        read_one(52,125,15);
        open_job(77,97); drain_reads;
        read_one(77,125,15); drain_reads;
        open_job(91,0); fill_window_conflict;
        for(i=0;i<128;i=i+1) read_one(91,i,15);
        drain_reads;
        if(checked<260 || valid_lanes<500 || denied<10 || completion_races!=2)
            $fatal(1,"coverage absent reads=%0d lanes=%0d denied=%0d races=%0d",
                checked,valid_lanes,denied,completion_races);
        $display("PASS MARGIN=%0d NPC32 full128 stage golden reads=%0d lanes=%0d denied=%0d completion_races=%0d conflict_stalls=%0d effective-edge reset/owner-snapshot/masked-unknown",MARGIN,checked,valid_lanes,denied,completion_races,stalls);
        $finish;
    end
endmodule
