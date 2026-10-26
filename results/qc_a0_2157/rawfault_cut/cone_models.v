module AND3x1_ASAP7_75t_R(A,B,C,Y); input A,B,C; output Y; assign Y = (A & B & C); endmodule
module AND4x1_ASAP7_75t_R(A,B,C,D,Y); input A,B,C,D; output Y; assign Y = (A & B & C & D); endmodule
module AO21x1_ASAP7_75t_R(A1,A2,B,Y); input A1,A2,B; output Y; assign Y = (A1 & A2) | (B); endmodule
module INVx1_ASAP7_75t_R(A,Y); input A; output Y; assign Y = ~A; endmodule
module NAND2x1_ASAP7_75t_R(A,B,Y); input A,B; output Y; assign Y = (~A) | (~B); endmodule
