`timescale 1ns/1ps
// Released native1737 primitive arithmetic, not a PC40 fragment or controller.
// Stateless beat: Pauli owns captured operands, whole result, identity, ECC,
// publication, terminal/reverse, clock and all provider leases. ENABLE=0.
// LANES4 is one actual32-byte operand beat; controller walks max128 elements.
module ot_hbm_accel_native_bits #(
 parameter integer ENABLE=0, LANES=4
)(
 input wire [4:0] opcode,
 input wire [1:0] dtype,a_type,b_type,c_type,
 input wire a_scalar,b_scalar,c_scalar,
 input wire [LANES-1:0] lane_mask,
 input wire [LANES*64-1:0] a_data,b_data,c_data,
 output wire [LANES*64-1:0] result,
 output reg [1:0] result_type,
 output wire [LANES-1:0] lane_fault,
 output wire supported
);
 localparam [1:0] F32=0,U32=1,I64=2;
 localparam [4:0] COPY=0,BITCAST_U=1,BITCAST_F=2,AND_OP=3,OR_OP=4,XOR_OP=5,
  IADD=6,ISUB=7,SHR=8,SHL=9,GT=10,LT=11,EQ=12,NE=13,SELECT_OP=14,FMAX=15,FMIN=16;
 assign supported=(ENABLE!=0)&&(opcode<=FMIN);
 always @* begin
  result_type=dtype;
  case(opcode)
   COPY:result_type=a_type;
   BITCAST_U,GT,LT,EQ,NE:result_type=U32;
   BITCAST_F,FMAX,FMIN:result_type=F32;
   default:result_type=dtype;
  endcase
  if(ENABLE==0)result_type=F32;
 end
 genvar l;
 generate for(l=0;l<LANES;l=l+1)begin:g_lane
  if(ENABLE!=0)begin:g_enabled
   wire [63:0] a=a_scalar?a_data[63:0]:a_data[l*64+:64];
   wire [63:0] b=b_scalar?b_data[63:0]:b_data[l*64+:64];
   wire [63:0] c=c_scalar?c_data[63:0]:c_data[l*64+:64];
   // Numeric cast of integer operands: U32 zero extends; I64 keeps its bits.
   // Explicit U32 dtype truncates after the operation, exactly modulo2^32.
   wire [63:0] ai=(a_type==I64)?a:{32'd0,a[31:0]};
   wire [63:0] bi=(b_type==I64)?b:{32'd0,b[31:0]};
   wire [63:0] ci=(c_type==I64)?c:{32'd0,c[31:0]};
   wire integer_args=(a_type==U32||a_type==I64)&&(b_type==U32||b_type==I64);
   wire cmp_float=(a_type==F32)&&(b_type==F32);
   wire nan_a=(a[30:23]==8'hff)&&(|a[22:0]);
   wire nan_b=(b[30:23]==8'hff)&&(|b[22:0]);
   wire both_zero=(a[30:0]==0)&&(b[30:0]==0);
   wire float_eq=(a[31:0]==b[31:0])||both_zero;
   wire float_lt=(a[31]!=b[31])?a[31]:a[31]?(a[30:0]>b[30:0]):(a[30:0]<b[30:0]);
   // Mixed U32/I64 compares promote numerically to signedI64; U32 fits.
   wire int_lt=$signed(ai)<$signed(bi);
   wire int_eq=ai==bi;
   wire less=cmp_float?(!nan_a&&!nan_b&&!float_eq&&float_lt):int_lt;
   wire equal=cmp_float?(!nan_a&&!nan_b&&float_eq):int_eq;
   wire greater=cmp_float?(!nan_a&&!nan_b&&!float_eq&&!float_lt):(!int_lt&&!int_eq);
   wire unequal=cmp_float?(nan_a||nan_b||!float_eq):!int_eq;
   wire nonzero_a=(a_type==F32)?(|a[30:0]):(a_type==U32)?(|a[31:0]):(|a);
   wire sub=(opcode==ISUB);
   wire [63:0] shift_count=(dtype==U32)?{32'd0,bi[31:0]}:bi;
   wire signed [63:0] signed_right=$signed(ai)>>>shift_count[5:0];
   wire [63:0] sum;wire carry_unused;
   // Reuse the existing log-depth exact integer adder, not a mapped ripple.
   ot_hdc_ksadd_k #(.W(64))u_int(.a(ai),.b(sub?~bi:bi),.cin(sub),.s(sum),.cout(carry_unused));
   reg [63:0] value;
   reg bad;
   reg [31:0] chosen_float;
   always @* begin
    value=0;bad=0;chosen_float=0;
    case(opcode)
     COPY:begin value=(a_type==I64)?a:{32'd0,a[31:0]};bad=(a_type==3);end
     BITCAST_U:begin value={32'd0,a[31:0]};bad=(a_type!=F32);end
     BITCAST_F:begin value={32'd0,a[31:0]};bad=(a_type!=U32&&a_type!=I64);end
     AND_OP,OR_OP,XOR_OP,IADD,ISUB,SHR,SHL:begin
      bad=!integer_args||(dtype!=U32&&dtype!=I64);
      case(opcode)
       AND_OP:value=ai&bi;
       OR_OP:value=ai|bi;
       XOR_OP:value=ai^bi;
       IADD,ISUB:value=sum;
       SHR:begin
        bad=bad||(shift_count>=((dtype==I64)?64:32));
        value=(dtype==I64)?signed_right:({32'd0,ai[31:0]}>>shift_count[5:0]);
       end
       SHL:begin
        bad=bad||(shift_count>=((dtype==I64)?64:32));
        value=ai<<shift_count[5:0];
       end
       default:value=0;
      endcase
      if(dtype==U32)value={32'd0,value[31:0]};
     end
     GT,LT,EQ,NE:begin
      bad=!(cmp_float||integer_args);
      case(opcode)
       GT:value={63'd0,greater};
       LT:value={63'd0,less};
       EQ:value={63'd0,equal};
       NE:value={63'd0,unequal};
       default:value=0;
      endcase
     end
     SELECT_OP:begin
      bad=(a_type==3)||(dtype==3);
      if(dtype==F32)begin
       bad=bad||(b_type!=F32)||(c_type!=F32);
       value={32'd0,nonzero_a?b[31:0]:c[31:0]};
      end else begin
       bad=bad||(b_type!=U32&&b_type!=I64)||(c_type!=U32&&c_type!=I64);
       value=nonzero_a?bi:ci;
       if(dtype==U32)value={32'd0,value[31:0]};
      end
     end
     FMAX,FMIN:begin
      bad=!cmp_float;
      // np.maximum/minimum preserve the first NaN payload and return the
      // second operand on equal values, including opposite signed zeros.
      if(nan_a)chosen_float=a[31:0];
      else if(nan_b)chosen_float=b[31:0];
      else if(float_eq)chosen_float=b[31:0];
      else if(opcode==FMAX)chosen_float=float_lt?b[31:0]:a[31:0];
      else chosen_float=float_lt?a[31:0]:b[31:0];
      value={32'd0,chosen_float};
     end
     default:bad=1;
    endcase
   end
   assign result[l*64+:64]=lane_mask[l]?value:64'd0;
   assign lane_fault[l]=lane_mask[l]&&bad;
  end else begin:g_disabled
   assign result[l*64+:64]=0;
   assign lane_fault[l]=0;
  end
 end endgenerate
endmodule
