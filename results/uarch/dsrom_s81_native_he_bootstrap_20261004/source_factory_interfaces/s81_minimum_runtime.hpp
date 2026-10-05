#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>

class VerilatedContext;

// Literal ports of the already-built ot_v41_pair_w17w10. These are native
// payloads, not FP32 values converted or quantized by a software interpreter.
struct DsromS81PairDrive {
    uint8_t cfg_go=0,cfg_np=0,go=0,go_bf=0;
    uint16_t cfg_ph=0;
    uint8_t xs_v=0,xs_p=0,xs_b=0,xs_sv=0,xs_pos=0;
    uint16_t xs_e0=0,xs_e1=0;
    std::array<uint32_t,8> xs_q0{},xs_q1{};
    uint8_t xb_pos=0,xb_v=0,xb_b=0,xb_sv=0;
    uint32_t xb_u=0;
    std::array<uint32_t,32> xb_d{};
};
struct DsromS81PairResult {
    uint8_t valid=0,error=0,positions=0;
    uint16_t segments=0,segment_counts=0;
    uint32_t rows=0;
    uint64_t values=0;
    bool busy=false,quiet=false,fault=false;
};

// Participants wrap actual native encoder/return/capture/VM models. Every
// participant samples the same pre-edge result before ANY rising evaluation.
// The host owns all clock edges; a participant must not clock a private loop.
struct DsromS81MinimumParticipant {
    std::string name;
    std::function<void(const DsromS81PairResult&)> prepare;
    std::function<void(bool reset_released)> rising,falling;
    std::function<bool()> fault;
};

struct DsromS81MinimumRuntime {
    int stage,rank,pair;
    bool bf16;
    VerilatedContext* context;
    std::function<void(const DsromS81PairDrive&)> drive;
    std::function<DsromS81PairResult()> result;
    std::function<void()> tick;
    // One shared cold reset before context admission, never a debt-clearing reset.
    std::function<void()> cold_start;
    std::function<long()> cycle;
    std::vector<DsromS81MinimumParticipant> participants;
    // Actual admission and matched VM publication/drain outputs from Popper's
    // mechanism, including pending/visibility/fault obligations. Required.
    std::function<bool(uint64_t)> publication_ready,publication_drained;
    std::optional<uint64_t> identity;
    std::function<void(uint64_t)> bind_context;
    // Rebind native ROM/CFG only under positive old-context drain and quiet.
    // This reuses the SAME pair model; it does not reset accepted state.
    std::function<void(int stage,int rank,int pair,const std::string& cfg)> reload;
};

// Actual source caller registers its native input and publication participants,
// admits the real context, drives source-native inputs and waits real drain.
extern "C" int dsrom_s81_minimum_source_main(DsromS81MinimumRuntime&,const char* output);
