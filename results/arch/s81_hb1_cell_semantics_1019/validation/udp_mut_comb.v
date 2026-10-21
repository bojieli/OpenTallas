`timescale 1ns/1ps
module AND2x2_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	nand (Y, A, B);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
	endspecify
endmodule
module AND3x1_ASAP7_75t_R (Y, A, B, C);
	output Y;
	input A, B, C;

	// Function
	and (Y, A, B, C);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
	endspecify
endmodule
module AND4x1_ASAP7_75t_R (Y, A, B, C, D);
	output Y;
	input A, B, C, D;

	// Function
	and (Y, A, B, C, D);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
		(D => Y) = 0;
	endspecify
endmodule
module AND5x1_ASAP7_75t_R (Y, A, B, C, D, E);
	output Y;
	input A, B, C, D, E;

	// Function
	and (Y, A, B, C, D, E);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
		(D => Y) = 0;
		(E => Y) = 0;
	endspecify
endmodule
module AO21x1_ASAP7_75t_R (Y, A1, A2, B);
	output Y;
	input A1, A2, B;

	// Function
	wire int_fwire_0;

	and (int_fwire_0, A1, A2);
	or (Y, int_fwire_0, B);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & ~A2))
			(B => Y) = 0;
		if ((~A1 & A2))
			(B => Y) = 0;
		if ((~A1 & ~A2))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
	endspecify
endmodule
module AO221x1_ASAP7_75t_R (Y, A1, A2, B1, B2, C);
	output Y;
	input A1, A2, B1, B2, C;

	// Function
	wire int_fwire_0, int_fwire_1;

	and (int_fwire_0, B1, B2);
	and (int_fwire_1, A1, A2);
	or (Y, int_fwire_1, int_fwire_0, C);

	// Timing
	specify
		if ((A2 & B1 & ~B2 & ~C))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2 & ~C))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2 & ~C))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((A1 & B1 & ~B2 & ~C))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2 & ~C))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2 & ~C))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & ~A2 & B2 & ~C))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2 & ~C))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2 & ~C))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~C))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~C))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~C))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((A1 & ~A2 & ~B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((~A1 & A2 & ~B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & ~A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((~A1 & ~A2 & ~B1 & ~B2))
			(C => Y) = 0;
		ifnone (C => Y) = 0;
	endspecify
endmodule
module AO222x2_ASAP7_75t_R (Y, A1, A2, B1, B2, C1, C2);
	output Y;
	input A1, A2, B1, B2, C1, C2;

	// Function
	wire int_fwire_0, int_fwire_1, int_fwire_2;

	and (int_fwire_0, C1, C2);
	and (int_fwire_1, B1, B2);
	and (int_fwire_2, A1, A2);
	or (Y, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((A2 & B1 & ~B2 & C1 & ~C2))
			(A1 => Y) = 0;
		if ((A2 & B1 & ~B2 & ~C1 & C2))
			(A1 => Y) = 0;
		if ((A2 & B1 & ~B2 & ~C1 & ~C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2 & C1 & ~C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2 & ~C1 & C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2 & ~C1 & ~C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2 & C1 & ~C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2 & ~C1 & C2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2 & ~C1 & ~C2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((A1 & B1 & ~B2 & C1 & ~C2))
			(A2 => Y) = 0;
		if ((A1 & B1 & ~B2 & ~C1 & C2))
			(A2 => Y) = 0;
		if ((A1 & B1 & ~B2 & ~C1 & ~C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2 & C1 & ~C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2 & ~C1 & C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2 & ~C1 & ~C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2 & C1 & ~C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2 & ~C1 & C2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2 & ~C1 & ~C2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & ~A2 & B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & B2 & ~C1 & C2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & B2 & ~C1 & ~C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2 & ~C1 & C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2 & ~C1 & ~C2))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2 & ~C1 & C2))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2 & ~C1 & ~C2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & ~A2 & B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~C1 & C2))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~C1 & ~C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~C1 & C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~C1 & ~C2))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~C1 & C2))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~C1 & ~C2))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2 & C2))
			(C1 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2 & C2))
			(C1 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & ~B2 & C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2 & C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2 & C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & ~B1 & ~B2 & C2) | (~A1 & ~A2 & ~B1 & B2 & C2))
			(C1 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~B2 & C2))
			(C1 => Y) = 0;
		if ((~A1 & ~A2 & ~B1 & ~B2 & C2))
			(C1 => Y) = 0;
		ifnone (C1 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2 & C1))
			(C2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2 & C1))
			(C2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & ~B2 & C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2 & C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2 & C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & ~B2 & C1) | (~A1 & ~A2 & ~B1 & B2 & C1))
			(C2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~B2 & C1))
			(C2 => Y) = 0;
		if ((~A1 & ~A2 & ~B1 & ~B2 & C1))
			(C2 => Y) = 0;
		ifnone (C2 => Y) = 0;
	endspecify
endmodule
module AO22x1_ASAP7_75t_R (Y, A1, A2, B1, B2);
	output Y;
	input A1, A2, B1, B2;

	// Function
	wire int_fwire_0, int_fwire_1;

	and (int_fwire_0, B1, B2);
	and (int_fwire_1, A1, A2);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((A2 & B1 & ~B2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((A1 & B1 & ~B2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & ~A2 & B2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & ~A2 & B1))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
	endspecify
endmodule
module AO31x2_ASAP7_75t_R (Y, A1, A2, A3, B);
	output Y;
	input A1, A2, A3, B;

	// Function
	wire int_fwire_0;

	and (int_fwire_0, A1, A2, A3);
	or (Y, int_fwire_0, B);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		(A3 => Y) = 0;
		if ((A1 & A2 & ~A3))
			(B => Y) = 0;
		if ((A1 & ~A2 & A3))
			(B => Y) = 0;
		if ((A1 & ~A2 & ~A3))
			(B => Y) = 0;
		if ((~A1 & A2 & A3))
			(B => Y) = 0;
		if ((~A1 & A2 & ~A3) | (~A1 & ~A2 & A3))
			(B => Y) = 0;
		if ((~A1 & ~A2 & ~A3))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
	endspecify
endmodule
module AO32x1_ASAP7_75t_R (Y, A1, A2, A3, B1, B2);
	output Y;
	input A1, A2, A3, B1, B2;

	// Function
	wire int_fwire_0, int_fwire_1;

	and (int_fwire_0, B1, B2);
	and (int_fwire_1, A1, A2, A3);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((A2 & A3 & B1 & ~B2))
			(A1 => Y) = 0;
		if ((A2 & A3 & ~B1 & B2))
			(A1 => Y) = 0;
		if ((A2 & A3 & ~B1 & ~B2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((A1 & A3 & B1 & ~B2))
			(A2 => Y) = 0;
		if ((A1 & A3 & ~B1 & B2))
			(A2 => Y) = 0;
		if ((A1 & A3 & ~B1 & ~B2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & A2 & B1 & ~B2))
			(A3 => Y) = 0;
		if ((A1 & A2 & ~B1 & B2))
			(A3 => Y) = 0;
		if ((A1 & A2 & ~B1 & ~B2))
			(A3 => Y) = 0;
		ifnone (A3 => Y) = 0;
		if ((A1 & A2 & ~A3 & B2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & A3 & B2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~A3 & B2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & A3 & B2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~A3 & B2) | (~A1 & ~A2 & A3 & B2))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & ~A3 & B2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & A2 & ~A3 & B1))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & A3 & B1))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~A3 & B1))
			(B2 => Y) = 0;
		if ((~A1 & A2 & A3 & B1))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~A3 & B1) | (~A1 & ~A2 & A3 & B1))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & ~A3 & B1))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
	endspecify
endmodule
module AOI211x1_ASAP7_75t_R (Y, A1, A2, B, C);
	output Y;
	input A1, A2, B, C;

	// Function
	wire A1__bar, A2__bar, B__bar;
	wire C__bar, int_fwire_0, int_fwire_1;

	not (C__bar, C);
	not (B__bar, B);
	not (A2__bar, A2);
	and (int_fwire_0, A2__bar, B__bar, C__bar);
	not (A1__bar, A1);
	and (int_fwire_1, A1__bar, B__bar, C__bar);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & ~A2 & ~C))
			(B => Y) = 0;
		if ((~A1 & A2 & ~C))
			(B => Y) = 0;
		if ((~A1 & ~A2 & ~C))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
		if ((A1 & ~A2 & ~B))
			(C => Y) = 0;
		if ((~A1 & A2 & ~B))
			(C => Y) = 0;
		if ((~A1 & ~A2 & ~B))
			(C => Y) = 0;
		ifnone (C => Y) = 0;
	endspecify
endmodule
module AOI21x1_ASAP7_75t_R (Y, A1, A2, B);
	output Y;
	input A1, A2, B;

	// Function
	wire A1__bar, A2__bar, B__bar;
	wire int_fwire_0, int_fwire_1;

	not (B__bar, B);
	not (A2__bar, A2);
	and (int_fwire_0, A2__bar, B__bar);
	not (A1__bar, A1);
	and (int_fwire_1, A1__bar, B__bar);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & ~A2))
			(B => Y) = 0;
		if ((~A1 & A2))
			(B => Y) = 0;
		if ((~A1 & ~A2))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
	endspecify
endmodule
module AOI221x1_ASAP7_75t_R (Y, A1, A2, B1, B2, C);
	output Y;
	input A1, A2, B1, B2, C;

	// Function
	wire A1__bar, A2__bar, B1__bar;
	wire B2__bar, C__bar, int_fwire_0;
	wire int_fwire_1, int_fwire_2, int_fwire_3;

	not (C__bar, C);
	not (B2__bar, B2);
	not (A2__bar, A2);
	and (int_fwire_0, A2__bar, B2__bar, C__bar);
	not (B1__bar, B1);
	and (int_fwire_1, A2__bar, B1__bar, C__bar);
	not (A1__bar, A1);
	and (int_fwire_2, A1__bar, B2__bar, C__bar);
	and (int_fwire_3, A1__bar, B1__bar, C__bar);
	or (Y, int_fwire_3, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((A2 & B1 & ~B2 & ~C))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & B2 & ~C))
			(A1 => Y) = 0;
		if ((A2 & ~B1 & ~B2 & ~C))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((A1 & B1 & ~B2 & ~C))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & B2 & ~C))
			(A2 => Y) = 0;
		if ((A1 & ~B1 & ~B2 & ~C))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & ~A2 & B2 & ~C))
			(B1 => Y) = 0;
		if ((~A1 & A2 & B2 & ~C))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & B2 & ~C))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~C))
			(B2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~C))
			(B2 => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~C))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((A1 & ~A2 & ~B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((~A1 & A2 & ~B1 & ~B2) | (~A1 & ~A2 & ~B1 & B2))
			(C => Y) = 0;
		if ((~A1 & ~A2 & B1 & ~B2))
			(C => Y) = 0;
		if ((~A1 & ~A2 & ~B1 & ~B2))
			(C => Y) = 0;
		ifnone (C => Y) = 0;
	endspecify
endmodule
module BUFx12f_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx2_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx3_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx4f_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx5_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx6f_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module BUFx8_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	buf (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module INVx1_ASAP7_75t_R (Y, A);
	output Y;
	input A;

	// Function
	not (Y, A);

	// Timing
	specify
		(A => Y) = 0;
	endspecify
endmodule
module MAJx2_ASAP7_75t_R (Y, A, B, C);
	output Y;
	input A, B, C;

	// Function
	wire int_fwire_0, int_fwire_1, int_fwire_2;

	and (int_fwire_0, B, C);
	and (int_fwire_1, A, C);
	and (int_fwire_2, A, B);
	or (Y, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((B & ~C))
			(A => Y) = 0;
		if ((~B & C))
			(A => Y) = 0;
		ifnone (A => Y) = 0;
		if ((A & ~C))
			(B => Y) = 0;
		if ((~A & C))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
		if ((A & ~B))
			(C => Y) = 0;
		if ((~A & B))
			(C => Y) = 0;
		ifnone (C => Y) = 0;
	endspecify
endmodule
module NAND2x1_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	wire A__bar, B__bar;

	not (B__bar, B);
	not (A__bar, A);
	or (Y, A__bar, B__bar);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
	endspecify
endmodule
module NAND3x1_ASAP7_75t_R (Y, A, B, C);
	output Y;
	input A, B, C;

	// Function
	wire A__bar, B__bar, C__bar;

	not (C__bar, C);
	not (B__bar, B);
	not (A__bar, A);
	or (Y, A__bar, B__bar, C__bar);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
	endspecify
endmodule
module NOR2x1_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	wire A__bar, B__bar;

	not (B__bar, B);
	not (A__bar, A);
	and (Y, A__bar, B__bar);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
	endspecify
endmodule
module OA211x2_ASAP7_75t_R (Y, A1, A2, B, C);
	output Y;
	input A1, A2, B, C;

	// Function
	wire int_fwire_0, int_fwire_1;

	and (int_fwire_0, A2, B, C);
	and (int_fwire_1, A1, B, C);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & A2 & C))
			(B => Y) = 0;
		if ((A1 & ~A2 & C))
			(B => Y) = 0;
		if ((~A1 & A2 & C))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
		if ((A1 & A2 & B))
			(C => Y) = 0;
		if ((A1 & ~A2 & B))
			(C => Y) = 0;
		if ((~A1 & A2 & B))
			(C => Y) = 0;
		ifnone (C => Y) = 0;
	endspecify
endmodule
module OA21x2_ASAP7_75t_R (Y, A1, A2, B);
	output Y;
	input A1, A2, B;

	// Function
	wire int_fwire_0, int_fwire_1;

	and (int_fwire_0, A2, B);
	and (int_fwire_1, A1, B);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & A2))
			(B => Y) = 0;
		if ((A1 & ~A2))
			(B => Y) = 0;
		if ((~A1 & A2))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
	endspecify
endmodule
module OA222x2_ASAP7_75t_R (Y, A1, A2, B1, B2, C1, C2);
	output Y;
	input A1, A2, B1, B2, C1, C2;

	// Function
	wire int_fwire_0, int_fwire_1, int_fwire_2;
	wire int_fwire_3, int_fwire_4, int_fwire_5;
	wire int_fwire_6, int_fwire_7;

	and (int_fwire_0, A2, B2, C2);
	and (int_fwire_1, A2, B2, C1);
	and (int_fwire_2, A2, B1, C2);
	and (int_fwire_3, A2, B1, C1);
	and (int_fwire_4, A1, B2, C2);
	and (int_fwire_5, A1, B2, C1);
	and (int_fwire_6, A1, B1, C2);
	and (int_fwire_7, A1, B1, C1);
	or (Y, int_fwire_7, int_fwire_6, int_fwire_5, int_fwire_4, int_fwire_3, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((~A2 & B1 & B2 & C1 & C2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & B2 & C1 & ~C2) | (~A2 & B1 & ~B2 & C1 & C2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & B2 & ~C1 & C2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & ~B2 & C1 & ~C2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & ~B2 & ~C1 & C2))
			(A1 => Y) = 0;
		if ((~A2 & ~B1 & B2 & C1 & C2))
			(A1 => Y) = 0;
		if ((~A2 & ~B1 & B2 & C1 & ~C2))
			(A1 => Y) = 0;
		if ((~A2 & ~B1 & B2 & ~C1 & C2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((~A1 & B1 & B2 & C1 & C2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & B2 & C1 & ~C2) | (~A1 & B1 & ~B2 & C1 & C2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & B2 & ~C1 & C2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & ~B2 & C1 & ~C2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & ~B2 & ~C1 & C2))
			(A2 => Y) = 0;
		if ((~A1 & ~B1 & B2 & C1 & C2))
			(A2 => Y) = 0;
		if ((~A1 & ~B1 & B2 & C1 & ~C2))
			(A2 => Y) = 0;
		if ((~A1 & ~B1 & B2 & ~C1 & C2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & A2 & ~B2 & C1 & C2))
			(B1 => Y) = 0;
		if ((A1 & A2 & ~B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((A1 & A2 & ~B2 & ~C1 & C2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~B2 & C1 & C2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~B2 & ~C1 & C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~B2 & C1 & C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~B2 & C1 & ~C2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~B2 & ~C1 & C2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & A2 & ~B1 & C1 & C2))
			(B2 => Y) = 0;
		if ((A1 & A2 & ~B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((A1 & A2 & ~B1 & ~C1 & C2))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & C1 & C2))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & ~C1 & C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & C1 & C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & C1 & ~C2))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & ~C1 & C2))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
		if ((A1 & A2 & B1 & B2 & ~C2))
			(C1 => Y) = 0;
		if ((A1 & A2 & B1 & ~B2 & ~C2))
			(C1 => Y) = 0;
		if ((A1 & A2 & ~B1 & B2 & ~C2))
			(C1 => Y) = 0;
		if ((A1 & ~A2 & B1 & B2 & ~C2))
			(C1 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2 & ~C2))
			(C1 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2 & ~C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & B1 & B2 & ~C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2 & ~C2))
			(C1 => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2 & ~C2))
			(C1 => Y) = 0;
		ifnone (C1 => Y) = 0;
		if ((A1 & A2 & B1 & B2 & ~C1))
			(C2 => Y) = 0;
		if ((A1 & A2 & B1 & ~B2 & ~C1))
			(C2 => Y) = 0;
		if ((A1 & A2 & ~B1 & B2 & ~C1))
			(C2 => Y) = 0;
		if ((A1 & ~A2 & B1 & B2 & ~C1))
			(C2 => Y) = 0;
		if ((A1 & ~A2 & B1 & ~B2 & ~C1))
			(C2 => Y) = 0;
		if ((A1 & ~A2 & ~B1 & B2 & ~C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & B1 & B2 & ~C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & B1 & ~B2 & ~C1))
			(C2 => Y) = 0;
		if ((~A1 & A2 & ~B1 & B2 & ~C1))
			(C2 => Y) = 0;
		ifnone (C2 => Y) = 0;
	endspecify
endmodule
module OA22x2_ASAP7_75t_R (Y, A1, A2, B1, B2);
	output Y;
	input A1, A2, B1, B2;

	// Function
	wire int_fwire_0, int_fwire_1, int_fwire_2;
	wire int_fwire_3;

	and (int_fwire_0, A2, B2);
	and (int_fwire_1, A2, B1);
	and (int_fwire_2, A1, B2);
	and (int_fwire_3, A1, B1);
	or (Y, int_fwire_3, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((~A2 & B1 & B2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & ~B2))
			(A1 => Y) = 0;
		if ((~A2 & ~B1 & B2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((~A1 & B1 & B2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & ~B2))
			(A2 => Y) = 0;
		if ((~A1 & ~B1 & B2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & A2 & ~B2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~B2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~B2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & A2 & ~B1))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~B1))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~B1))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
	endspecify
endmodule
module OA31x2_ASAP7_75t_R (Y, A1, A2, A3, B1);
	output Y;
	input A1, A2, A3, B1;

	// Function
	wire int_fwire_0, int_fwire_1, int_fwire_2;

	and (int_fwire_0, A3, B1);
	and (int_fwire_1, A2, B1);
	and (int_fwire_2, A1, B1);
	or (Y, int_fwire_2, int_fwire_1, int_fwire_0);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		(A3 => Y) = 0;
		if ((A1 & A2 & A3))
			(B1 => Y) = 0;
		if ((A1 & A2 & ~A3))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & A3) | (~A1 & A2 & A3))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~A3))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~A3))
			(B1 => Y) = 0;
		if ((~A1 & ~A2 & A3))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
	endspecify
endmodule
module OAI21x1_ASAP7_75t_R (Y, A1, A2, B);
	output Y;
	input A1, A2, B;

	// Function
	wire A1__bar, A2__bar, B__bar;
	wire int_fwire_0;

	not (B__bar, B);
	not (A2__bar, A2);
	not (A1__bar, A1);
	and (int_fwire_0, A1__bar, A2__bar);
	or (Y, int_fwire_0, B__bar);

	// Timing
	specify
		(A1 => Y) = 0;
		(A2 => Y) = 0;
		if ((A1 & A2))
			(B => Y) = 0;
		if ((A1 & ~A2))
			(B => Y) = 0;
		if ((~A1 & A2))
			(B => Y) = 0;
		ifnone (B => Y) = 0;
	endspecify
endmodule
module OAI22x1_ASAP7_75t_R (Y, A1, A2, B1, B2);
	output Y;
	input A1, A2, B1, B2;

	// Function
	wire A1__bar, A2__bar, B1__bar;
	wire B2__bar, int_fwire_0, int_fwire_1;

	not (B2__bar, B2);
	not (B1__bar, B1);
	and (int_fwire_0, B1__bar, B2__bar);
	not (A2__bar, A2);
	not (A1__bar, A1);
	and (int_fwire_1, A1__bar, A2__bar);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if ((~A2 & B1 & B2))
			(A1 => Y) = 0;
		if ((~A2 & B1 & ~B2))
			(A1 => Y) = 0;
		if ((~A2 & ~B1 & B2))
			(A1 => Y) = 0;
		ifnone (A1 => Y) = 0;
		if ((~A1 & B1 & B2))
			(A2 => Y) = 0;
		if ((~A1 & B1 & ~B2))
			(A2 => Y) = 0;
		if ((~A1 & ~B1 & B2))
			(A2 => Y) = 0;
		ifnone (A2 => Y) = 0;
		if ((A1 & A2 & ~B2))
			(B1 => Y) = 0;
		if ((A1 & ~A2 & ~B2))
			(B1 => Y) = 0;
		if ((~A1 & A2 & ~B2))
			(B1 => Y) = 0;
		ifnone (B1 => Y) = 0;
		if ((A1 & A2 & ~B1))
			(B2 => Y) = 0;
		if ((A1 & ~A2 & ~B1))
			(B2 => Y) = 0;
		if ((~A1 & A2 & ~B1))
			(B2 => Y) = 0;
		ifnone (B2 => Y) = 0;
	endspecify
endmodule
module OR2x2_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	or (Y, A, B);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
	endspecify
endmodule
module OR3x1_ASAP7_75t_R (Y, A, B, C);
	output Y;
	input A, B, C;

	// Function
	or (Y, A, B, C);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
	endspecify
endmodule
module OR4x1_ASAP7_75t_R (Y, A, B, C, D);
	output Y;
	input A, B, C, D;

	// Function
	or (Y, A, B, C, D);

	// Timing
	specify
		(A => Y) = 0;
		(B => Y) = 0;
		(C => Y) = 0;
		(D => Y) = 0;
	endspecify
endmodule
module TIEHIx1_ASAP7_75t_R (H);
	output H;

	// Function
	buf (H, 1'b1);

	// Timing
	specify
	endspecify
endmodule
module TIELOx1_ASAP7_75t_R (L);
	output L;

	// Function
	buf (L, 1'b0);

	// Timing
	specify
	endspecify
endmodule
module XNOR2x2_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	wire A__bar, B__bar, int_fwire_0;
	wire int_fwire_1;

	not (B__bar, B);
	not (A__bar, A);
	and (int_fwire_0, A__bar, B__bar);
	and (int_fwire_1, A, B);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if (B)
			(A => Y) = 0;
		if (~B)
			(A => Y) = 0;
		if (A)
			(B => Y) = 0;
		if (~A)
			(B => Y) = 0;
	endspecify
endmodule
module XOR2x2_ASAP7_75t_R (Y, A, B);
	output Y;
	input A, B;

	// Function
	wire A__bar, B__bar, int_fwire_0;
	wire int_fwire_1;

	not (A__bar, A);
	and (int_fwire_0, A__bar, B);
	not (B__bar, B);
	and (int_fwire_1, A, B__bar);
	or (Y, int_fwire_1, int_fwire_0);

	// Timing
	specify
		if (~B)
			(A => Y) = 0;
		if (B)
			(A => Y) = 0;
		if (~A)
			(B => Y) = 0;
		if (A)
			(B => Y) = 0;
	endspecify
endmodule

primitive proj_altos_dff (q, v, clk, d, xcr);
	output q;
	reg q;
	input v, clk, d, xcr;

	table
		*  ?   ? ? : ? : x;
		? (x1) 0 0 : ? : 0;
		? (x1) 1 0 : ? : 1;
		? (x1) 0 1 : 0 : 0;
		? (x1) 1 1 : 1 : 1;
		? (x1) ? x : ? : -;
		? (bx) 0 ? : 0 : -;
		? (bx) 1 ? : 1 : -;
		? (x0) b ? : ? : -;
		? (x0) ? x : ? : -;
		? (01) 0 ? : ? : 0;
		? (01) 1 ? : ? : 1;
		? (10) ? ? : ? : -;
		?  b   * ? : ? : -;
		?  ?   ? * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_init0 (q, v, clk, d, xcr);
	output q;
	reg q;
	input v, clk, d, xcr;

	initial q = 1'b0;
	table
		*  ?   ? ? : ? : x;
		? (x1) 0 0 : ? : 0;
		? (x1) 1 0 : ? : 1;
		? (x1) 0 1 : 0 : 0;
		? (x1) 1 1 : 1 : 1;
		? (x1) ? x : ? : -;
		? (bx) 0 ? : 0 : -;
		? (bx) 1 ? : 1 : -;
		? (x0) b ? : ? : -;
		? (x0) ? x : ? : -;
		? (01) 0 ? : ? : 0;
		? (01) 1 ? : ? : 1;
		? (10) ? ? : ? : -;
		?  b   * ? : ? : -;
		?  ?   ? * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_init1 (q, v, clk, d, xcr);
	output q;
	reg q;
	input v, clk, d, xcr;

	initial q = 1'b1;
	table
		*  ?   ? ? : ? : x;
		? (x1) 0 0 : ? : 0;
		? (x1) 1 0 : ? : 1;
		? (x1) 0 1 : 0 : 0;
		? (x1) 1 1 : 1 : 1;
		? (x1) ? x : ? : -;
		? (bx) 0 ? : 0 : -;
		? (bx) 1 ? : 1 : -;
		? (x0) b ? : ? : -;
		? (x0) ? x : ? : -;
		? (01) 0 ? : ? : 0;
		? (01) 1 ? : ? : 1;
		? (10) ? ? : ? : -;
		?  b   * ? : ? : -;
		?  ?   ? * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_sr_0 (q, v, clk, d, s, r, xcr);
	output q;
	reg q;
	input v, clk, d, s, r, xcr;

	table
	//	v,  clk, d, s, r : q' : q;

		*  ?   ?   ?   ?   ? : ? : x;
		?  ?   ?   ?   1   ? : ? : 0;
		?  ?   ?   1   0   ? : ? : 1;
		?  b   ? (1?)  0   ? : 1 : -;
		?  x   1 (1?)  0   ? : 1 : -;
		?  ?   ? (10)  0   ? : ? : -;
		?  ?   ? (x0)  0   ? : ? : -;
		?  ?   ? (0x)  0   ? : 1 : -;
		?  b   ?  0   (1?) ? : 0 : -;
		?  x   0  0   (1?) ? : 0 : -;
		?  ?   ?  0   (10) ? : ? : -;
		?  ?   ?  0   (x0) ? : ? : -;
		?  ?   ?  0   (0x) ? : 0 : -;
		? (x1) 0  0    ?   0 : ? : 0;
		? (x1) 1  ?    0   0 : ? : 1;
		? (x1) 0  0    ?   1 : 0 : 0;
		? (x1) 1  ?    0   1 : 1 : 1;
		? (x1) ?  ?    0   x : ? : -;
		? (x1) ?  0    ?   x : ? : -;
		? (1x) 0  0    ?   ? : 0 : -;
		? (1x) 1  ?    0   ? : 1 : -;
		? (x0) 0  0    ?   ? : ? : -;
		? (x0) 1  ?    0   ? : ? : -;
		? (x0) ?  0    0   x : ? : -;
		? (0x) 0  0    ?   ? : 0 : -;
		? (0x) 1  ?    0   ? : 1 : -;
		? (01) 0  0    ?   ? : ? : 0;
		? (01) 1  ?    0   ? : ? : 1;
		? (10) ?  0    ?   ? : ? : -;
		? (10) ?  ?    0   ? : ? : -;
		?  b   *  0    ?   ? : ? : -;
		?  b   *  ?    0   ? : ? : -;
		?  ?   ?  ?    ?   * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_sr_0_init0 (q, v, clk, d, s, r, xcr);
	output q;
	reg q;
	input v, clk, d, s, r, xcr;

	initial q = 1'b0;
	table
	//	v,  clk, d, s, r : q' : q;

		*  ?   ?   ?   ?   ? : ? : x;
		?  ?   ?   ?   1   ? : ? : 0;
		?  ?   ?   1   0   ? : ? : 1;
		?  b   ? (1?)  0   ? : 1 : -;
		?  x   1 (1?)  0   ? : 1 : -;
		?  ?   ? (10)  0   ? : ? : -;
		?  ?   ? (x0)  0   ? : ? : -;
		?  ?   ? (0x)  0   ? : 1 : -;
		?  b   ?  0   (1?) ? : 0 : -;
		?  x   0  0   (1?) ? : 0 : -;
		?  ?   ?  0   (10) ? : ? : -;
		?  ?   ?  0   (x0) ? : ? : -;
		?  ?   ?  0   (0x) ? : 0 : -;
		? (x1) 0  0    ?   0 : ? : 0;
		? (x1) 1  ?    0   0 : ? : 1;
		? (x1) 0  0    ?   1 : 0 : 0;
		? (x1) 1  ?    0   1 : 1 : 1;
		? (x1) ?  ?    0   x : ? : -;
		? (x1) ?  0    ?   x : ? : -;
		? (1x) 0  0    ?   ? : 0 : -;
		? (1x) 1  ?    0   ? : 1 : -;
		? (x0) 0  0    ?   ? : ? : -;
		? (x0) 1  ?    0   ? : ? : -;
		? (x0) ?  0    0   x : ? : -;
		? (0x) 0  0    ?   ? : 0 : -;
		? (0x) 1  ?    0   ? : 1 : -;
		? (01) 0  0    ?   ? : ? : 0;
		? (01) 1  ?    0   ? : ? : 1;
		? (10) ?  0    ?   ? : ? : -;
		? (10) ?  ?    0   ? : ? : -;
		?  b   *  0    ?   ? : ? : -;
		?  b   *  ?    0   ? : ? : -;
		?  ?   ?  ?    ?   * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_sr_0_init1 (q, v, clk, d, s, r, xcr);
	output q;
	reg q;
	input v, clk, d, s, r, xcr;

	initial q = 1'b1;
	table
	//	v,  clk, d, s, r : q' : q;

		*  ?   ?   ?   ?   ? : ? : x;
		?  ?   ?   ?   1   ? : ? : 0;
		?  ?   ?   1   0   ? : ? : 1;
		?  b   ? (1?)  0   ? : 1 : -;
		?  x   1 (1?)  0   ? : 1 : -;
		?  ?   ? (10)  0   ? : ? : -;
		?  ?   ? (x0)  0   ? : ? : -;
		?  ?   ? (0x)  0   ? : 1 : -;
		?  b   ?  0   (1?) ? : 0 : -;
		?  x   0  0   (1?) ? : 0 : -;
		?  ?   ?  0   (10) ? : ? : -;
		?  ?   ?  0   (x0) ? : ? : -;
		?  ?   ?  0   (0x) ? : 0 : -;
		? (x1) 0  0    ?   0 : ? : 0;
		? (x1) 1  ?    0   0 : ? : 1;
		? (x1) 0  0    ?   1 : 0 : 0;
		? (x1) 1  ?    0   1 : 1 : 1;
		? (x1) ?  ?    0   x : ? : -;
		? (x1) ?  0    ?   x : ? : -;
		? (1x) 0  0    ?   ? : 0 : -;
		? (1x) 1  ?    0   ? : 1 : -;
		? (x0) 0  0    ?   ? : ? : -;
		? (x0) 1  ?    0   ? : ? : -;
		? (x0) ?  0    0   x : ? : -;
		? (0x) 0  0    ?   ? : 0 : -;
		? (0x) 1  ?    0   ? : 1 : -;
		? (01) 0  0    ?   ? : ? : 0;
		? (01) 1  ?    0   ? : ? : 1;
		? (10) ?  0    ?   ? : ? : -;
		? (10) ?  ?    0   ? : ? : -;
		?  b   *  0    ?   ? : ? : -;
		?  b   *  ?    0   ? : ? : -;
		?  ?   ?  ?    ?   * : ? : -;
	endtable
endprimitive
primitive proj_altos_dff_err (q, clk, d);
	output q;
	reg q;
	input clk, d;

	table
		(0x) ? : ? : 0;
		(1x) ? : ? : 1;
	endtable
endprimitive
primitive proj_altos_dff_sr_err (q, clk, d, s, r);
	output q;
	reg q;
	input clk, d, s, r;

	table
		 ?   1 (0x)  ?   : ? : -;
		 ?   0  ?   (0x) : ? : -;
		 ?   0  ?   (x0) : ? : -;
		(0x) ?  0    0   : ? : 0;
		(0x) 1  x    0   : ? : 0;
		(0x) 0  0    x   : ? : 0;
		(1x) ?  0    0   : ? : 1;
		(1x) 1  x    0   : ? : 1;
		(1x) 0  0    x   : ? : 1;
	endtable
endprimitive
module DFFHQNx1_ASAP7_75t_R #(parameter INIT=-1)(output QN,input D,CLK);
reg notifier;wire nd,xcr;not(nd,D);proj_altos_dff_err e(xcr,CLK,nd);
generate if(INIT==0)begin proj_altos_dff_init0 u(QN,notifier,CLK,nd,xcr);end
else if(INIT==1)begin proj_altos_dff_init1 u(QN,notifier,CLK,nd,xcr);end
else begin proj_altos_dff u(QN,notifier,CLK,nd,xcr);end endgenerate
endmodule
module DFFASRHQNx1_ASAP7_75t_R #(parameter INIT=-1)(output QN,input D,RESETN,SETN,CLK);
reg notifier;wire nd,ns,nr,xcr;not(nd,D);not(ns,RESETN);not(nr,SETN);
proj_altos_dff_sr_err e(xcr,CLK,nd,ns,nr);
generate if(INIT==0)begin proj_altos_dff_sr_0_init0 u(QN,notifier,CLK,nd,ns,nr,xcr);end
else if(INIT==1)begin proj_altos_dff_sr_0_init1 u(QN,notifier,CLK,nd,ns,nr,xcr);end
else begin proj_altos_dff_sr_0 u(QN,notifier,CLK,nd,ns,nr,xcr);end endgenerate
endmodule
