module seen_dut(input clk,input[4:0]rn,input start_b,input[3:0]z_b,lm_b,done_slot,any_b,input[7:0]hh_b,input[15:0]k_b,output[511:0]q);
reg[127:0] zseen[0:3];reg[15:0]lany,lm_seen;reg[3:0]done_seen;
assign q={zseen[3],zseen[2],zseen[1],zseen[0]};
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin lany<=0;lm_seen<=0;done_seen<=0;end
        else if(start_b)begin lany<=0;lm_seen<=0;done_seen<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)begin
                if(lm_b[a])begin lany[4*a+hh_b[2*a+:2]]<=any_b[a];lm_seen[4*a+hh_b[2*a+:2]]<=1;end
                if(done_slot[a])done_seen[a]<=1;
            end
        end
    // Each static bank has exactly one procedural driver. The prior two dynamic array writes were
    // mutually exclusive by hh_b[1], but slang retained a second self-held FF for the other half.
    for (genvar bank = 0; bank < 4; bank = bank + 1) begin : g_zseen_bank
        wire bank_rst_n = rn[(bank < 2) ? 1 : 4];
        always @(posedge clk or negedge bank_rst_n)
            if (!bank_rst_n) zseen[bank] <= 0;
            else if (start_b) zseen[bank] <= 0;
            else for (integer a = 0; a < 4; a = a + 1)
                if (z_b[a] && hh_b[2*a +: 2] == 2'(bank))
                    zseen[bank][{1'b0, k_b[4*a +: 4], 2'(a)}] <= 1;
    end
endmodule
