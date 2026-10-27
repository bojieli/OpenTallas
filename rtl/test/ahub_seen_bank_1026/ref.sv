module seen_ref(input clk,input[4:0]rn,input start_b,input[3:0]z_b,lm_b,done_slot,any_b,input[7:0]hh_b,input[15:0]k_b,output[511:0]q);
reg[127:0] zseen[0:3];reg[15:0]lany,lm_seen;reg[3:0]done_seen;
assign q={zseen[3],zseen[2],zseen[1],zseen[0]};
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin lany<=0;lm_seen<=0;done_seen<=0;zseen[0]<=0;zseen[1]<=0;end
        else if(start_b)begin lany<=0;lm_seen<=0;done_seen<=0;zseen[0]<=0;zseen[1]<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)begin
                if(lm_b[a])begin lany[4*a+hh_b[2*a+:2]]<=any_b[a];lm_seen[4*a+hh_b[2*a+:2]]<=1;end
                if(done_slot[a])done_seen[a]<=1;
                if(z_b[a] && !hh_b[2*a+1])zseen[hh_b[2*a+:2]][{1'b0,k_b[4*a+:4],2'(a)}]<=1;
            end
        end
    always @(posedge clk or negedge rn[4])
        if(!rn[4])begin zseen[2]<=0;zseen[3]<=0;end
        else if(start_b)begin zseen[2]<=0;zseen[3]<=0;end
        else for(integer a=0;a<4;a=a+1)if(z_b[a] && hh_b[2*a+1])zseen[hh_b[2*a+:2]][{1'b0,k_b[4*a+:4],2'(a)}]<=1;
endmodule
