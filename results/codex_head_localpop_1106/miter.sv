module miter(input wire a,b, output wire eq);
wire count_copy,addr_copy; wire shared_pop=a&&b;
ot_link_credit_rx_b64_pop u_count(.a(a),.b(b),.q(count_copy));
ot_link_credit_rx_b64_pop u_addr(.a(a),.b(b),.q(addr_copy));
assign eq=(count_copy==shared_pop)&&(addr_copy==shared_pop);
endmodule
