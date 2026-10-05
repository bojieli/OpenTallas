// ---------------------------------------------------------------------------
// Index-key ROW LAYOUT (opt-in; the 4-KB super-block layout of ot_hdc_v41x_idx_kstream_range stays the
// default).  Included inside a module: the row-layout writer (ot_hdc_v41x_idx_ring_kwr_row), the row-layout
// reader (ot_hdc_v41x_idx_kgrow) and their benches all place a key with this one function.
//
// Unit: an 8-key BLOCK (8-aligned ring slots t = 8 x .. 8 x + 7) = 17 sectors: sector 0 the 8 keys' scales
// (4 B a key, key k at bytes 4k..4k+3), sectors 1 + 2k / 2 + 2k key k's 64 code bytes (low / high half).
// Every block owns ONE DRAM row of ONE bank of ONE pseudo-channel and sits in columns 0..16 of it, so a
// block read is 1 ACT + 17 column reads (columns 17..31 of the row are unused: 47% of the row; see the
// record for the capacity cost).  Consecutive blocks rotate pseudo-channel first, then bank group, then
// bank (and SID): block x of a region based at row r0 is
//     row   = r0 + x / 1024              (1,024 blocks = 32 pseudo-channels x 32 banks fill one row index)
//     pc    = (x mod 32) ^ (row mod 32)   (the row rotates the channel order)
//     bank  = (x / 32) mod 32            (bank group = bank mod 4, bank in group + SID = bank / 4)
// so a channel's consecutive blocks rotate the four bank groups, then the 32 banks, then the row.
// In the controller's address map (ot_hdc_v41x_idx_hbm: sector s -> bank group s[1:0] ^ row[1:0],
// pseudo-channel s[6:2] ^ s[11:7] ^ s[16:12], column s[11:7], bank s[14:12] ^ row[4:2], row s >> 15) that is
//     s = {row, bank[4:2] ^ row[4:2], col[4:0], pc ^ col ^ {row[1:0], bank[4:2] ^ row[4:2]}, bank[1:0] ^ row[1:0]}
// with col = the block sector 0..16: pseudo-channel, bank and row are the same for all 17 sectors.
// ---------------------------------------------------------------------------
function automatic [63:0] idx_rowmap_sec(input [31:0] row0, input [31:0] x, input [4:0] col);
    reg [31:0] row;
    reg [4:0]  pc, bank;
    reg [2:0]  b42;
    reg [1:0]  b10;
    begin
        row  = row0 + (x >> 10);
        pc   = x[4:0] ^ row[4:0];
        bank = x[9:5];
        b42  = bank[4:2] ^ row[4:2];
        b10  = bank[1:0] ^ row[1:0];
        idx_rowmap_sec = {17'd0, row, b42, col, pc ^ col ^ {row[1:0], b42}, b10};
    end
endfunction
