// tb_mtp_wave golden content functions (included inside each bench module; el1011-ds-mtp wave bench, 2026-10-11).
//   wv_mix      the S0 vehicle's hash (tb_mtp_rom_s0_tokpipe mix)
//   wv_word     a 512-b HIDDEN payload word of hop s (s = die d's input: d; die d's output: 100 + d), position p, token t
//   wv_beat     a 1,024-b main-hidden row beat (part, position, token at the position, beat)
//   wv_fc       fast-cycle index of the current simulation time (fclk period 3 ns, rising edges at 1.5 + 3k)
function automatic [31:0] wv_mix(input [31:0] h, input [31:0] x);
    reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
    wv_mix = t ^ (t >> 12); end
endfunction
function automatic [511:0] wv_word(input integer s, input integer p, input integer t, input integer w);
    integer b; reg [31:0] h; begin
        h = wv_mix(wv_mix(wv_mix(32'h5a5a0000 + s, p), t), w);
        for (b = 0; b < 16; b = b + 1) begin wv_word[b*32 +: 32] = h; h = wv_mix(h, b); end
    end
endfunction
function automatic [1023:0] wv_beat(input integer part, input integer p, input integer t, input integer b);
    integer k; reg [31:0] h; begin
        h = wv_mix(wv_mix(wv_mix(32'h3c3c0000 + part, p), t), b);
        for (k = 0; k < 32; k = k + 1) begin wv_beat[k*32 +: 32] = h; h = wv_mix(h, k); end
    end
endfunction
function automatic integer wv_fc(input integer dummy);
    wv_fc = $rtoi($realtime / 3.0);
endfunction
