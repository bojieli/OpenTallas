// Immutable exact installer spans; no grant produced. Source SHA256 966e26b3ae32d310ced8a3667b8076a45b7d13ca4a449035cd8d90bc16516427
module ot_hbm_sm_native_tuple(input wire[15:0] record_id,output reg found,
 output reg[31:0]weight_base,output reg[32:0]weight_limit,
 output reg[36:0]x_base,output reg[37:0]x_limit,output reg[7:0]x_extent,output reg[6:0]x_ring,
 output reg[36:0]result_base,result_limit,output reg[12:0]result_rows);
 always @*begin found=0;weight_base=0;weight_limit=0;x_base=0;x_limit=0;x_extent=0;x_ring=0;result_base=0;result_limit=0;result_rows=0;
 case(record_id)
 16'd0:begin found=1;weight_base=32'd744759;weight_limit=33'd744839;x_base=37'd119174240;x_limit=38'd119440480;x_extent=8'd80;x_ring=7'd0;result_base=37'd119440480;result_limit=37'd119440512;result_rows=13'd1;end
16'd1:begin found=1;weight_base=32'd746504;weight_limit=33'd746584;x_base=37'd119453440;x_limit=38'd119719680;x_extent=8'd80;x_ring=7'd80;result_base=37'd119719680;result_limit=37'd119719712;result_rows=13'd1;end
16'd2:begin found=1;weight_base=32'd748249;weight_limit=33'd748281;x_base=37'd119724960;x_limit=38'd119778208;x_extent=8'd16;x_ring=7'd32;result_base=37'd119778208;result_limit=37'd119778272;result_rows=13'd2;end
16'd3:begin found=1;weight_base=32'd748615;weight_limit=33'd748871;x_base=37'd119819360;x_limit=38'd119845984;x_extent=8'd8;x_ring=7'd48;result_base=37'd119845984;result_limit=37'd119847008;result_rows=13'd32;end
16'd4:begin found=1;weight_base=32'd749044;weight_limit=33'd749172;x_base=37'd119867520;x_limit=38'd120080512;x_extent=8'd64;x_ring=7'd56;result_base=37'd120080512;result_limit=37'd120080576;result_rows=13'd2;end
16'd5:begin found=1;weight_base=32'd750504;weight_limit=33'd750528;x_base=37'd120084480;x_limit=38'd120164352;x_extent=8'd24;x_ring=7'd120;result_base=37'd120164352;result_limit=37'd120164384;result_rows=13'd1;end
16'd6:begin found=1;weight_base=32'd751028;weight_limit=33'd751268;x_base=37'd120202880;x_limit=38'd120469120;x_extent=8'd80;x_ring=7'd16;result_base=37'd120469120;result_limit=37'd120469216;result_rows=13'd3;end
16'd7:begin found=1;weight_base=32'd752933;weight_limit=33'd753189;x_base=37'd120510240;x_limit=38'd120563488;x_extent=8'd16;x_ring=7'd96;result_base=37'd120563488;result_limit=37'd120564000;result_rows=13'd16;end
16'd8:begin found=1;weight_base=32'd753525;weight_limit=33'd753557;x_base=37'd120510240;x_limit=38'd120563488;x_extent=8'd16;x_ring=7'd96;result_base=37'd120569120;result_limit=37'd120569184;result_rows=13'd2;end
16'd9:begin found=1;weight_base=32'd753558;weight_limit=33'd753638;x_base=37'd120582080;x_limit=38'd120848320;x_extent=8'd80;x_ring=7'd112;result_base=37'd120848320;result_limit=37'd120848352;result_rows=13'd1;end
16'd10:begin found=1;weight_base=32'd755303;weight_limit=33'd755351;x_base=37'd120856160;x_limit=38'd120936032;x_extent=8'd24;x_ring=7'd64;result_base=37'd120936032;result_limit=37'd120936096;result_rows=13'd2;end
16'd11:begin found=1;weight_base=32'd755851;weight_limit=33'd755883;x_base=37'd120941280;x_limit=38'd120994528;x_extent=8'd16;x_ring=7'd88;result_base=37'd120994528;result_limit=37'd120994592;result_rows=13'd2;end
16'd12:begin found=1;weight_base=32'd756217;weight_limit=33'd756473;x_base=37'd121035680;x_limit=38'd121062304;x_extent=8'd8;x_ring=7'd104;result_base=37'd121062304;result_limit=37'd121063328;result_rows=13'd32;end
 default:begin end
 endcase end
endmodule
