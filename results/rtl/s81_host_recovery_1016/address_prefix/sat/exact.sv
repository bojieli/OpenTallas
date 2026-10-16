module proof(input[31:0]a,b,input[4:0]sec,input[2:0]ph,output ok);
    function automatic [31:0] host_addr_add32_prefix;
        input [31:0] a,b;
        reg [39:0] q;
        reg [7:0] p0,g0,p1,g1,p2,g2,g3;
        integer i;
        begin
            for(i=0;i<8;i=i+1)begin
                q[5*i+:5]={1'b0,a[4*i+:4]}+{1'b0,b[4*i+:4]};
                p0[i]=&(a[4*i+:4]^b[4*i+:4]);g0[i]=q[5*i+4];
            end
            for(i=0;i<8;i=i+1)begin
                if(i>=1)begin p1[i]=p0[i]&p0[i-1];g1[i]=g0[i]|(p0[i]&g0[i-1]);end
                else begin p1[i]=p0[i];g1[i]=g0[i];end
            end
            for(i=0;i<8;i=i+1)begin
                if(i>=2)begin p2[i]=p1[i]&p1[i-2];g2[i]=g1[i]|(p1[i]&g1[i-2]);end
                else begin p2[i]=p1[i];g2[i]=g1[i];end
            end
            for(i=0;i<8;i=i+1)begin
                if(i>=4)g3[i]=g2[i]|(p2[i]&g2[i-4]);else g3[i]=g2[i];
            end
            host_addr_add32_prefix[3:0]=q[3:0];
            for(i=1;i<8;i=i+1)host_addr_add32_prefix[4*i+:4]=q[5*i+:4]+{3'd0,g3[i-1]};
        end
    endfunction
wire[31:0]fast=host_addr_add32_prefix(a,b);
wire[31:0]refsum=a+b;
wire[30:0]ref31r=a+sec,ref31k=a+ph,ref31s=a+(ph==4?1:0);
    wire [31-1:0] selected31r=(31<=32)?host_addr_add32_prefix(a,{27'd0,sec}):(a+sec);
    wire [31-1:0] selected31k=(31<=32)?host_addr_add32_prefix(a,{29'd0,ph}):(a+ph);
    wire [31-1:0] selected31s=(31<=32)?host_addr_add32_prefix(a,ph==3'd4 ? 32'd1 : 32'd0):(a+(ph==3'd4 ? 1:0));
    wire [31-1:0] default31r=a+sec;
    wire [31-1:0] default31k=a+ph;
    wire [31-1:0] default31s=a+(ph==3'd4 ? 1:0);
wire[31:0]ref32r=a+sec,ref32k=a+ph,ref32s=a+(ph==4?1:0);
    wire [32-1:0] selected32r=(32<=32)?host_addr_add32_prefix(a,{27'd0,sec}):(a+sec);
    wire [32-1:0] selected32k=(32<=32)?host_addr_add32_prefix(a,{29'd0,ph}):(a+ph);
    wire [32-1:0] selected32s=(32<=32)?host_addr_add32_prefix(a,ph==3'd4 ? 32'd1 : 32'd0):(a+(ph==3'd4 ? 1:0));
    wire [32-1:0] default32r=a+sec;
    wire [32-1:0] default32k=a+ph;
    wire [32-1:0] default32s=a+(ph==3'd4 ? 1:0);
wire[32:0]ref33r=a+sec,ref33k=a+ph,ref33s=a+(ph==4?1:0);
    wire [33-1:0] selected33r=(33<=32)?host_addr_add32_prefix(a,{27'd0,sec}):(a+sec);
    wire [33-1:0] selected33k=(33<=32)?host_addr_add32_prefix(a,{29'd0,ph}):(a+ph);
    wire [33-1:0] selected33s=(33<=32)?host_addr_add32_prefix(a,ph==3'd4 ? 32'd1 : 32'd0):(a+(ph==3'd4 ? 1:0));
    wire [33-1:0] default33r=a+sec;
    wire [33-1:0] default33k=a+ph;
    wire [33-1:0] default33s=a+(ph==3'd4 ? 1:0);
wire[63:0]ref64r=a+sec,ref64k=a+ph,ref64s=a+(ph==4?1:0);
    wire [64-1:0] selected64r=(64<=32)?host_addr_add32_prefix(a,{27'd0,sec}):(a+sec);
    wire [64-1:0] selected64k=(64<=32)?host_addr_add32_prefix(a,{29'd0,ph}):(a+ph);
    wire [64-1:0] selected64s=(64<=32)?host_addr_add32_prefix(a,ph==3'd4 ? 32'd1 : 32'd0):(a+(ph==3'd4 ? 1:0));
    wire [64-1:0] default64r=a+sec;
    wire [64-1:0] default64k=a+ph;
    wire [64-1:0] default64s=a+(ph==3'd4 ? 1:0);
assign ok=(fast==refsum)&&({selected31r,selected31k,selected31s}=={ref31r,ref31k,ref31s})&&({default31r,default31k,default31s}=={ref31r,ref31k,ref31s})&&({selected32r,selected32k,selected32s}=={ref32r,ref32k,ref32s})&&({default32r,default32k,default32s}=={ref32r,ref32k,ref32s})&&({selected33r,selected33k,selected33s}=={ref33r,ref33k,ref33s})&&({default33r,default33k,default33s}=={ref33r,ref33k,ref33s})&&({selected64r,selected64k,selected64s}=={ref64r,ref64k,ref64s})&&({default64r,default64k,default64s}=={ref64r,ref64k,ref64s});
endmodule
