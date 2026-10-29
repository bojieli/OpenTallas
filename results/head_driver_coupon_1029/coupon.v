module head_driver_coupon(input a,output inv_y,output buf_y);
INVx1_ASAP7_75t_R inv(.A(a),.Y(inv_y));
BUFx8_ASAP7_75t_R buf8(.A(a),.Y(buf_y));
endmodule
