`timescale 1ns/1ps
// Opt-in typed510-bit bridge packet codec. Caller reserves space before each i_v.
// No clock crossing, transaction ownership, epoch fence or mutable-state protection here.
module ot_qwen_kvc_packet_encode_parallel #(parameter integer ENABLE=0)(
    input wire clk,rst_n,i_v,
    input wire [3:0] i_op,
    input wire [7:0] i_epoch,
    input wire [6:0] i_pc,
    input wire [15:0] i_seq,
    input wire [8:0] i_tag,
    input wire [23:0] i_sec,
    input wire [255:0] i_data,
    output reg o_v,o_bad,
    output reg [509:0] o_packet
);
    function automatic [31:0] crc32(input [477:0] body);
        begin
            crc32[0] = ^(body & 478'h315364171036014d53b1d3dc25534ce23b6ee187e962dfd5c8b6332a9108245d01578ee7d4c01ec658a183d1e8f6c5afc0be831eb4e5b025f7011641) ^ 1'b1;
            crc32[1] = ^(body & 478'h13f5ac39305a03d7f4d274646ff5d5264db322883ba7607e59da557fb3186ce703f893287d40234ae9e28472391b4ef041c38523dd2ed06e19033ac3) ^ 1'b0;
            crc32[2] = ^(body & 478'h16b83c65708206e2ba153b14fab8e6aea008a4979e2c1f297b0299d5f738fd9306a6a8b72e4058538b648b359ac0584f433989590eb810f9c50763c7) ^ 1'b1;
            crc32[3] = ^(body & 478'h2d7078cae1040dc5742a7629f571cd5d4011492f3c583e52f60533abee71fb260d4d516e5c80b0a716c9166b3580b09e867312b21d7021f38a0ec78e) ^ 1'b0;
            crc32[4] = ^(body & 478'h2bb39582d23e1ac7bbe53f8fcfb0d658bb4c73d991d2a37024bc547d4debd2111bcd2c3b6dc17f887533af0783f7a492cc58a67a8e05f3c2e31c995d) ^ 1'b0;
            crc32[5] = ^(body & 478'h26344f12b44a34c2247bacc3ba32e0534df60634cac7993581ce9bd00adf807f36cdd6910f42e1d6b2c6dddeef198c8a580fcfeba8ee57a0313824fb) ^ 1'b1;
            crc32[6] = ^(body & 478'h0c689e256894698448f759877465c0a69bec0c69958f326b039d37a015bf00fe6d9bad221e85c3ad658dbbbdde331914b01f9fd751dcaf40627049f6) ^ 1'b1;
            crc32[7] = ^(body & 478'h2982585dc11ed245c25f60d2cd98cdaf0cb6f954c27cbb03cf8c5c6aba7625a1da60d4a3e9cb999c93baf4aa5490f786a081bcb0175ceea533e185ad) ^ 1'b0;
            crc32[8] = ^(body & 478'h2257d4ac920ba5c6d70f1279be62d7bc2203132e6d9ba9d257ae8bffe5e46f1eb59627a007572dff7fd46a8541d72aa281bdfa7e9a5c6d6f90c21d1b) ^ 1'b1;
            crc32[9] = ^(body & 478'h04afa95924174b8dae1e24f37cc5af784406265cdb3753a4af5d17ffcbc8de3d6b2c4f400eae5bfeffa8d50a83ae5545037bf4fd34b8dadf21843a36) ^ 1'b0;
            crc32[10] = ^(body & 478'h380c36a5581896560f8d9a3adcd81212b362ad3e5f0c789c960c1cd506999827d70f1067c99ca93ba7f029c4efaa6f25c6496ae4dd94059bb409622d) ^ 1'b1;
            crc32[11] = ^(body & 478'h014b095da0072de14caae7a99ce368c75dabbbfb577a2eece4ae0a809c3b1412af49ae2847f94cb11741d05837a21be44c2c56d70fcdbb129f13d21b) ^ 1'b0;
            crc32[12] = ^(body & 478'h33c576ac50385a8fcae41c8f1c959d6c803996714796820c01ea262ba97e0c785fc4d2b75b3287a47622236187b2f26758e62eb0ab7ec600c926b277) ^ 1'b1;
            crc32[13] = ^(body & 478'h278aed58a070b51f95c8391e392b3ad900732ce28f2d041803d44c5752fc18f0bf89a56eb6650f48ec4446c30f65e4ceb1cc5d6156fd8c01924d64ee) ^ 1'b0;
            crc32[14] = ^(body & 478'h0f15dab140e16a3f2b90723c725675b200e659c51e5a083007a898aea5f831e17f134add6cca1e91d8888d861ecbc99d6398bac2adfb1803249ac9dc) ^ 1'b0;
            crc32[15] = ^(body & 478'h1e2bb56281c2d47e5720e478e4aceb6401ccb38a3cb410600f51315d4bf063c2fe2695bad9943d23b1111b0c3d97933ac73175855bf63006493593b8) ^ 1'b0;
            crc32[16] = ^(body & 478'h0d040ed213b3a9b1fdf01b2dec0a9a2a38f78693900aff15d614519006e8e3d8fd1aa59267e864813a83b5c993d9e3da4edc68140309d029656a3131) ^ 1'b0;
            crc32[17] = ^(body & 478'h1a081da427675363fbe0365bd815345471ef0d272015fe2bac28a3200dd1c7b1fa354b24cfd0c90275076b9327b3c7b49db8d0280613a052cad46262) ^ 1'b0;
            crc32[18] = ^(body & 478'h34103b484ecea6c7f7c06cb7b02a68a8e3de1a4e402bfc57585146401ba38f63f46a96499fa19204ea0ed7264f678f693b71a0500c2740a595a8c4c4) ^ 1'b1;
            crc32[19] = ^(body & 478'h282076909d9d4d8fef80d96f6054d151c7bc349c8057f8aeb0a28c8037471ec7e8d52c933f432409d41dae4c9ecf1ed276e340a0184e814b2b518988) ^ 1'b0;
            crc32[20] = ^(body & 478'h1040ed213b3a9b1fdf01b2dec0a9a2a38f78693900aff15d614519006e8e3d8fd1aa59267e864813a83b5c993d9e3da4edc68140309d029656a31310) ^ 1'b1;
            crc32[21] = ^(body & 478'h2081da427675363fbe0365bd815345471ef0d272015fe2bac28a3200dd1c7b1fa354b24cfd0c90275076b9327b3c7b49db8d0280613a052cad462620) ^ 1'b0;
            crc32[22] = ^(body & 478'h3050d093fcdc6d322fb718a727f5c66c068f4563ebdd1aa04da2572b2b30d26247feea7e2ed93e88f84cf1b51e8e333c77a4861e7691ba7cad8d5a01) ^ 1'b0;
            crc32[23] = ^(body & 478'h11f2c530e98edb290cdfe2926ab8c03a36706b403ed8ea9553f29d7cc76980998eaa5a1b897263d7a83860bbd5eaa3d72ff78f2259c6c4dcac1ba243) ^ 1'b0;
            crc32[24] = ^(body & 478'h23e58a61d31db65219bfc524d57180746ce0d6807db1d52aa7e53af98ed301331d54b43712e4c7af5070c177abd547ae5fef1e44b38d89b958374486) ^ 1'b1;
            crc32[25] = ^(body & 478'h07cb14c3a63b6ca4337f8a49aae300e8d9c1ad00fb63aa554fca75f31da602663aa9686e25c98f5ea0e182ef57aa8f5cbfde3c89671b1372b06e890c) ^ 1'b0;
            crc32[26] = ^(body & 478'h3ec54d905c40d805354ec74f70954d3388edbb861fa58b7f5722d8ccaa44209174055e3b9f53007b1962860f47a3db16bf02fa0c7ad396c097dc0459) ^ 1'b1;
            crc32[27] = ^(body & 478'h3d8a9b20b881b00a6a9d8e9ee12a9a6711db770c3f4b16feae45b19954884122e80abc773ea600f632c50c1e8f47b62d7e05f418f5a72d812fb808b2) ^ 1'b0;
            crc32[28] = ^(body & 478'h3b15364171036014d53b1d3dc25534ce23b6ee187e962dfd5c8b6332a9108245d01578ee7d4c01ec658a183d1e8f6c5afc0be831eb4e5b025f701164) ^ 1'b0;
            crc32[29] = ^(body & 478'h362a6c82e206c029aa763a7b84aa699c476ddc30fd2c5bfab916c6655221048ba02af1dcfa9803d8cb14307a3d1ed8b5f817d063d69cb604bee022c8) ^ 1'b0;
            crc32[30] = ^(body & 478'h2c54d905c40d805354ec74f70954d3388edbb861fa58b7f5722d8ccaa44209174055e3b9f53007b1962860f47a3db16bf02fa0c7ad396c097dc04590) ^ 1'b0;
            crc32[31] = ^(body & 478'h18a9b20b881b00a6a9d8e9ee12a9a6711db770c3f4b16feae45b19954884122e80abc773ea600f632c50c1e8f47b62d7e05f418f5a72d812fb808b20) ^ 1'b1;
        end
    endfunction
    wire [477:0] body={4'd1,i_op,i_epoch,i_pc,i_seq,i_tag,i_sec,i_data,150'd0};
    wire legal=(i_op==4'd1) || ((i_op==4'd2) && (i_sec==0) && (i_data==0));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin o_v<=0; o_bad<=0; end
        else begin
            o_v<=(ENABLE!=0) && i_v && legal;
            o_bad<=(ENABLE!=0) && i_v && !legal;
        end
    end
    always @(posedge clk) begin
        if(ENABLE!=0) o_packet<={body,crc32(body)};
        else o_packet<=510'd0;
    end
endmodule

module ot_qwen_kvc_packet_decode_parallel #(parameter integer ENABLE=0)(
    input wire clk,rst_n,i_v,
    input wire [509:0] i_packet,
    output reg o_v,o_bad,
    output reg [509:0] o_packet,
    output wire [3:0] o_op,
    output wire [7:0] o_epoch,
    output wire [6:0] o_pc,
    output wire [15:0] o_seq,
    output wire [8:0] o_tag,
    output wire [23:0] o_sec,
    output wire [255:0] o_data
);
    function automatic [31:0] crc32(input [477:0] body);
        begin
            crc32[0] = ^(body & 478'h315364171036014d53b1d3dc25534ce23b6ee187e962dfd5c8b6332a9108245d01578ee7d4c01ec658a183d1e8f6c5afc0be831eb4e5b025f7011641) ^ 1'b1;
            crc32[1] = ^(body & 478'h13f5ac39305a03d7f4d274646ff5d5264db322883ba7607e59da557fb3186ce703f893287d40234ae9e28472391b4ef041c38523dd2ed06e19033ac3) ^ 1'b0;
            crc32[2] = ^(body & 478'h16b83c65708206e2ba153b14fab8e6aea008a4979e2c1f297b0299d5f738fd9306a6a8b72e4058538b648b359ac0584f433989590eb810f9c50763c7) ^ 1'b1;
            crc32[3] = ^(body & 478'h2d7078cae1040dc5742a7629f571cd5d4011492f3c583e52f60533abee71fb260d4d516e5c80b0a716c9166b3580b09e867312b21d7021f38a0ec78e) ^ 1'b0;
            crc32[4] = ^(body & 478'h2bb39582d23e1ac7bbe53f8fcfb0d658bb4c73d991d2a37024bc547d4debd2111bcd2c3b6dc17f887533af0783f7a492cc58a67a8e05f3c2e31c995d) ^ 1'b0;
            crc32[5] = ^(body & 478'h26344f12b44a34c2247bacc3ba32e0534df60634cac7993581ce9bd00adf807f36cdd6910f42e1d6b2c6dddeef198c8a580fcfeba8ee57a0313824fb) ^ 1'b1;
            crc32[6] = ^(body & 478'h0c689e256894698448f759877465c0a69bec0c69958f326b039d37a015bf00fe6d9bad221e85c3ad658dbbbdde331914b01f9fd751dcaf40627049f6) ^ 1'b1;
            crc32[7] = ^(body & 478'h2982585dc11ed245c25f60d2cd98cdaf0cb6f954c27cbb03cf8c5c6aba7625a1da60d4a3e9cb999c93baf4aa5490f786a081bcb0175ceea533e185ad) ^ 1'b0;
            crc32[8] = ^(body & 478'h2257d4ac920ba5c6d70f1279be62d7bc2203132e6d9ba9d257ae8bffe5e46f1eb59627a007572dff7fd46a8541d72aa281bdfa7e9a5c6d6f90c21d1b) ^ 1'b1;
            crc32[9] = ^(body & 478'h04afa95924174b8dae1e24f37cc5af784406265cdb3753a4af5d17ffcbc8de3d6b2c4f400eae5bfeffa8d50a83ae5545037bf4fd34b8dadf21843a36) ^ 1'b0;
            crc32[10] = ^(body & 478'h380c36a5581896560f8d9a3adcd81212b362ad3e5f0c789c960c1cd506999827d70f1067c99ca93ba7f029c4efaa6f25c6496ae4dd94059bb409622d) ^ 1'b1;
            crc32[11] = ^(body & 478'h014b095da0072de14caae7a99ce368c75dabbbfb577a2eece4ae0a809c3b1412af49ae2847f94cb11741d05837a21be44c2c56d70fcdbb129f13d21b) ^ 1'b0;
            crc32[12] = ^(body & 478'h33c576ac50385a8fcae41c8f1c959d6c803996714796820c01ea262ba97e0c785fc4d2b75b3287a47622236187b2f26758e62eb0ab7ec600c926b277) ^ 1'b1;
            crc32[13] = ^(body & 478'h278aed58a070b51f95c8391e392b3ad900732ce28f2d041803d44c5752fc18f0bf89a56eb6650f48ec4446c30f65e4ceb1cc5d6156fd8c01924d64ee) ^ 1'b0;
            crc32[14] = ^(body & 478'h0f15dab140e16a3f2b90723c725675b200e659c51e5a083007a898aea5f831e17f134add6cca1e91d8888d861ecbc99d6398bac2adfb1803249ac9dc) ^ 1'b0;
            crc32[15] = ^(body & 478'h1e2bb56281c2d47e5720e478e4aceb6401ccb38a3cb410600f51315d4bf063c2fe2695bad9943d23b1111b0c3d97933ac73175855bf63006493593b8) ^ 1'b0;
            crc32[16] = ^(body & 478'h0d040ed213b3a9b1fdf01b2dec0a9a2a38f78693900aff15d614519006e8e3d8fd1aa59267e864813a83b5c993d9e3da4edc68140309d029656a3131) ^ 1'b0;
            crc32[17] = ^(body & 478'h1a081da427675363fbe0365bd815345471ef0d272015fe2bac28a3200dd1c7b1fa354b24cfd0c90275076b9327b3c7b49db8d0280613a052cad46262) ^ 1'b0;
            crc32[18] = ^(body & 478'h34103b484ecea6c7f7c06cb7b02a68a8e3de1a4e402bfc57585146401ba38f63f46a96499fa19204ea0ed7264f678f693b71a0500c2740a595a8c4c4) ^ 1'b1;
            crc32[19] = ^(body & 478'h282076909d9d4d8fef80d96f6054d151c7bc349c8057f8aeb0a28c8037471ec7e8d52c933f432409d41dae4c9ecf1ed276e340a0184e814b2b518988) ^ 1'b0;
            crc32[20] = ^(body & 478'h1040ed213b3a9b1fdf01b2dec0a9a2a38f78693900aff15d614519006e8e3d8fd1aa59267e864813a83b5c993d9e3da4edc68140309d029656a31310) ^ 1'b1;
            crc32[21] = ^(body & 478'h2081da427675363fbe0365bd815345471ef0d272015fe2bac28a3200dd1c7b1fa354b24cfd0c90275076b9327b3c7b49db8d0280613a052cad462620) ^ 1'b0;
            crc32[22] = ^(body & 478'h3050d093fcdc6d322fb718a727f5c66c068f4563ebdd1aa04da2572b2b30d26247feea7e2ed93e88f84cf1b51e8e333c77a4861e7691ba7cad8d5a01) ^ 1'b0;
            crc32[23] = ^(body & 478'h11f2c530e98edb290cdfe2926ab8c03a36706b403ed8ea9553f29d7cc76980998eaa5a1b897263d7a83860bbd5eaa3d72ff78f2259c6c4dcac1ba243) ^ 1'b0;
            crc32[24] = ^(body & 478'h23e58a61d31db65219bfc524d57180746ce0d6807db1d52aa7e53af98ed301331d54b43712e4c7af5070c177abd547ae5fef1e44b38d89b958374486) ^ 1'b1;
            crc32[25] = ^(body & 478'h07cb14c3a63b6ca4337f8a49aae300e8d9c1ad00fb63aa554fca75f31da602663aa9686e25c98f5ea0e182ef57aa8f5cbfde3c89671b1372b06e890c) ^ 1'b0;
            crc32[26] = ^(body & 478'h3ec54d905c40d805354ec74f70954d3388edbb861fa58b7f5722d8ccaa44209174055e3b9f53007b1962860f47a3db16bf02fa0c7ad396c097dc0459) ^ 1'b1;
            crc32[27] = ^(body & 478'h3d8a9b20b881b00a6a9d8e9ee12a9a6711db770c3f4b16feae45b19954884122e80abc773ea600f632c50c1e8f47b62d7e05f418f5a72d812fb808b2) ^ 1'b0;
            crc32[28] = ^(body & 478'h3b15364171036014d53b1d3dc25534ce23b6ee187e962dfd5c8b6332a9108245d01578ee7d4c01ec658a183d1e8f6c5afc0be831eb4e5b025f701164) ^ 1'b0;
            crc32[29] = ^(body & 478'h362a6c82e206c029aa763a7b84aa699c476ddc30fd2c5bfab916c6655221048ba02af1dcfa9803d8cb14307a3d1ed8b5f817d063d69cb604bee022c8) ^ 1'b0;
            crc32[30] = ^(body & 478'h2c54d905c40d805354ec74f70954d3388edbb861fa58b7f5722d8ccaa44209174055e3b9f53007b1962860f47a3db16bf02fa0c7ad396c097dc04590) ^ 1'b0;
            crc32[31] = ^(body & 478'h18a9b20b881b00a6a9d8e9ee12a9a6711db770c3f4b16feae45b19954884122e80abc773ea600f632c50c1e8f47b62d7e05f418f5a72d812fb808b20) ^ 1'b1;
        end
    endfunction
    wire legal_op=(i_packet[505:502]==4'd1) ||
        ((i_packet[505:502]==4'd2) && (i_packet[461:438]==0) && (i_packet[437:182]==0));
    wire legal=(i_packet[509:506]==4'd1) && legal_op &&
        (i_packet[181:32]==0) && (i_packet[31:0]==crc32(i_packet[509:32]));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin o_v<=0; o_bad<=0; end
        else begin
            o_v<=(ENABLE!=0) && i_v && legal;
            o_bad<=(ENABLE!=0) && i_v && !legal;
        end
    end
    always @(posedge clk) begin
        if(ENABLE!=0) o_packet<=i_packet;
        else o_packet<=510'd0;
    end
    assign {o_op,o_epoch,o_pc,o_seq,o_tag,o_sec,o_data}=o_packet[505:182];
endmodule
