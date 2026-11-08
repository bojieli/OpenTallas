function [31:0] ot_rest_round32(input [31:0] x);
  reg carry;
  begin
    carry = x[15] & ((|x[14:0]) | x[16]);
    ot_rest_round32[0] = x[16] ? x[0] : ~x[0];
    ot_rest_round32[1] = x[16] ? x[1] : (x[1] ^ (~|x[0:0]));
    ot_rest_round32[2] = x[16] ? x[2] : (x[2] ^ (~|x[1:0]));
    ot_rest_round32[3] = x[16] ? x[3] : (x[3] ^ (~|x[2:0]));
    ot_rest_round32[4] = x[16] ? x[4] : (x[4] ^ (~|x[3:0]));
    ot_rest_round32[5] = x[16] ? x[5] : (x[5] ^ (~|x[4:0]));
    ot_rest_round32[6] = x[16] ? x[6] : (x[6] ^ (~|x[5:0]));
    ot_rest_round32[7] = x[16] ? x[7] : (x[7] ^ (~|x[6:0]));
    ot_rest_round32[8] = x[16] ? x[8] : (x[8] ^ (~|x[7:0]));
    ot_rest_round32[9] = x[16] ? x[9] : (x[9] ^ (~|x[8:0]));
    ot_rest_round32[10] = x[16] ? x[10] : (x[10] ^ (~|x[9:0]));
    ot_rest_round32[11] = x[16] ? x[11] : (x[11] ^ (~|x[10:0]));
    ot_rest_round32[12] = x[16] ? x[12] : (x[12] ^ (~|x[11:0]));
    ot_rest_round32[13] = x[16] ? x[13] : (x[13] ^ (~|x[12:0]));
    ot_rest_round32[14] = x[16] ? x[14] : (x[14] ^ (~|x[13:0]));
    ot_rest_round32[15] = x[15] ^ (x[16] | (|x[14:0]));
    ot_rest_round32[16] = x[16] ^ carry;
    ot_rest_round32[17] = x[17] ^ (carry & (&x[16:16]));
    ot_rest_round32[18] = x[18] ^ (carry & (&x[17:16]));
    ot_rest_round32[19] = x[19] ^ (carry & (&x[18:16]));
    ot_rest_round32[20] = x[20] ^ (carry & (&x[19:16]));
    ot_rest_round32[21] = x[21] ^ (carry & (&x[20:16]));
    ot_rest_round32[22] = x[22] ^ (carry & (&x[21:16]));
    ot_rest_round32[23] = x[23] ^ (carry & (&x[22:16]));
    ot_rest_round32[24] = x[24] ^ (carry & (&x[23:16]));
    ot_rest_round32[25] = x[25] ^ (carry & (&x[24:16]));
    ot_rest_round32[26] = x[26] ^ (carry & (&x[25:16]));
    ot_rest_round32[27] = x[27] ^ (carry & (&x[26:16]));
    ot_rest_round32[28] = x[28] ^ (carry & (&x[27:16]));
    ot_rest_round32[29] = x[29] ^ (carry & (&x[28:16]));
    ot_rest_round32[30] = x[30] ^ (carry & (&x[29:16]));
    ot_rest_round32[31] = x[31] ^ (carry & (&x[30:16]));
  end
endfunction
