module mesh2(input clk, output o0,o1,o2,o3);
wire ck_mesh;
BUFx24_ASAP7_75t_R drv0(.A(clk),.Y(ck_mesh));
BUFx24_ASAP7_75t_R stub0(.A(ck_mesh),.Y(o0));
BUFx24_ASAP7_75t_R drv1(.A(clk),.Y(ck_mesh));
BUFx24_ASAP7_75t_R stub1(.A(ck_mesh),.Y(o1));
BUFx24_ASAP7_75t_R drv2(.A(clk),.Y(ck_mesh));
BUFx24_ASAP7_75t_R stub2(.A(ck_mesh),.Y(o2));
BUFx24_ASAP7_75t_R drv3(.A(clk),.Y(ck_mesh));
BUFx24_ASAP7_75t_R stub3(.A(ck_mesh),.Y(o3));
endmodule
