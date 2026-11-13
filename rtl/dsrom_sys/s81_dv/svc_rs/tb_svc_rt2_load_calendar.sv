`timescale 1ns/1ps
// Independent native H8 RT2 transport vehicle. Both programmes are fixed before
// the first active edge: twelve packets, no request/ready-driven issue.
module tb_svc_rt2_load_calendar;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg rst_n = 0;
    wire load_slot;
    ot_s81_svc_rt2_load_calendar u_calendar(.clk(clk), .rst_n(rst_n), .load_slot(load_slot));

    reg [1:0] ld_v = 0, ld_mode = 0, ld_w2v = 0;
    reg [2:0] ld_bank [0:1];
    reg [7:0] ld_grp [0:1];
    reg [1023:0] ld_w [0:1];
    wire [1:0] out_v, out_mode, out_w2v, fault;
    wire [2:0] out_bank [0:1];
    wire [7:0] out_grp [0:1];
    wire [1023:0] out_w [0:1];
    for(genvar g=0; g<2; g=g+1) begin:g_expander
        ot_s81c_h8_rt2_load u_expand(
            .clk(clk), .rst_n(rst_n), .ld_v(ld_v[g]), .ld_mode(ld_mode[g]),
            .ld_bank(ld_bank[g]), .ld_grp(ld_grp[g]), .ld_w(ld_w[g]), .ld_w2v(ld_w2v[g]),
            .out_v(out_v[g]), .out_mode(out_mode[g]), .out_bank(out_bank[g]),
            .out_grp(out_grp[g]), .out_w(out_w[g]), .out_w2v(out_w2v[g]), .fault(fault[g]));
    end

    // The source value depends on packet/row/head, not DUT state or timing.
    function automatic [15:0] q_value(input integer packet, input integer word_index);
        q_value = 16'(4096 + packet*64 + word_index);
    endfunction
    function automatic [15:0] p_value(input integer row_index, input integer head);
        p_value = 16'(16384 + row_index*8 + head);
    endfunction
    function automatic [1023:0] packet_word(input integer packet);
        reg [1023:0] w;
        integer r,h,j;
        begin
            w = 0;
            if(packet<8) begin
                for(j=0;j<64;j=j+1) w[16*j+:16]=q_value(packet,j);
            end else begin
                for(r=0;r<8;r=r+1) for(h=0;h<8;h=h+1)
                    w[16*(8*r+h)+:16]=p_value((packet-8)*8+r,h);
            end
            packet_word=w;
        end
    endfunction

    reg [15:0] q_matrix [0:1][0:7][0:63];
    reg [15:0] p_matrix [0:1][0:31][0:7];
    integer offered [0:1];
    integer q_outputs [0:1];
    integer p_outputs [0:1];
    integer metadata_errors [0:1];
    integer reserved_inputs [0:1];
    integer cycle=0, last_accept=-2, ii_errors=0, phase_errors=0;
    integer requested_origin=0, accepted_origin=0;
    integer timing_errors=0, first_output=-1, last_output=-1, first_p_output=-1, last_p_output=-1;
    integer i,j,k,r,h,n,base;

    // Scoreboard samples the transport values on the receiving clock edge.
    // P output grp is an OLD RT2 index: 2*grp gives the first of four rows.
    task automatic observe(input integer which);
        integer rr,hh,ww,row0,relative_cycle;
        begin
            relative_cycle=cycle-accepted_origin;
            if(which==0) begin
                if(out_v[which] !== (((relative_cycle>=0)&&(relative_cycle<=14)&&(relative_cycle%2==0)) || (relative_cycle>=16&&relative_cycle<=23)))
                    timing_errors=timing_errors+1;
                if(out_v[which]) begin
                    if(first_output<0) first_output=cycle;
                    last_output=cycle;
                    if(out_mode[which]) begin
                        if(first_p_output<0) first_p_output=cycle;
                        last_p_output=cycle;
                        if(relative_cycle<16 || relative_cycle>23 || out_grp[which] != 8'(2*(relative_cycle-16))) timing_errors=timing_errors+1;
                    end else if(relative_cycle<0 || relative_cycle>14 || relative_cycle%2!=0 || out_grp[which] != 8'(relative_cycle/2)) timing_errors=timing_errors+1;
                end
            end
            if(out_v[which]) begin
                if(!out_mode[which]) begin
                    q_outputs[which]=q_outputs[which]+1;
                    if(out_grp[which]>=8 || out_bank[which] != 3'(out_grp[which]%5))
                        metadata_errors[which]=metadata_errors[which]+1;
                    if(out_grp[which]<8)
                        for(ww=0;ww<64;ww=ww+1)
                            q_matrix[which][out_grp[which]][ww]=out_w[which][16*ww+:16];
                end else begin
                    p_outputs[which]=p_outputs[which]+1;
                    row0=2*out_grp[which];
                    if(row0<0 || row0+3>=32 || out_bank[which] != 3'd3 || !out_w2v[which])
                        metadata_errors[which]=metadata_errors[which]+1;
                    if(row0>=0 && row0+3<32)
                        for(rr=0;rr<4;rr=rr+1) for(hh=0;hh<8;hh=hh+1)
                            p_matrix[which][row0+rr][hh]=out_w[which][16*(16*rr+hh)+:16];
                    for(rr=0;rr<4;rr=rr+1) for(hh=8;hh<16;hh=hh+1)
                        if(out_w[which][16*(16*rr+hh)+:16] !== 16'd0)
                            metadata_errors[which]=metadata_errors[which]+1;
                end
            end
        end
    endtask

    always @(posedge clk) if(rst_n) begin
        if(load_slot !== (cycle%2==0)) phase_errors=phase_errors+1;
        for(integer m=0;m<2;m=m+1) begin
            if(ld_v[m]) begin
                offered[m]=offered[m]+1;
                if(!load_slot) reserved_inputs[m]=reserved_inputs[m]+1;
                if(m==0) begin
                    if(cycle-last_accept!=2) ii_errors=ii_errors+1;
                    last_accept=cycle;
                    $display("RT2_ACCEPT cycle=%0d packet=%0d slot=%0d",cycle,offered[m]-1,load_slot);
                end
            end
            observe(m);
        end
        cycle=cycle+1;
    end

    integer q_errors [0:1];
    integer p_errors [0:1];
    integer checked [0:1];
    initial begin
        void'($value$plusargs("requested_origin=%d",requested_origin));
        if(requested_origin<0) $fatal(1,"negative programme origin");
        // Compile the programme once, before any active edge. Never wait for
        // ready or inspect calendar state to decide a later issue cycle.
        accepted_origin=requested_origin+(requested_origin%2);
        last_accept=accepted_origin-2;
        $display("RT2_ROUND request=%0d accepted_origin=%0d phase=0 II=2",requested_origin,accepted_origin);
        for(i=0;i<2;i=i+1) begin
            offered[i]=0;q_outputs[i]=0;p_outputs[i]=0;
            metadata_errors[i]=0;reserved_inputs[i]=0;
            q_errors[i]=0;p_errors[i]=0;checked[i]=0;
            ld_bank[i]=0;ld_grp[i]=0;ld_w[i]=0;
            for(j=0;j<8;j=j+1) for(k=0;k<64;k=k+1) q_matrix[i][j][k]=16'hdead;
            for(j=0;j<32;j=j+1) for(k=0;k<8;k=k+1) p_matrix[i][j][k]=16'hdead;
        end
        repeat(4) @(negedge clk);
        rst_n=1;
        // Case0: fixed phase0 issue at cycles0,2,...22. Case1: the SAME packets
        // at cycles0..11, deliberately ignoring the reserved replay phase.
        for(i=0;i<40;i=i+1) begin
            for(j=0;j<2;j=j+1) begin
                n=(j==0)?((i-accepted_origin)/2):i;
                ld_v[j]=(n>=0)&&(n<12)&&((j==1)||((i>=accepted_origin)&&((i-accepted_origin)%2==0)));
                ld_mode[j]=(n>=8);
                ld_w2v[j]=1;
                ld_grp[j]=(n<8)?8'(n):8'((n-8)*2);
                ld_bank[j]=(n<8)?3'(n%5):3'd3;
                ld_w[j]=(n>=0&&n<12)?packet_word(n):1024'd0;
            end
            @(negedge clk);
        end
        ld_v=0;
        for(i=0;i<2;i=i+1) begin
            for(j=0;j<8;j=j+1) for(k=0;k<64;k=k+1) begin
                checked[i]=checked[i]+1;
                if(q_matrix[i][j][k] !== q_value(j,k)) q_errors[i]=q_errors[i]+1;
            end
            for(r=0;r<32;r=r+1) for(h=0;h<8;h=h+1) begin
                checked[i]=checked[i]+1;
                if(p_matrix[i][r][h] !== p_value(r,h)) p_errors[i]=p_errors[i]+1;
            end
        end
        $display("RT2_CALENDAR nominal offered=%0d Q_outputs=%0d P_outputs=%0d checked_words=%0d Q_errors=%0d P_errors=%0d metadata_errors=%0d af=%0d II=2 ii_errors=%0d reserved_inputs=%0d phase_errors=%0d active_cycles=%0d",
            offered[0],q_outputs[0],p_outputs[0],checked[0],q_errors[0],p_errors[0],metadata_errors[0],fault[0],ii_errors,reserved_inputs[0],phase_errors,cycle);
        $display("RT2_CALENDAR malformed offered=%0d Q_outputs=%0d P_outputs=%0d checked_words=%0d Q_errors=%0d P_errors=%0d metadata_errors=%0d af=%0d reserved_inputs=%0d",
            offered[1],q_outputs[1],p_outputs[1],checked[1],q_errors[1],p_errors[1],metadata_errors[1],fault[1],reserved_inputs[1]);
        $display("RT2_CALENDAR timing first_output=%0d last_output=%0d first_P=%0d last_P=%0d errors=%0d",first_output,last_output,first_p_output,last_p_output,timing_errors);
        if(offered[0]!=12 || q_outputs[0]!=8 || p_outputs[0]!=8 || checked[0]!=768 ||
           q_errors[0]!=0 || p_errors[0]!=0 || metadata_errors[0]!=0 || fault[0]!==1'b0 ||
           ii_errors!=0 || reserved_inputs[0]!=0 || phase_errors!=0 || timing_errors!=0)
            $fatal(1,"RT2_CALENDAR nominal FAIL");
        if(offered[1]!=12 || q_outputs[1]!=8 || p_outputs[1]>=8 || q_errors[1]!=0 ||
           p_errors[1]==0 || fault[1]!==1'b1)
            $fatal(1,"RT2_CALENDAR malformed cadence was not caught by loss plus fault");
        $display("RT2_CALENDAR PASS: static phase0 programme lossless; malformed cadence loses P words and raises af");
        $finish;
    end
endmodule
