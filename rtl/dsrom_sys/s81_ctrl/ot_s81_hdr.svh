// ot_s81_hdr.svh (stream ds-control, 2026-10-08): the S81 array's message header (flit 0 of every stage-to-stage
// message), the S81-geometry successor of ot_rom_pkg_ctrl_x's header.  What changes at S81 (120 stages x 4 TP dies,
// 12 head dies, 1,792 pairs, 1M context, 129,280-entry vocabulary):
//   * fabric ids are 12 bits (480 layer dies + 12 head dies + host + multicast groups > 256);
//   * LEN is 12 bits: a HIDDEN message is 640 flits of 64 B (40,976 B: 4 x 5,120 FP32 + header, the measured hop);
//   * USER is 12 bits;
//   * POS / IDX / TOK are NW = 21 bits (position 1,048,575 and token ids < 2^17 both fit);
//   * the run's stop configuration rides in every HIDDEN header, so the head die's sampler (ot_s81_stop) needs no
//     configuration path of its own: EOSEN, EOS (the released eos_token_id, 1) and MAXL (maximum sequence length);
//   * STOP: set by the head die on a RESULT whose token ends the user's sequence.
// Field offsets (bits): DEST 0+12, SRC 12+12, TYPE 24+4, LEN 28+12, USER 40+12, POS 52+21, IDX 73+21, VAL 94+32,
// TOK 126+21, ADDR 147+16, STOP 163, EOSEN 164, EOS 165+21, MAXL 186+22 (208 bits of a 512-bit flit).
// Included inside each module body (module-scope localparams); no include guard.
localparam integer SH_DEST = 0, SH_SRC = 12, SH_TYPE = 24, SH_LEN = 28, SH_USER = 40, SH_POS = 52, SH_IDX = 73,
                   SH_VAL = 94, SH_TOK = 126, SH_ADDR = 147, SH_STOP = 163, SH_EOSEN = 164, SH_EOS = 165,
                   SH_MAXL = 186, SH_END = 208;
localparam integer SH_IDW = 12, SH_LENW = 12, SH_UW = 12, SH_NW = 21, SH_MLW = 22;
localparam [3:0] MT_HIDDEN = 4'd1, MT_RESULT = 4'd2, MT_SIDE = 4'd3;
