// Exact combinational glue from ot_hgi_qdq_host_split_r3. Zero added edges.
module hbfd_qdq_split_or(input wire A,B,output wire Y);
    assign Y=A|B;
endmodule
module hbfd_qdq_split_and(input wire A,B,output wire Y);
    assign Y=A&&B;
endmodule
