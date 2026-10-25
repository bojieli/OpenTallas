"""Opt-in physical source transform: ROM-local replicas of the issue counter.

The pinned arithmetic source stays untouched. Only the two macro addr_in
connections change to dedicated same-edge address copies. No cycle is added.
"""
from pathlib import Path

def transform(text):
    anchor='    wire last = a == NPHYS - 1;'
    assert text.count(anchor)==1,'pinned issue counter anchor changed'
    for bank in (0,1):
        old=f'u_rom{bank} (.clk(clk), .ce_in(ce{bank}_q), .addr_in(a[12:1]), .rd_out(rd{bank}));'
        assert text.count(old)==1,f'pinned ROM{bank} connection changed'
        text=text.replace(old,old.replace('a[12:1]',f'rom_addr{bank}'))
    copies='''
    // Same edge as a <= a+1 / clear / hold; physical copies cannot be shared across ROMs.
    wire [13:0] rom_addr_next = a + 14'd1;
    wire [11:0] rom_addr0, rom_addr1;
    ot_s81hd_rom_addr_copy #(.BANK(0)) u_rom_addr0 (.clk(clk), .rst_n(rst_n),
        .clear(go_r), .advance(run), .next_addr(rom_addr_next[12:1]), .addr(rom_addr0));
    ot_s81hd_rom_addr_copy #(.BANK(1)) u_rom_addr1 (.clk(clk), .rst_n(rst_n),
        .clear(go_r), .advance(run), .next_addr(rom_addr_next[12:1]), .addr(rom_addr1));
'''
    return text.replace(anchor,anchor+copies)
