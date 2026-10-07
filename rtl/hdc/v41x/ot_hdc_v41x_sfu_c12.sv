`timescale 1ns/1ps
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_sfu.sv for the c12
// build, derived from the f12 file (rtl/hbm_accel/su/pinned_native/ot_hdc_v41x_sfu_f12.sv, unchanged).  Only
// ot_hdc_v41x_softplus changes, and only through two new parameters whose defaults are the f12 unit:
//   DDIV = 21  its divider u / (t + 2) is the DS ROM kit's ot_dsrom_fdiv_f12 (rtl/hdc/v41x/ot_dsrom_su_f12.sv; the
//              f12 divider's normalise stage missed 0.833 ns by 29 ps in the routed SFU lane): DEPTH + 2
//   FSQ = 1    its square root is ot_hdc_fsqrt_c12 (rtl/hdc/v41/ot_hdc_fsqrt_c12.sv: keep-prefix digit recurrence,
//              precomputed finish; same DEPTH 31; the routed softplus missed by 113 ps in ot_hdc_fsqrt's finish)
// DEPTH = exp + 11 LM + 10 LA + 31 + DDIV.  Bit-identical (the SU campaigns' SFU equivalence).
// hbm-fmax-su (2026-10-04): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_sfu.sv for the 1.2 GHz build: the original
// except ot_hdc_v41x_fdiv's timing-only rewrites (marked hbm-fmax-su; bit- and cycle-identical).  A source list names
// this file OR the original; the original (pinned by committed records) is unchanged.  Needs rtl/hdc/ot_hdc_prefix.sv.
// ---------------------------------------------------------------------------
// Special-function pipes of the V4.1 vector stream unit (ot_hdc_v41x_vec), at
// the fast-FP depths and with NO padding:
//
//   ot_hdc_v41x_exp       exp(x), DEPTH 49     } verbatim copies of ot_hdc_exp and
//   ot_hdc_v41x_rsqrt     1/sqrt(x), DEPTH 37  } ot_hdc_rsqrt in rtl/hdc/ot_hdc_sfu.sv
//                                                on branch worktree-agent-a516a664e7d53536c
//                                                (acc46e61), renamed only.  The
//                                                main-line file keeps the five-stage
//                                                pipes under the old names.  Their
//                                                algorithms are tools/hdc_golden.py
//                                                exp and rsqrt, checked there on all
//                                                2^32 inputs.
//   ot_hdc_v41x_fdiv      IEEE binary32 division, DEPTH 19 (rtl/hdc/v41/ot_hdc_fdiv's
//                         digit recurrence, two quotient bits per stage, radix-4 select)
//   ot_hdc_v41x_softplus  softplus and sqrt(softplus), DEPTH 162
//   ot_hdc_v41x_ins       an insertion delay line: variable depth, in order
//
// They are built from the fast binary32 add and multiply (rtl/hdc/ot_hdc_fastfp.sv:
// LATENCY 3, II 1), which are bit-identical to the qualified five-stage pipes.
// ---------------------------------------------------------------------------

// exp(x): clamp to [-87, 88]; t = x*log2e; n = rint(t); two-constant Cody-Waite
// reduction; degree-6 Horner; 2^n added to the exponent.
//
// The golden forms n by the 1.5*2^23 trick: u = t + 1.5*2^23 is the exact sum
// rounded to an integer, ties to even (|t| < 2^22 puts u in [2^23, 2^24), where
// the ulp is 1, and 1.5*2^23 is even), and n = u - 1.5*2^23 is exact.  That is
// rint-to-even of t, so here it is one integer step on t's encoding.  n*ln2_hi
// (exact) and RN(n*ln2_lo) depend on n alone, n in [-126, 127] after the clamp:
// a 254-entry table holding the golden's own products.
module ot_hdc_v41x_exp #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer T_N = 1 + LM + 1;        // n registered
    localparam integer T_K = T_N + 1;           // table products registered
    localparam integer T_R1 = T_K + LA;
    localparam integer T_R = T_R1 + LA;
    localparam integer T_P = T_R + 6 * (LM + LA);
    localparam integer DEPTH = T_P + 1;         // 7 LM + 8 LA + 4: 49 (LM 3), 56 (LM 4)
    localparam [31:0] K_MAX   = 32'h42B00000;   //  88.0
    localparam [31:0] K_MINM  = 32'h42AE0000;   //  87.0 (magnitude of the lower clamp)
    localparam [31:0] K_LOG2E = 32'h3FB8AA3B;
    localparam [32*7-1:0] POLY = {32'h3AB60B61, 32'h3C088889, 32'h3D2AAAAB,
                                  32'h3E2AAAAB, 32'h3F000000, 32'h3F800000, 32'h3F800000};
    function automatic [31:0] poly(input integer i);   // EXP_POLY[i]
        poly = POLY[32*(6-i) +: 32];
    endfunction
    //: {n*LN2_HI, RN(n*LN2_LO)}: the golden's binary32 products (hdc_golden.mul,
    //: canonical +0 at n = 0), indexed by n's low 8 bits.
    function automatic [63:0] ln2_nk(input [7:0] nk);
        case (nk)
            8'd130: ln2_nk = {32'hC2AEAC38, 32'hB93CBF94};   // n = -126
            8'd131: ln2_nk = {32'hC2AD4954, 32'hB93B4017};   // n = -125
            8'd132: ln2_nk = {32'hC2ABE670, 32'hB939C09A};   // n = -124
            8'd133: ln2_nk = {32'hC2AA838C, 32'hB938411C};   // n = -123
            8'd134: ln2_nk = {32'hC2A920A8, 32'hB936C19F};   // n = -122
            8'd135: ln2_nk = {32'hC2A7BDC4, 32'hB9354222};   // n = -121
            8'd136: ln2_nk = {32'hC2A65AE0, 32'hB933C2A5};   // n = -120
            8'd137: ln2_nk = {32'hC2A4F7FC, 32'hB9324328};   // n = -119
            8'd138: ln2_nk = {32'hC2A39518, 32'hB930C3AB};   // n = -118
            8'd139: ln2_nk = {32'hC2A23234, 32'hB92F442E};   // n = -117
            8'd140: ln2_nk = {32'hC2A0CF50, 32'hB92DC4B1};   // n = -116
            8'd141: ln2_nk = {32'hC29F6C6C, 32'hB92C4534};   // n = -115
            8'd142: ln2_nk = {32'hC29E0988, 32'hB92AC5B6};   // n = -114
            8'd143: ln2_nk = {32'hC29CA6A4, 32'hB9294639};   // n = -113
            8'd144: ln2_nk = {32'hC29B43C0, 32'hB927C6BC};   // n = -112
            8'd145: ln2_nk = {32'hC299E0DC, 32'hB926473F};   // n = -111
            8'd146: ln2_nk = {32'hC2987DF8, 32'hB924C7C2};   // n = -110
            8'd147: ln2_nk = {32'hC2971B14, 32'hB9234845};   // n = -109
            8'd148: ln2_nk = {32'hC295B830, 32'hB921C8C8};   // n = -108
            8'd149: ln2_nk = {32'hC294554C, 32'hB920494B};   // n = -107
            8'd150: ln2_nk = {32'hC292F268, 32'hB91EC9CE};   // n = -106
            8'd151: ln2_nk = {32'hC2918F84, 32'hB91D4A50};   // n = -105
            8'd152: ln2_nk = {32'hC2902CA0, 32'hB91BCAD3};   // n = -104
            8'd153: ln2_nk = {32'hC28EC9BC, 32'hB91A4B56};   // n = -103
            8'd154: ln2_nk = {32'hC28D66D8, 32'hB918CBD9};   // n = -102
            8'd155: ln2_nk = {32'hC28C03F4, 32'hB9174C5C};   // n = -101
            8'd156: ln2_nk = {32'hC28AA110, 32'hB915CCDF};   // n = -100
            8'd157: ln2_nk = {32'hC2893E2C, 32'hB9144D62};   // n = -99
            8'd158: ln2_nk = {32'hC287DB48, 32'hB912CDE5};   // n = -98
            8'd159: ln2_nk = {32'hC2867864, 32'hB9114E68};   // n = -97
            8'd160: ln2_nk = {32'hC2851580, 32'hB90FCEEA};   // n = -96
            8'd161: ln2_nk = {32'hC283B29C, 32'hB90E4F6D};   // n = -95
            8'd162: ln2_nk = {32'hC2824FB8, 32'hB90CCFF0};   // n = -94
            8'd163: ln2_nk = {32'hC280ECD4, 32'hB90B5073};   // n = -93
            8'd164: ln2_nk = {32'hC27F13E0, 32'hB909D0F6};   // n = -92
            8'd165: ln2_nk = {32'hC27C4E18, 32'hB9085179};   // n = -91
            8'd166: ln2_nk = {32'hC2798850, 32'hB906D1FC};   // n = -90
            8'd167: ln2_nk = {32'hC276C288, 32'hB905527F};   // n = -89
            8'd168: ln2_nk = {32'hC273FCC0, 32'hB903D302};   // n = -88
            8'd169: ln2_nk = {32'hC27136F8, 32'hB9025385};   // n = -87
            8'd170: ln2_nk = {32'hC26E7130, 32'hB900D407};   // n = -86
            8'd171: ln2_nk = {32'hC26BAB68, 32'hB8FEA915};   // n = -85
            8'd172: ln2_nk = {32'hC268E5A0, 32'hB8FBAA1A};   // n = -84
            8'd173: ln2_nk = {32'hC2661FD8, 32'hB8F8AB20};   // n = -83
            8'd174: ln2_nk = {32'hC2635A10, 32'hB8F5AC26};   // n = -82
            8'd175: ln2_nk = {32'hC2609448, 32'hB8F2AD2C};   // n = -81
            8'd176: ln2_nk = {32'hC25DCE80, 32'hB8EFAE32};   // n = -80
            8'd177: ln2_nk = {32'hC25B08B8, 32'hB8ECAF37};   // n = -79
            8'd178: ln2_nk = {32'hC25842F0, 32'hB8E9B03D};   // n = -78
            8'd179: ln2_nk = {32'hC2557D28, 32'hB8E6B143};   // n = -77
            8'd180: ln2_nk = {32'hC252B760, 32'hB8E3B249};   // n = -76
            8'd181: ln2_nk = {32'hC24FF198, 32'hB8E0B34E};   // n = -75
            8'd182: ln2_nk = {32'hC24D2BD0, 32'hB8DDB454};   // n = -74
            8'd183: ln2_nk = {32'hC24A6608, 32'hB8DAB55A};   // n = -73
            8'd184: ln2_nk = {32'hC247A040, 32'hB8D7B660};   // n = -72
            8'd185: ln2_nk = {32'hC244DA78, 32'hB8D4B766};   // n = -71
            8'd186: ln2_nk = {32'hC24214B0, 32'hB8D1B86B};   // n = -70
            8'd187: ln2_nk = {32'hC23F4EE8, 32'hB8CEB971};   // n = -69
            8'd188: ln2_nk = {32'hC23C8920, 32'hB8CBBA77};   // n = -68
            8'd189: ln2_nk = {32'hC239C358, 32'hB8C8BB7D};   // n = -67
            8'd190: ln2_nk = {32'hC236FD90, 32'hB8C5BC82};   // n = -66
            8'd191: ln2_nk = {32'hC23437C8, 32'hB8C2BD88};   // n = -65
            8'd192: ln2_nk = {32'hC2317200, 32'hB8BFBE8E};   // n = -64
            8'd193: ln2_nk = {32'hC22EAC38, 32'hB8BCBF94};   // n = -63
            8'd194: ln2_nk = {32'hC22BE670, 32'hB8B9C09A};   // n = -62
            8'd195: ln2_nk = {32'hC22920A8, 32'hB8B6C19F};   // n = -61
            8'd196: ln2_nk = {32'hC2265AE0, 32'hB8B3C2A5};   // n = -60
            8'd197: ln2_nk = {32'hC2239518, 32'hB8B0C3AB};   // n = -59
            8'd198: ln2_nk = {32'hC220CF50, 32'hB8ADC4B1};   // n = -58
            8'd199: ln2_nk = {32'hC21E0988, 32'hB8AAC5B6};   // n = -57
            8'd200: ln2_nk = {32'hC21B43C0, 32'hB8A7C6BC};   // n = -56
            8'd201: ln2_nk = {32'hC2187DF8, 32'hB8A4C7C2};   // n = -55
            8'd202: ln2_nk = {32'hC215B830, 32'hB8A1C8C8};   // n = -54
            8'd203: ln2_nk = {32'hC212F268, 32'hB89EC9CE};   // n = -53
            8'd204: ln2_nk = {32'hC2102CA0, 32'hB89BCAD3};   // n = -52
            8'd205: ln2_nk = {32'hC20D66D8, 32'hB898CBD9};   // n = -51
            8'd206: ln2_nk = {32'hC20AA110, 32'hB895CCDF};   // n = -50
            8'd207: ln2_nk = {32'hC207DB48, 32'hB892CDE5};   // n = -49
            8'd208: ln2_nk = {32'hC2051580, 32'hB88FCEEA};   // n = -48
            8'd209: ln2_nk = {32'hC2024FB8, 32'hB88CCFF0};   // n = -47
            8'd210: ln2_nk = {32'hC1FF13E0, 32'hB889D0F6};   // n = -46
            8'd211: ln2_nk = {32'hC1F98850, 32'hB886D1FC};   // n = -45
            8'd212: ln2_nk = {32'hC1F3FCC0, 32'hB883D302};   // n = -44
            8'd213: ln2_nk = {32'hC1EE7130, 32'hB880D407};   // n = -43
            8'd214: ln2_nk = {32'hC1E8E5A0, 32'hB87BAA1A};   // n = -42
            8'd215: ln2_nk = {32'hC1E35A10, 32'hB875AC26};   // n = -41
            8'd216: ln2_nk = {32'hC1DDCE80, 32'hB86FAE32};   // n = -40
            8'd217: ln2_nk = {32'hC1D842F0, 32'hB869B03D};   // n = -39
            8'd218: ln2_nk = {32'hC1D2B760, 32'hB863B249};   // n = -38
            8'd219: ln2_nk = {32'hC1CD2BD0, 32'hB85DB454};   // n = -37
            8'd220: ln2_nk = {32'hC1C7A040, 32'hB857B660};   // n = -36
            8'd221: ln2_nk = {32'hC1C214B0, 32'hB851B86B};   // n = -35
            8'd222: ln2_nk = {32'hC1BC8920, 32'hB84BBA77};   // n = -34
            8'd223: ln2_nk = {32'hC1B6FD90, 32'hB845BC82};   // n = -33
            8'd224: ln2_nk = {32'hC1B17200, 32'hB83FBE8E};   // n = -32
            8'd225: ln2_nk = {32'hC1ABE670, 32'hB839C09A};   // n = -31
            8'd226: ln2_nk = {32'hC1A65AE0, 32'hB833C2A5};   // n = -30
            8'd227: ln2_nk = {32'hC1A0CF50, 32'hB82DC4B1};   // n = -29
            8'd228: ln2_nk = {32'hC19B43C0, 32'hB827C6BC};   // n = -28
            8'd229: ln2_nk = {32'hC195B830, 32'hB821C8C8};   // n = -27
            8'd230: ln2_nk = {32'hC1902CA0, 32'hB81BCAD3};   // n = -26
            8'd231: ln2_nk = {32'hC18AA110, 32'hB815CCDF};   // n = -25
            8'd232: ln2_nk = {32'hC1851580, 32'hB80FCEEA};   // n = -24
            8'd233: ln2_nk = {32'hC17F13E0, 32'hB809D0F6};   // n = -23
            8'd234: ln2_nk = {32'hC173FCC0, 32'hB803D302};   // n = -22
            8'd235: ln2_nk = {32'hC168E5A0, 32'hB7FBAA1A};   // n = -21
            8'd236: ln2_nk = {32'hC15DCE80, 32'hB7EFAE32};   // n = -20
            8'd237: ln2_nk = {32'hC152B760, 32'hB7E3B249};   // n = -19
            8'd238: ln2_nk = {32'hC147A040, 32'hB7D7B660};   // n = -18
            8'd239: ln2_nk = {32'hC13C8920, 32'hB7CBBA77};   // n = -17
            8'd240: ln2_nk = {32'hC1317200, 32'hB7BFBE8E};   // n = -16
            8'd241: ln2_nk = {32'hC1265AE0, 32'hB7B3C2A5};   // n = -15
            8'd242: ln2_nk = {32'hC11B43C0, 32'hB7A7C6BC};   // n = -14
            8'd243: ln2_nk = {32'hC1102CA0, 32'hB79BCAD3};   // n = -13
            8'd244: ln2_nk = {32'hC1051580, 32'hB78FCEEA};   // n = -12
            8'd245: ln2_nk = {32'hC0F3FCC0, 32'hB783D302};   // n = -11
            8'd246: ln2_nk = {32'hC0DDCE80, 32'hB76FAE32};   // n = -10
            8'd247: ln2_nk = {32'hC0C7A040, 32'hB757B660};   // n = -9
            8'd248: ln2_nk = {32'hC0B17200, 32'hB73FBE8E};   // n = -8
            8'd249: ln2_nk = {32'hC09B43C0, 32'hB727C6BC};   // n = -7
            8'd250: ln2_nk = {32'hC0851580, 32'hB70FCEEA};   // n = -6
            8'd251: ln2_nk = {32'hC05DCE80, 32'hB6EFAE32};   // n = -5
            8'd252: ln2_nk = {32'hC0317200, 32'hB6BFBE8E};   // n = -4
            8'd253: ln2_nk = {32'hC0051580, 32'hB68FCEEA};   // n = -3
            8'd254: ln2_nk = {32'hBFB17200, 32'hB63FBE8E};   // n = -2
            8'd255: ln2_nk = {32'hBF317200, 32'hB5BFBE8E};   // n = -1
            8'd0  : ln2_nk = {32'h00000000, 32'h00000000};   // n = 0
            8'd1  : ln2_nk = {32'h3F317200, 32'h35BFBE8E};   // n = 1
            8'd2  : ln2_nk = {32'h3FB17200, 32'h363FBE8E};   // n = 2
            8'd3  : ln2_nk = {32'h40051580, 32'h368FCEEA};   // n = 3
            8'd4  : ln2_nk = {32'h40317200, 32'h36BFBE8E};   // n = 4
            8'd5  : ln2_nk = {32'h405DCE80, 32'h36EFAE32};   // n = 5
            8'd6  : ln2_nk = {32'h40851580, 32'h370FCEEA};   // n = 6
            8'd7  : ln2_nk = {32'h409B43C0, 32'h3727C6BC};   // n = 7
            8'd8  : ln2_nk = {32'h40B17200, 32'h373FBE8E};   // n = 8
            8'd9  : ln2_nk = {32'h40C7A040, 32'h3757B660};   // n = 9
            8'd10 : ln2_nk = {32'h40DDCE80, 32'h376FAE32};   // n = 10
            8'd11 : ln2_nk = {32'h40F3FCC0, 32'h3783D302};   // n = 11
            8'd12 : ln2_nk = {32'h41051580, 32'h378FCEEA};   // n = 12
            8'd13 : ln2_nk = {32'h41102CA0, 32'h379BCAD3};   // n = 13
            8'd14 : ln2_nk = {32'h411B43C0, 32'h37A7C6BC};   // n = 14
            8'd15 : ln2_nk = {32'h41265AE0, 32'h37B3C2A5};   // n = 15
            8'd16 : ln2_nk = {32'h41317200, 32'h37BFBE8E};   // n = 16
            8'd17 : ln2_nk = {32'h413C8920, 32'h37CBBA77};   // n = 17
            8'd18 : ln2_nk = {32'h4147A040, 32'h37D7B660};   // n = 18
            8'd19 : ln2_nk = {32'h4152B760, 32'h37E3B249};   // n = 19
            8'd20 : ln2_nk = {32'h415DCE80, 32'h37EFAE32};   // n = 20
            8'd21 : ln2_nk = {32'h4168E5A0, 32'h37FBAA1A};   // n = 21
            8'd22 : ln2_nk = {32'h4173FCC0, 32'h3803D302};   // n = 22
            8'd23 : ln2_nk = {32'h417F13E0, 32'h3809D0F6};   // n = 23
            8'd24 : ln2_nk = {32'h41851580, 32'h380FCEEA};   // n = 24
            8'd25 : ln2_nk = {32'h418AA110, 32'h3815CCDF};   // n = 25
            8'd26 : ln2_nk = {32'h41902CA0, 32'h381BCAD3};   // n = 26
            8'd27 : ln2_nk = {32'h4195B830, 32'h3821C8C8};   // n = 27
            8'd28 : ln2_nk = {32'h419B43C0, 32'h3827C6BC};   // n = 28
            8'd29 : ln2_nk = {32'h41A0CF50, 32'h382DC4B1};   // n = 29
            8'd30 : ln2_nk = {32'h41A65AE0, 32'h3833C2A5};   // n = 30
            8'd31 : ln2_nk = {32'h41ABE670, 32'h3839C09A};   // n = 31
            8'd32 : ln2_nk = {32'h41B17200, 32'h383FBE8E};   // n = 32
            8'd33 : ln2_nk = {32'h41B6FD90, 32'h3845BC82};   // n = 33
            8'd34 : ln2_nk = {32'h41BC8920, 32'h384BBA77};   // n = 34
            8'd35 : ln2_nk = {32'h41C214B0, 32'h3851B86B};   // n = 35
            8'd36 : ln2_nk = {32'h41C7A040, 32'h3857B660};   // n = 36
            8'd37 : ln2_nk = {32'h41CD2BD0, 32'h385DB454};   // n = 37
            8'd38 : ln2_nk = {32'h41D2B760, 32'h3863B249};   // n = 38
            8'd39 : ln2_nk = {32'h41D842F0, 32'h3869B03D};   // n = 39
            8'd40 : ln2_nk = {32'h41DDCE80, 32'h386FAE32};   // n = 40
            8'd41 : ln2_nk = {32'h41E35A10, 32'h3875AC26};   // n = 41
            8'd42 : ln2_nk = {32'h41E8E5A0, 32'h387BAA1A};   // n = 42
            8'd43 : ln2_nk = {32'h41EE7130, 32'h3880D407};   // n = 43
            8'd44 : ln2_nk = {32'h41F3FCC0, 32'h3883D302};   // n = 44
            8'd45 : ln2_nk = {32'h41F98850, 32'h3886D1FC};   // n = 45
            8'd46 : ln2_nk = {32'h41FF13E0, 32'h3889D0F6};   // n = 46
            8'd47 : ln2_nk = {32'h42024FB8, 32'h388CCFF0};   // n = 47
            8'd48 : ln2_nk = {32'h42051580, 32'h388FCEEA};   // n = 48
            8'd49 : ln2_nk = {32'h4207DB48, 32'h3892CDE5};   // n = 49
            8'd50 : ln2_nk = {32'h420AA110, 32'h3895CCDF};   // n = 50
            8'd51 : ln2_nk = {32'h420D66D8, 32'h3898CBD9};   // n = 51
            8'd52 : ln2_nk = {32'h42102CA0, 32'h389BCAD3};   // n = 52
            8'd53 : ln2_nk = {32'h4212F268, 32'h389EC9CE};   // n = 53
            8'd54 : ln2_nk = {32'h4215B830, 32'h38A1C8C8};   // n = 54
            8'd55 : ln2_nk = {32'h42187DF8, 32'h38A4C7C2};   // n = 55
            8'd56 : ln2_nk = {32'h421B43C0, 32'h38A7C6BC};   // n = 56
            8'd57 : ln2_nk = {32'h421E0988, 32'h38AAC5B6};   // n = 57
            8'd58 : ln2_nk = {32'h4220CF50, 32'h38ADC4B1};   // n = 58
            8'd59 : ln2_nk = {32'h42239518, 32'h38B0C3AB};   // n = 59
            8'd60 : ln2_nk = {32'h42265AE0, 32'h38B3C2A5};   // n = 60
            8'd61 : ln2_nk = {32'h422920A8, 32'h38B6C19F};   // n = 61
            8'd62 : ln2_nk = {32'h422BE670, 32'h38B9C09A};   // n = 62
            8'd63 : ln2_nk = {32'h422EAC38, 32'h38BCBF94};   // n = 63
            8'd64 : ln2_nk = {32'h42317200, 32'h38BFBE8E};   // n = 64
            8'd65 : ln2_nk = {32'h423437C8, 32'h38C2BD88};   // n = 65
            8'd66 : ln2_nk = {32'h4236FD90, 32'h38C5BC82};   // n = 66
            8'd67 : ln2_nk = {32'h4239C358, 32'h38C8BB7D};   // n = 67
            8'd68 : ln2_nk = {32'h423C8920, 32'h38CBBA77};   // n = 68
            8'd69 : ln2_nk = {32'h423F4EE8, 32'h38CEB971};   // n = 69
            8'd70 : ln2_nk = {32'h424214B0, 32'h38D1B86B};   // n = 70
            8'd71 : ln2_nk = {32'h4244DA78, 32'h38D4B766};   // n = 71
            8'd72 : ln2_nk = {32'h4247A040, 32'h38D7B660};   // n = 72
            8'd73 : ln2_nk = {32'h424A6608, 32'h38DAB55A};   // n = 73
            8'd74 : ln2_nk = {32'h424D2BD0, 32'h38DDB454};   // n = 74
            8'd75 : ln2_nk = {32'h424FF198, 32'h38E0B34E};   // n = 75
            8'd76 : ln2_nk = {32'h4252B760, 32'h38E3B249};   // n = 76
            8'd77 : ln2_nk = {32'h42557D28, 32'h38E6B143};   // n = 77
            8'd78 : ln2_nk = {32'h425842F0, 32'h38E9B03D};   // n = 78
            8'd79 : ln2_nk = {32'h425B08B8, 32'h38ECAF37};   // n = 79
            8'd80 : ln2_nk = {32'h425DCE80, 32'h38EFAE32};   // n = 80
            8'd81 : ln2_nk = {32'h42609448, 32'h38F2AD2C};   // n = 81
            8'd82 : ln2_nk = {32'h42635A10, 32'h38F5AC26};   // n = 82
            8'd83 : ln2_nk = {32'h42661FD8, 32'h38F8AB20};   // n = 83
            8'd84 : ln2_nk = {32'h4268E5A0, 32'h38FBAA1A};   // n = 84
            8'd85 : ln2_nk = {32'h426BAB68, 32'h38FEA915};   // n = 85
            8'd86 : ln2_nk = {32'h426E7130, 32'h3900D407};   // n = 86
            8'd87 : ln2_nk = {32'h427136F8, 32'h39025385};   // n = 87
            8'd88 : ln2_nk = {32'h4273FCC0, 32'h3903D302};   // n = 88
            8'd89 : ln2_nk = {32'h4276C288, 32'h3905527F};   // n = 89
            8'd90 : ln2_nk = {32'h42798850, 32'h3906D1FC};   // n = 90
            8'd91 : ln2_nk = {32'h427C4E18, 32'h39085179};   // n = 91
            8'd92 : ln2_nk = {32'h427F13E0, 32'h3909D0F6};   // n = 92
            8'd93 : ln2_nk = {32'h4280ECD4, 32'h390B5073};   // n = 93
            8'd94 : ln2_nk = {32'h42824FB8, 32'h390CCFF0};   // n = 94
            8'd95 : ln2_nk = {32'h4283B29C, 32'h390E4F6D};   // n = 95
            8'd96 : ln2_nk = {32'h42851580, 32'h390FCEEA};   // n = 96
            8'd97 : ln2_nk = {32'h42867864, 32'h39114E68};   // n = 97
            8'd98 : ln2_nk = {32'h4287DB48, 32'h3912CDE5};   // n = 98
            8'd99 : ln2_nk = {32'h42893E2C, 32'h39144D62};   // n = 99
            8'd100: ln2_nk = {32'h428AA110, 32'h3915CCDF};   // n = 100
            8'd101: ln2_nk = {32'h428C03F4, 32'h39174C5C};   // n = 101
            8'd102: ln2_nk = {32'h428D66D8, 32'h3918CBD9};   // n = 102
            8'd103: ln2_nk = {32'h428EC9BC, 32'h391A4B56};   // n = 103
            8'd104: ln2_nk = {32'h42902CA0, 32'h391BCAD3};   // n = 104
            8'd105: ln2_nk = {32'h42918F84, 32'h391D4A50};   // n = 105
            8'd106: ln2_nk = {32'h4292F268, 32'h391EC9CE};   // n = 106
            8'd107: ln2_nk = {32'h4294554C, 32'h3920494B};   // n = 107
            8'd108: ln2_nk = {32'h4295B830, 32'h3921C8C8};   // n = 108
            8'd109: ln2_nk = {32'h42971B14, 32'h39234845};   // n = 109
            8'd110: ln2_nk = {32'h42987DF8, 32'h3924C7C2};   // n = 110
            8'd111: ln2_nk = {32'h4299E0DC, 32'h3926473F};   // n = 111
            8'd112: ln2_nk = {32'h429B43C0, 32'h3927C6BC};   // n = 112
            8'd113: ln2_nk = {32'h429CA6A4, 32'h39294639};   // n = 113
            8'd114: ln2_nk = {32'h429E0988, 32'h392AC5B6};   // n = 114
            8'd115: ln2_nk = {32'h429F6C6C, 32'h392C4534};   // n = 115
            8'd116: ln2_nk = {32'h42A0CF50, 32'h392DC4B1};   // n = 116
            8'd117: ln2_nk = {32'h42A23234, 32'h392F442E};   // n = 117
            8'd118: ln2_nk = {32'h42A39518, 32'h3930C3AB};   // n = 118
            8'd119: ln2_nk = {32'h42A4F7FC, 32'h39324328};   // n = 119
            8'd120: ln2_nk = {32'h42A65AE0, 32'h3933C2A5};   // n = 120
            8'd121: ln2_nk = {32'h42A7BDC4, 32'h39354222};   // n = 121
            8'd122: ln2_nk = {32'h42A920A8, 32'h3936C19F};   // n = 122
            8'd123: ln2_nk = {32'h42AA838C, 32'h3938411C};   // n = 123
            8'd124: ln2_nk = {32'h42ABE670, 32'h3939C09A};   // n = 124
            8'd125: ln2_nk = {32'h42AD4954, 32'h393B4017};   // n = 125
            8'd126: ln2_nk = {32'h42AEAC38, 32'h393CBF94};   // n = 126
            8'd127: ln2_nk = {32'h42B00F1C, 32'h393E3F11};   // n = 127
            default: ln2_nk = 64'd0;
        endcase
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    // depth 1: clamp
    reg [31:0] xc;
    always @(posedge clk) begin
        if (!x[31] && x[30:0] > K_MAX[30:0]) xc <= K_MAX;
        else if (x[31] && x[30:0] > K_MINM[30:0]) xc <= {1'b1, K_MINM[30:0]};
        else xc <= x;
    end

    wire [31:0] t;
    wire [2:0] f;
    ot_hdc_qmul_lat #(LM) m_t (clk, rst_n, vd[1], xc, K_LOG2E, t, f[0]);   // 1 + LM

    // n = rint-to-even(t), |t| < 127.  With E = field - 127, the integer part
    // is the significand shifted right by 23 - E (E in [-1, 6]); below E = -1,
    // |t| < 1/2 and n = 0.
    wire [23:0] tm = {1'b1, t[22:0]};
    wire [7:0]  te = t[30:23];
    wire [4:0]  tsh = 5'd23 - (te[4:0] - 5'd31);      // 23 - E, as te - 127 = te[4:0] - 31 (mod 32)
    wire [23:0] tip = tm >> tsh;
    wire [4:0]  trb = tsh - 5'd1;
    wire        thalf = tm[trb];
    wire        tstk = |(tm & ~({24{1'b1}} << trb));
    wire [7:0]  tmag = (te < 8'd126) ? 8'd0 : (tip[7:0] + {7'd0, thalf && (tstk || tip[0])});
    reg  [8:0]  nint;
    always @(posedge clk) nint <= t[31] ? -{1'b0, tmag} : {1'b0, tmag};

    reg [31:0] a_hi, a_lo;
    always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);

    wire [31:0] r1, r, xc_d, lo_d;
    ot_hdc_delay #(.W(32), .D(T_K - 1)) d_x (clk, rst_n, xc, xc_d);
    ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r1 (clk, rst_n, vd[T_K], xc_d, {~a_hi[31], a_hi[30:0]}, r1, f[1]);
    ot_hdc_delay #(.W(32), .D(LA)) d_lo (clk, rst_n, a_lo, lo_d);
    ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_r  (clk, rst_n, vd[T_R1], r1, {~lo_d[31], lo_d[30:0]}, r, f[2]);

    // Horner: p = C0; six times p = p*r + C[k]; r travels in (LM+LA)-cycle hops.
    wire [31:0] rd [0:6];
    wire [31:0] pm [1:6];
    wire [31:0] pa [0:6];
    wire [12:1] hf;
    assign rd[0] = r;
    assign pa[0] = poly(0);
    genvar k;
    generate
        for (k = 1; k <= 6; k = k + 1) begin : g_h
            if (k < 6) begin : g_rd
                ot_hdc_delay #(.W(32), .D(LM + LA)) d_r (clk, rst_n, rd[k-1], rd[k]);
            end
            ot_hdc_qmul_lat #(LM) u_m (clk, rst_n, vd[T_R + (LM + LA)*(k-1)], pa[k-1], rd[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_R + (LM + LA)*(k-1) + LM], pm[k], poly(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [8:0] nint_d;
    ot_hdc_delay #(.W(9), .D(T_P - T_N)) d_n (clk, rst_n, nint, nint_d);
    // 2^n into the exponent field (a keep-prefix add in the serial-domain build, LM != 3)
    wire [31:0] y_n;
    wire        unused_cy;
    ot_hdc_kadd #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_yn (.a(pa[6]), .b({{14{nint_d[8]}}, nint_d, 23'd0}), .cin(1'b0),
                                                      .s(y_n), .cout(unused_cy));
    always @(posedge clk) y <= y_n;

    assign fault = |{f, hf};
endmodule

// 1/sqrt(v): seed 0x5f3759df - (bits >> 1), three steps y*(1.5 - half*(y*y)).
module ot_hdc_v41x_rsqrt #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat)
    parameter integer LA = 3                    // add latency (ot_hdc_qadd_lat: 3, or 4 input cut)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    localparam integer IT = 3 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;      // 37 (LM 3), 46 (LM 4)
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0;
    wire [31:0] y0_n;
    wire        unused_cy;
    ot_hdc_kadd #(.W(32), .K((LM != 3 || LA != 3) ? 1 : 0)) u_y0 (.a(32'h5F3759DF), .b(~{1'b0, x[31:1]}), .cin(1'b1), .s(y0_n),
                                                      .cout(unused_cy));
    always @(posedge clk) y0 <= y0_n;
    wire [31:0] half;
    wire [31:0] hd [0:2];
    wire [31:0] yi [0:3];
    wire [31:0] yy [0:2];
    wire [31:0] hm [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [12:0] f;
    ot_hdc_qmul_lat #(LM) m_half (clk, rst_n, v, x, 32'h3F000000, half, f[12]);   // LM
    ot_hdc_delay #(.W(32), .D(1)) d_h0 (clk, rst_n, half, hd[0]);       // 1 + LM
    assign yi[0] = y0;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_h
                ot_hdc_delay #(.W(32), .D(IT)) d_h (clk, rst_n, hd[k], hd[k+1]);
            end
            ot_hdc_qmul_lat #(LM) m_yy (clk, rst_n, vd[1 + IT*k],             yi[k], yi[k], yy[k], f[4*k]);
            ot_hdc_qmul_lat #(LM) m_hm (clk, rst_n, vd[1 + IT*k + LM],        hd[k], yy[k], hm[k], f[4*k+1]);
            ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_s  (clk, rst_n, vd[1 + IT*k + 2*LM],      32'h3FC00000, {~hm[k][31], hm[k][30:0]}, s[k], f[4*k+2]);
            ot_hdc_delay #(.W(32), .D(2*LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_hdc_qmul_lat #(LM) m_y  (clk, rst_n, vd[1 + IT*k + 2*LM + LA], yd[k], s[k], yi[k+1], f[4*k+3]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule

// ---------------------------------------------------------------------------
// Correctly rounded binary32 DIVISION: II 1, fixed DEPTH 19.
//
// The function, the operand decode, the finish and the fault convention are
// those of rtl/hdc/v41/ot_hdc_fdiv.sv, transcribed unchanged:
//   y = RN_even(a / b), gradual underflow, every zero result +0; a nonfinite
//   operand, a zero divisor or an overflowing quotient fails closed
//   (fault, y = +0).
// What changes is the recurrence.  It forms the same 27 quotient bits and the
// same final remainder, but TWO bits per register stage.  A stage takes x = 4R
// (2 ma in the first stage), with R < mb the running remainder, so x < 4 mb.
// It forms x - mb, x - 2 mb and x - 3 mb in parallel, and the digit
// q = floor(x / mb) in [0, 3] is the largest with a non-negative difference.
// That is one subtract and a select, not two subtracts in series: the routed
// SFU lane measured two serial restoring steps at 907 MHz.  3 mb is formed
// once, in a stage after the decode.  The last stage forms one bit.  A
// correctly rounded quotient is unique, so the result is the same bit for bit.
// Stages: 1 decode, 1 (3 mb), 14 recurrence, 3 finish.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_fdiv (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire        vo,
    output reg         fault
);
    localparam integer QB = 27;
    localparam integer NS = (QB + 1) / 2;      // 14
    localparam integer DEPTH = 2 + NS + 3;     // 19

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    function automatic [33:0] norm;   // {sig[23:0], exponent[9:0] signed, unbiased of sig * 2^-23}
        input [7:0]  e;
        input [22:0] f;
        integer i;
        reg [4:0] p;
        begin
            if (e != 8'd0) norm = {1'b1, f, e - 10'sd127};
            else begin
                p = 5'd0;
                for (i = 0; i < 23; i = i + 1) if (f[i]) p = i[4:0];
                norm = {({1'b0, f} << (5'd23 - p)), $signed({5'd0, p}) - 10'sd149};
            end
        end
    endfunction
    wire [33:0] na = norm(a[30:23], a[22:0]);
    wire [33:0] nb = norm(b[30:23], b[22:0]);

    reg        d_sign, d_zero, d_bad;
    reg [23:0] d_ma, d_mb;
    reg signed [10:0] d_e;
    always @(posedge clk) begin
        d_sign <= a[31] ^ b[31];
        d_zero <= (a[30:0] == 31'd0);
        d_bad  <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF) || (b[30:0] == 31'd0);
        d_ma   <= na[33:10];
        d_mb   <= nb[33:10];
        d_e    <= $signed({na[9], na[9:0]}) - $signed({nb[9], nb[9:0]});
    end

    // 3 mb, once (hbm-fmax-su: a keep-prefix add)
    wire [25:0] mb3_w;
    wire        mb3_co;
    ot_hdc_ksadd_k #(.W(26)) u_mb3 (.a({2'b0, d_mb}), .b({1'b0, d_mb, 1'b0}), .cin(1'b0), .s(mb3_w), .cout(mb3_co));
    reg        e_sign, e_zero, e_bad;
    reg [23:0] e_ma, e_mb;
    reg [25:0] e_mb3;
    reg signed [10:0] e_e;
    always @(posedge clk) begin
        e_sign <= d_sign; e_zero <= d_zero; e_bad <= d_bad; e_e <= d_e;
        e_ma <= d_ma; e_mb <= d_mb; e_mb3 <= mb3_w;
    end

    reg [24:0]        r_rem  [0:NS-1];
    reg [QB-1:0]      r_q    [0:NS-1];
    reg [23:0]        r_mb   [0:NS-1];
    reg [25:0]        r_mb3  [0:NS-1];
    reg               r_sign [0:NS-1];
    reg               r_zero [0:NS-1];
    reg               r_bad  [0:NS-1];
    reg signed [10:0] r_e    [0:NS-1];

    genvar j;
    generate
        for (j = 0; j < NS; j = j + 1) begin : g_rec
            // quotient bits 2j and 2j+1 (bit 2^-k is restoring step k); stage NS-1 forms one bit
            localparam integer TWO = (2 * j + 1 < QB);
            wire [23:0]   mb  = (j == 0) ? e_mb : r_mb[j-1];
            wire [25:0]   mb3 = (j == 0) ? e_mb3 : r_mb3[j-1];
            wire [QB-1:0] qin = (j == 0) ? {QB{1'b0}} : r_q[j-1];
            wire [26:0]   x   = (j == 0) ? {2'b0, e_ma, 1'b0} :
                                TWO ? {r_rem[j-1][24:0], 2'b0} : {1'b0, r_rem[j-1][24:0], 1'b0};
            // hbm-fmax-su: the three trial subtractions as keep-prefix adders (behavioural, 177 ps over 0.833 ns at SS)
            wire [27:0]   d1, d2, d3;
            wire [2:0]    unused_dc;
            ot_hdc_ksadd_k #(.W(28)) u_d1 (.a({1'b0, x}), .b(~{4'b0, mb}), .cin(1'b1), .s(d1), .cout(unused_dc[0]));
            ot_hdc_ksadd_k #(.W(28)) u_d2 (.a({1'b0, x}), .b(~{3'b0, mb, 1'b0}), .cin(1'b1), .s(d2), .cout(unused_dc[1]));
            ot_hdc_ksadd_k #(.W(28)) u_d3 (.a({1'b0, x}), .b(~{2'b0, mb3}), .cin(1'b1), .s(d3), .cout(unused_dc[2]));
            wire [1:0]    q  = !d3[27] ? 2'd3 : !d2[27] ? 2'd2 : !d1[27] ? 2'd1 : 2'd0;
            wire [26:0]   r  = !d3[27] ? d3[26:0] : !d2[27] ? d2[26:0] : !d1[27] ? d1[26:0] : x;
            always @(posedge clk) begin
                r_rem[j]  <= r[24:0];
                r_q[j]    <= TWO ? {qin[QB-3:0], q} : {qin[QB-2:0], q[0]};
                r_mb[j]   <= mb;
                r_mb3[j]  <= mb3;
                r_sign[j] <= (j == 0) ? e_sign : r_sign[j-1];
                r_zero[j] <= (j == 0) ? e_zero : r_zero[j-1];
                r_bad[j]  <= (j == 0) ? e_bad  : r_bad[j-1];
                r_e[j]    <= (j == 0) ? e_e    : r_e[j-1];
            end
        end
    endgenerate

    // ---- finish 1: leading bit, significand, guard, sticky, biased exponent ----
    wire [QB-1:0] q = r_q[NS-1];
    reg        f1_sign, f1_zero, f1_bad, f1_g, f1_st;
    reg [23:0] f1_sig;
    reg signed [10:0] f1_be;
    always @(posedge clk) begin
        f1_sign <= r_sign[NS-1];
        f1_zero <= r_zero[NS-1];
        f1_bad  <= r_bad[NS-1];
        if (q[26]) begin
            f1_sig <= q[26:3]; f1_g <= q[2]; f1_st <= (|q[1:0]) || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd127;
        end else begin
            f1_sig <= q[25:2]; f1_g <= q[1]; f1_st <= q[0] || (|r_rem[NS-1]);
            f1_be  <= r_e[NS-1] + 11'sd126;
        end
    end

    // ---- finish 2: denormalise a subnormal result -------------------------------
    wire        f1_sub = (f1_be < 11'sd1);
    wire [10:0] sh_full = 11'sd1 - f1_be;
    wire [4:0]  sh = (sh_full > 11'd25) ? 5'd25 : sh_full[4:0];
    wire [24:0] ext = {f1_sig, f1_g};
    wire [24:0] ext_sh = ext >> sh;
    wire [24:0] lost_mask = ~({25{1'b1}} << sh);      // hbm-fmax-su: (1 << sh) - 1 without the subtract
    reg        f2_sign, f2_zero, f2_bad, f2_ovf, f2_g, f2_st;
    reg [23:0] f2_sig;
    reg [7:0]  f2_field;
    always @(posedge clk) begin
        f2_sign <= f1_sign;
        f2_zero <= f1_zero;
        f2_bad  <= f1_bad;
        f2_ovf  <= (f1_be > 11'sd254);
        if (f1_sub) begin
            f2_sig <= ext_sh[24:1]; f2_g <= ext_sh[0];
            f2_st <= f1_st || (|(ext & lost_mask));
            f2_field <= 8'd0;
        end else begin
            f2_sig <= f1_sig; f2_g <= f1_g; f2_st <= f1_st;
            f2_field <= f1_be[7:0];
        end
    end

    // ---- finish 3: round to nearest even, encode ----------------------------------
    wire        rup = f2_g && (f2_st || f2_sig[0]);
    // hbm-fmax-su: the rounding increment as a keep-prefix incrementer (the behavioural add re-rippled: 233 ps over
    // 0.833 ns at SS); the same sum
    wire [30:0] code;
    wire        code_co;
    ot_hdc_inc_k #(.W(31)) u_rinc (.a({f2_field, f2_sig[22:0]}), .inc(rup), .y(code), .co(code_co));
    wire        ovf = f2_ovf || (code[30:23] == 8'hFF);
    always @(posedge clk) begin
        if (f2_bad || (ovf && !f2_zero)) begin y <= 32'd0; fault <= vd[DEPTH-1]; end
        else if (f2_zero || code == 31'd0) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= {f2_sign, code}; fault <= 1'b0; end
    end
endmodule

// ---------------------------------------------------------------------------
// softplus(x) and sqrt(softplus(x)): II 1, fixed DEPTH 162.  The operation order
// of rtl/hdc/v41/ot_hdc_softplus.sv (tools/hdc_golden_v41.softplus, .sqrt), on
// the fast units:
//     t = exp(-|x|)            49     ot_hdc_v41x_exp
//     u = t / (t + 2)          3 + 19 ot_hdc_qadd, ot_hdc_v41x_fdiv
//     u2 = u * u               3
//     p = 1/17; p = p*u2 + 1/(2i+1), i = 7 .. 0      8 x (3 + 3)
//     l = (u * p) * 2          3 + 3
//     sp = max(x, 0) + l       3
//     r = sqrt(sp)             31     ot_hdc_fsqrt
// The fault convention is ot_hdc_softplus's.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_softplus #(
    parameter integer LM = 3,                   // multiplier latency (ot_hdc_qmul_lat)
    parameter integer LA = 3,                   // add latency (ot_hdc_qadd_lat: 3, or 4 input cut)
    parameter integer DDIV = 19,                // c12: 21 = ot_dsrom_fdiv_f12
    parameter integer FSQ = 0                   // c12: 1 = ot_hdc_fsqrt_c12
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] sp,
    output wire [31:0] r,
    output wire        vo,
    output wire        fault
);
    localparam integer T_EXP  = 7 * LM + 8 * LA + 4;   // ot_hdc_v41x_exp DEPTH
    localparam integer T_DEN  = T_EXP + LA;
    localparam integer T_U    = T_DEN + DDIV;
    localparam integer T_U2   = T_U + LM;
    localparam integer T_P    = T_U2 + 8 * (LM + LA);
    localparam integer T_UP   = T_P + LM;
    localparam integer T_L    = T_UP + LM;
    localparam integer T_SP   = T_L + LA;
    localparam integer DEPTH  = T_SP + 31;       // 162 (LM 3), 180 (LM 4)
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i);
        coef = C[32*(8-i) +: 32];
    endfunction

    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    wire [31:0] t, den, t_d, u, u2, lp, l;
    wire f_exp, f_den, f_div, f_u2, f_up, f_l, f_sp, f_sq;
    ot_hdc_v41x_exp #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rst_n), .v(v), .x({1'b1, x[30:0]}), .y(t), .vo(), .fault(f_exp));
    ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_den (clk, rst_n, vd[T_EXP], t, 32'h40000000, den, f_den);
    ot_hdc_delay #(.W(32), .D(LA)) d_t (clk, rst_n, t, t_d);
    generate if (DDIV == 31) begin : g_d31
        ot_hdc_fdiv    u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end else if (DDIV == 21) begin : g_d21
        ot_dsrom_fdiv_f12 u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end else begin : g_d19
        ot_hdc_v41x_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_DEN]), .a(t_d), .b(den), .y(u), .vo(), .fault(f_div));
    end endgenerate
    ot_hdc_qmul_lat #(LM) m_u2 (clk, rst_n, vd[T_U], u, u, u2, f_u2);

    wire [31:0] u2d [0:7];
    wire [31:0] pm  [1:8];
    wire [31:0] pa  [0:8];
    wire [16:1] hf;
    assign u2d[0] = u2;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay #(.W(32), .D(LM + LA)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_qmul_lat #(LM) u_m (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1)], pa[k-1], u2d[k-1], pm[k], hf[2*k-1]);
            ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) u_a (clk, rst_n, vd[T_U2 + (LM + LA)*(k-1) + LM], pm[k], coef(k), pa[k], hf[2*k]);
        end
    endgenerate

    wire [31:0] u_d;
    ot_hdc_delay #(.W(32), .D(T_P - T_U)) d_u (clk, rst_n, u, u_d);
    ot_hdc_qmul_lat #(LM) m_up (clk, rst_n, vd[T_P], u_d, pa[8], lp, f_up);
    ot_hdc_qmul_lat #(LM) m_l  (clk, rst_n, vd[T_UP], lp, 32'h40000000, l, f_l);

    reg  [31:0] mx;
    wire [31:0] mx_d, spv;
    wire x_nan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    always @(posedge clk) mx <= (x[31] && !x_nan) ? 32'd0 : x;
    ot_hdc_delay #(.W(32), .D(T_L - 1)) d_mx (clk, rst_n, mx, mx_d);
    ot_hdc_qadd_lat #(.KEEP((LM != 3 || LA != 3) ? 1 : 0), .LAT(LA)) a_sp (clk, rst_n, vd[T_L], mx_d, l, spv, f_sp);

    generate if (FSQ != 0) begin : g_sq12
        ot_hdc_fsqrt_c12 u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    end else begin : g_sq
        ot_hdc_fsqrt u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP]), .a(spv), .y(r), .vo(), .fault(f_sq));
    end endgenerate
    ot_hdc_delay #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);

    wire f_sp_d;
    ot_hdc_delay #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    assign fault = f_sp_d | f_sq | f_exp | f_den | f_div | f_u2 | (|hf) | f_up | f_l;
endmodule

// ---------------------------------------------------------------------------
// Insertion delay line: an item entering with depth choice k leaves exactly
// DEPTHS[k] cycles later (0 = a wire), all items through ONE exit.  It is a
// shift register toward the exit whose stage DEPTHS[k] also loads new items.
// Items keep their order only if every item leaves after the one before it;
// the controller guarantees that (ot_hdc_v41x_vec: the checkpoint rule).  A
// stage that is loaded while an item shifts into it raises `coll`.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_ins #(
    parameter integer W = 32,
    parameter integer K = 2,                 // depth choices
    parameter [16*K-1:0] DEPTHS = {16'd3, 16'd0},   // choice k = DEPTHS[16k +: 16]
    parameter integer DMAX = 3,              // max over DEPTHS
    parameter integer RESET_DATA = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice
    input  wire [W-1:0] d,
    output wire         vo,
    output wire [W-1:0] q,
    output wire         coll,
    output wire         busy                 // an item is in the line
);
    function automatic has(input integer p, input [K-1:0] s);
        integer k;
        begin
            has = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p && s[k]) has = 1'b1;
        end
    endfunction
    function automatic canbe(input integer p);
        integer k;
        begin
            canbe = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p) canbe = 1'b1;
        end
    endfunction
    generate
        if (DMAX == 0) begin : g_wire
            assign vo = v; assign q = d; assign coll = 1'b0; assign busy = 1'b0;
        end else begin : g_line
            reg [W-1:0] r  [1:DMAX];
            reg         rv [1:DMAX];
            wire [DMAX+1:1] cl;
            assign cl[DMAX+1] = 1'b0;
            genvar p;
            for (p = 1; p <= DMAX; p = p + 1) begin : g_s
                wire [W-1:0] nx  = (p == DMAX) ? {W{1'b0}} : r[(p == DMAX) ? p : p + 1];
                wire         nxv = (p == DMAX) ? 1'b0 : rv[(p == DMAX) ? p : p + 1];
                if (canbe(p)) begin : g_ld
                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= ld || nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= ld ? d : nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= ld ? d : nx;
                    end
                end else begin : g_sh
                    assign cl[p] = 1'b0;
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= nx;
                    end else begin : g_nd
                        always @(posedge clk) r[p] <= nx;
                    end
                end
            end
            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];
            assign coll = (|cl) || (now && rv[1]);
            reg any;
            integer b;
            always @(*) begin
                any = 1'b0;
                for (b = 1; b <= DMAX; b = b + 1) any = any | rv[b];
            end
            assign busy = any;
        end
    endgenerate
endmodule
