#pragma once
#include <cstring>

// Host-only L20 operand address binding, matching dsrom_s81_l20_sim_only.py.
// Literal native instruction/ports and arithmetic remain unchanged. The enrolled
// DSROM_S81_MINIMUM_CROM_HEX must contain the actual L20 constants, not L0 gamma.
// results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz
// SHA256 fec91ca041e8b1640292ca06163def706c0d0dab8c5d524ba9e8f611dd925d0f
// results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json
// SHA256 269deb20fd02a7114982b522c679decb475da8232181e4a75bb0ce9cd51498dd
// Native vec.sv slices rd ports as 4*lane+operand (A,B,C,D).
// Apply only to exact canonical producer + entire literal + template hash.
inline uint32_t dsrom_s81_su_constant_address(
    const DsromS81PrefixOperation& op, unsigned operand, unsigned src, uint32_t address) {
    if (operand>=4) throw std::runtime_error("SU constant operand port");
    switch(op.index) {
    case 2490: { // Exact L20.I19; coefficients staged by explicit SIM_ONLY I18 caller.
        static constexpr std::array<uint32_t,64> literal{{0x00000012u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x20000004u,0x00000000u,0x0000035eu,0x00400002u,0x00000000u,0x04000000u,0x03000000u,0x01000000u,0x10800000u,0x00000000u,0x00000000u,0x80000000u,0xc0000002u,0x40000000u,0x20000000u,0x06005840u,0x00000d78u,0x01000008u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x80000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}};
        if(op.unit!=2||!op.template_sha256||std::strcmp(op.template_sha256,"fbb809f39f7e40aa80554ef7e8e7ff9a2768c403d772d06bf00e78eae37da28e")!=0||op.instruction!=literal)
            throw std::runtime_error("SU RoPE canonical key operation mismatch");
        if(operand==1||operand==3){
            if(src!=(operand==1?1u:2u)||address<0x31ffffe0u||address>0x31ffffffu)
                throw std::runtime_error("SU RoPE wrong target position/kind/coefficient span");
            return 128000u+(address-0x31ffffe0u);
        }
        return address;
    }
    case 2494: { // Exact L20.I23; coefficients staged by explicit SIM_ONLY I18 caller.
        static constexpr std::array<uint32_t,64> literal{{0x00000002u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x20000040u,0x00000000u,0x0000036eu,0x00400002u,0x00000000u,0x04000000u,0x03000000u,0x01000000u,0x10800000u,0x00000000u,0x00000000u,0x80000000u,0xc0000002u,0x40000000u,0x20000000u,0x06005840u,0x00000db8u,0x01000008u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x80000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}};
        if(op.unit!=2||!op.template_sha256||std::strcmp(op.template_sha256,"1ec11dc637c0e036e49757e4b0fbbce3258cbb3c7b09838226530cbbb1c3a614")!=0||op.instruction!=literal)
            throw std::runtime_error("SU RoPE canonical query operation mismatch");
        if(operand==1||operand==3){
            if(src!=(operand==1?1u:2u)||address<0x31ffffe0u||address>0x31ffffffu)
                throw std::runtime_error("SU RoPE wrong target position/kind/coefficient span");
            return 128000u+(address-0x31ffffe0u);
        }
        return address;
    }
    case 2484: { // L20.I13
        static constexpr std::array<uint32_t,64> literal{{
            0x00000012u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000004u,
            0x00000002u, 0x00000327u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000c9au, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x06100040u, 0x00000cecu,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"2788192194b6f874bfadf950d51d01853a0b54388a4ce449d3d0d74a774029a0")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>1279u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+10240u;
        default: return address;
        }
    }
    case 2488: { // L20.I17
        static constexpr std::array<uint32_t,64> literal{{
            0x00000012u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000004u,
            0x00000001u, 0x0000034fu, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000c9au, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x06100040u, 0x00000d5cu,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"9aea4effa19626df2f620682aa376aafb62606f2f9eb392458a1f1f364d31e1b")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>511u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+11520u;
        default: return address;
        }
    }
    case 2500: { // L20.I29
        static constexpr std::array<uint32_t,64> literal{{
            0x00000012u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000004u,
            0x80000001u, 0x000005b0u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000c9au, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x06100040u, 0x000016e2u,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"95a18e3b6ac566cac3497ba83454b3b0d4ec567b1dc750954706e73b3e177c3e")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>511u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12528u;
        default: return address;
        }
    }
    case 2504: { // L20.I33
        static constexpr std::array<uint32_t,64> literal{{
            0x00000012u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x40000004u,
            0x80000000u, 0x000005c0u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000c9au, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x06100040u, 0x0000170au,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"74dc18378d2cc0e0daef471d918735ef815c5d7bbd44dcdcfc2d3b24739a96b2")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>127u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+13040u;
        default: return address;
        }
    }
    case 2527: { // L20.I56
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000004u,
            0x00000000u, 0x00000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000001u, 0x40000000u, 0x00000000u, 0x04494240u, 0x00000a06u,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0xa0000000u, 0x06b0c6f7u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"a2126885030e34f799a5825d61360dd1d552eeef92dfa3d1f1805ddc7c9e6698")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>3u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12032u;
        case 3:
            if (src!=1 || address>3u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12056u;
        default: return address;
        }
    }
    case 2528: { // L20.I57
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000004u,
            0x10000000u, 0x00000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x00000002u, 0x08000000u, 0x00000000u, 0x00000011u, 0x40000000u, 0x00000000u, 0x04394240u, 0x00000a08u,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"2a69bea7440499e35ced0ca10a52c48e43f8cdefa5754cb54f8b19f6e97ece23")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address<4u || address>7u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-4u+12036u;
        case 3:
            if (src!=1 || address<4u || address>7u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-4u+12060u;
        default: return address;
        }
    }
    case 2529: { // L20.I58
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000010u,
            0x20000000u, 0x04000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x80000004u, 0x08000000u, 0x00000000u, 0x00000021u, 0x40000004u, 0x00000000u, 0x04014240u, 0x10000a12u,
            0x01000000u, 0x20000000u, 0x80014280u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000001u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"beb179e85222f6d0e4cdc1c4739eb1eec9ef013a35e6c8d809bb5efa11ca4a6c")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address<8u || address>23u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-8u+12040u;
        case 3:
            if (src!=1 || address<8u || address>23u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-8u+12064u;
        default: return address;
        }
    }
    case 2535: { // L20.I64
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x08000004u,
            0x01000000u, 0x00000000u, 0x00400000u, 0x00000000u, 0x00000000u, 0x0000121cu, 0x01000000u, 0x00000000u,
            0x000090f0u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x0422c000u, 0x00001220u,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"2f0c8d1f7dd9991871a239a0a67fb5628857ecb2cc23f62cc4fd7c55ef6d846f")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 0:
            if (src!=1 || address>15u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12128u;
        default: return address;
        }
    }
    case 2554: { // L20.I83
        static constexpr std::array<uint32_t,64> literal{{
            0x00000012u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000004u,
            0x0000000au, 0x00000286u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000c9au, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x06100040u, 0x00000b58u,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"9221023d4556e8137e4a3254ddc192ffd714f266694e020f88a2d8f2a3525829")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>5119u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+5120u;
        default: return address;
        }
    }
    case 2563: { // L20.I92
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0xc0000004u,
            0x80000000u, 0x00001655u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000001u, 0x40000000u, 0x00000000u, 0x04014000u, 0x0000596eu,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"574aab31bf37832811902b4113dbb029251be5f049c397f4464020900d01f745")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 3:
            if (src!=1 || address>383u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12144u;
        default: return address;
        }
    }
    case 2576: { // L20.I105
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000004u,
            0x00000000u, 0x00000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x00000000u, 0x08000000u, 0x00000000u, 0x00000001u, 0x40000000u, 0x00000000u, 0x04494240u, 0x00000a0cu,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0xa0000000u, 0x06b0c6f7u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"cae06be0df797d27ab7efc4cddeb046bafa70b5b05857422f0c2a56553c9221b")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address>3u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12080u;
        case 3:
            if (src!=1 || address>3u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-0u+12104u;
        default: return address;
        }
    }
    case 2577: { // L20.I106
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000004u,
            0x10000000u, 0x00000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x00000002u, 0x08000000u, 0x00000000u, 0x00000011u, 0x40000000u, 0x00000000u, 0x04394240u, 0x00000a0eu,
            0x01000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x08000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x80000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"0d45a5689d7406a1b983c873d6c28ed06ada16cde70c1eea1d495b867d932e90")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address<4u || address>7u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-4u+12084u;
        case 3:
            if (src!=1 || address<4u || address>7u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-4u+12108u;
        default: return address;
        }
    }
    case 2578: { // L20.I107
        static constexpr std::array<uint32_t,64> literal{{
            0x00000002u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x02000010u,
            0x20000000u, 0x04000281u, 0x00400000u, 0x00000000u, 0x00000000u, 0x00000a02u, 0x00000000u, 0x20000000u,
            0x80000004u, 0x08000000u, 0x00000000u, 0x00000021u, 0x40000004u, 0x00000000u, 0x04014240u, 0x10000a12u,
            0x01000000u, 0x20000000u, 0x80014280u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000001u, 0x00000000u, 0x00000000u,
            0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u, 0x00000000u,
        }};
        if (op.unit!=2 || !op.template_sha256 ||
            std::strcmp(op.template_sha256,"beb179e85222f6d0e4cdc1c4739eb1eec9ef013a35e6c8d809bb5efa11ca4a6c")!=0 ||
            op.instruction!=literal)
            throw std::runtime_error("SU constant canonical L20 operation mismatch");
        switch(operand) {
        case 2:
            if (src!=1 || address<8u || address>23u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-8u+12088u;
        case 3:
            if (src!=1 || address<8u || address>23u)
                throw std::runtime_error("SU constant outside canonical operand span");
            return address-8u+12112u;
        default: return address;
        }
    }
    default: return address;
    }
}
