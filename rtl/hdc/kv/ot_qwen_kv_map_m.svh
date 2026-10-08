// ---------------------------------------------------------------------------
// Qwen3-8B ROM die, 4-stack STREAM4 KV map, OPTION M (quadrant-local stripe; default-off, KV_MAP = 1).
// Included inside ot_qwen_rt_kv_stream4_service, ot_qwen_hbm_stream4_ack and ot_qwen_hbm_stream4_cdc.
//
// The layer-relative logical sector layout is unchanged (lsec = {r[7], r[6], g[8:0], r[5:0]}: g = 16-position
// tile, r < 128 K of head r[6] dim pair r[5:0], r >= 128 V of head r[6] position g*16 + r[5:2] dim pair r[1:0]);
// so are the tile slice map, the window, the backing store and the DRAM walk of a PC's stream index j.  What
// changes is WHICH stack / pseudo-channel streams a sector, and its place j in that PC's stream:
//   stack k = the die quadrant of the sector's destination tiles under the option-M tile binding
//             (WS{blocks 0-15, 64-71} WN{16-31, 72-79} ES{32-47, 80-87} EN{48-63, 88-95}, block = tile / 16):
//     V: k = r[1:0]              (V halves of dim-octet pair r[1:0] land in blocks 16 r[1:0] .. 16 r[1:0] + 15)
//     K: k = QK(g mod 48)        (K of tile g lands in block 2 (g mod 48) + r[5]: residues 0-31 -> blocks 0-63,
//                                 quadrant res / 8; residues 32-47 -> blocks 64-95, quadrant (res - 32) / 4)
//   pseudo-channel q = {r[6], r[5:2]} (as the base map);
//   PC stream, per tile g in order: [K r[1:0] = 0..3 if QK(g) == k] then [V]  (5 or 1 sectors).
// Every stack carries 12 of every 48 K tiles, so at P8191 (512 tiles) each PC streams exactly 1,024 sectors as in
// the base map; for other P the per-stack count differs (n_m), the descriptor's n is converted per stack.
// Destination check: every sector's tiles are inside its stack's quadrant (the die's per-stack landing crossbar,
// die r19 qfd_kvc: 32 PCs -> the quadrant's 12 tile rows).
// ---------------------------------------------------------------------------
function automatic [1:0] m_qk(input [8:0] g);
    integer r; begin r = integer'(g) % 48; m_qk = 2'(r < 32 ? r / 8 : (r - 32) / 4); end
endfunction
function automatic integer m_cnt_in(input integer k, input integer t);   // residues < t of 0..47 with QK == k
    integer a; begin
        a = t - 8 * k; a = a < 0 ? 0 : (a > 8 ? 8 : a);
        if (t > 32) begin m_cnt_in = t - 32 - 4 * k; m_cnt_in = 8 + (m_cnt_in < 0 ? 0 : (m_cnt_in > 4 ? 4 : m_cnt_in)); end
        else m_cnt_in = a;
    end
endfunction
function automatic integer m_base(input integer k, input integer g);   // first stream index of tile g, stack k
    m_base = g + 4 * (12 * (g / 48) + m_cnt_in(k, g % 48));
endfunction
function automatic [16:0] m_p2l(input integer port, input [9:0] j);
    integer k, t, off, r, len, g; reg [4:0] q; reg [2:0] it; reg found;
    begin
        k = port / 32; q = 5'(port % 32);
        t = integer'(j) % 96; off = 0; found = 1'b0; g = 0; it = 0;
        for (r = 0; r < 48; r = r + 1) begin
            len = (integer'(m_qk(9'(r))) == k) ? 5 : 1;
            if (!found && t < off + len) begin found = 1'b1; g = 48 * (integer'(j) / 96) + r; it = 3'(t - off); end
            off = off + len;
        end
        if (integer'(m_qk(9'(g))) == k && it < 4) m_p2l = {1'b0, q[4], 9'(g), q[3:0], it[1:0]};     // K
        else m_p2l = {1'b1, q[4], 9'(g), q[3:0], 2'(k)};                                          // V
    end
endfunction
function automatic integer m_l2port(input [16:0] l);
    m_l2port = (l[16] ? integer'(l[1:0]) : integer'(m_qk(l[14:6]))) * 32 + integer'({l[15], l[5:2]});
endfunction
function automatic [9:0] m_l2j(input [16:0] l);
    integer k, g; begin
        g = integer'(l[14:6]); k = l[16] ? integer'(l[1:0]) : integer'(m_qk(l[14:6]));
        m_l2j = 10'(m_base(k, g) + (l[16] ? ((integer'(m_qk(l[14:6])) == k) ? 4 : 0) : integer'(l[1:0])));
    end
endfunction
function automatic [10:0] m_n(input integer k, input [10:0] n);      // per-PC sectors of stack k for base n = 2 G0
    m_n = 11'(m_base(k, integer'(n) / 2));
endfunction
