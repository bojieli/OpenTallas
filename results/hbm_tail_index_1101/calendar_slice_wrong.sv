module calendar #(parameter PREDECODE_INDEX=0)(input clk,rst_n,launch,sink_capture,output[4:0] idx,output[8:0] age_out,output active_out);
    localparam integer P1=1,P2=28,MAX=55,P3=56,P4=75,P5=148,P6=159,P7=186,EREADY=197;
reg active;reg[8:0]age;reg fault,result_v;
wire mo=0,ao=0,eo=0,do_=0,ef=0,df=0,sink_fault=0,sv=1,sf=0;
wire[1:0]me=0,ae=0;
    wire p1=active&&age>=P1&&age<P1+24;
    wire p2=active&&age>=P2&&age<P2+24;
    wire p3=active&&age>=P3&&age<P3+16;
    wire p4=active&&age>=P4&&age<P4+24;
    wire p5=active&&age>=P5&&age<P5+8;
    wire p6=active&&age>=P6&&age<P6+8;
    wire p7=active&&age>=P7&&age<P7+8;
    wire [4:0] i_comb=p1?5'(age-P1):p2?5'(age-P2):p3?5'(age-P3+8):
        p4?5'(age-P4):p5?5'(age-P5):p6?5'(age-P6):5'(age-P7);
    wire [4:0] i;
    generate if (PREDECODE_INDEX != 0) begin:g_predecode_index
        // Match the control block's exact nonblocking priority, including
        // launch+capture and held/inactive ages. The invalid-cycle address
        // is preserved too, so all unchanged arithmetic sees identical bits.
        wire [8:0] age_next=launch?9'd1:
            (active&&age<EREADY+1)?age+9'd1:age;
        wire active_next=sink_capture?1'b0:launch?1'b1:active;
        function automatic [4:0] address(input [8:0] a,input act);
            if(act&&a>=P1&&a<P1+24)address=5'(a-P1);
            else if(act&&a>=P2&&a<P2+24)address=5'(a-P2);
            else if(act&&a>=P3&&a<P3+16)address=5'(a-P3+8);
            else if(act&&a>=P4&&a<P4+24)address=5'(a-P4);
            else if(act&&a>=P5&&a<P5+8)address=5'(a-P5);
            else if(act&&a>=P6&&a<P6+8)address=5'(a-P6);
            else address=5'(a-P7);
        endfunction
        reg [4:0] i_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)i_q<=5'(0-P7);
            else i_q<=address(age_next+9'd1,active_next);
        assign i=i_q;
    end else begin:g_comb_index
        assign i=i_comb;
    end endgenerate
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;age<=0;fault<=0;result_v<=0;end
        else begin
            result_v<=sink_capture;
            if(active&&age<EREADY+1)age<=age+1'b1;
            if(launch)begin
                age<=1;active<=1;
                if(active)fault<=1;
            end
            if((mo&&(|me))||(ao&&(|ae))||(eo&&ef)||(do_&&df)||sink_fault)fault<=1;
            if(sink_capture)begin
                // sv remains high for a complete sink-clock period. Compiler
                // picks the reserved core edge within that proven interval.
                if(!active||age<EREADY||!sv||sf)fault<=1;
                active<=0;
            end
        end
    end
assign idx=i;assign age_out=age;assign active_out=active;
endmodule
