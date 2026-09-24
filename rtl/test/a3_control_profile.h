// ---------------------------------------------------------------------------
// Cycle attribution for the reduced-token vehicle: where do the cycles go?
//
// Compiled into rtl/test/a3_reduced_token_driver.cpp only when OT_A3_PROFILE is
// defined, together with rtl/test/a3_control_profile.vlt, which marks the few
// internal registers read here public.  Without both, the driver is unchanged.
//
// Every cycle is put in exactly ONE bucket, by the state of the three control
// machines that sit between the program and an engine:
//
//   engine        the issue bridge is in S_START / S_ENGINE_WAIT: an engine
//                 owns the cycle (its own walk, including its internal
//                 operand-fetch control, is inside this bucket)
//   admission     the bridge is in any other non-idle state: descriptor
//                 fetches, placement/admission checks, index reads, response
//   adapter       the bridge is idle but the completion adapter is replaying
//                 captured views or returning a completion
//   frontend      both are idle: the microsequencer is fetching, decoding,
//                 evaluating predicates or waits, resolving views, checking
//                 dependences or looping, and no operation is in flight
//
// Inside `engine`, MAC-active cycles (a product entering the pipelined MAC lane,
// or the legacy lane busy) are counted separately, so the datapath's own
// efficiency and the control's are not confused.
//
// Output: `PROFILE <key> <value>` lines and one `PROFILE_ISSUE` line per engine
// issue, parsed by tools/profile_abi3_control_path.py.
// ---------------------------------------------------------------------------
#pragma once

#include "Vot_a3_shipped_prefix_top___024root.h"

#include <cstdint>
#include <cstdio>
#include <map>
#include <vector>

namespace ot_profile {

constexpr unsigned kBridgeIdle = 0, kBridgeStart = 6, kBridgeEngineWait = 7,
                   kBridgeResponse = 8;
constexpr unsigned kAdapterIdle = 0;

struct Issue {
    unsigned family = 0, sub = 0, index = 0;
    std::uint64_t t_issue = 0, t_bridge = 0, t_engine = 0, t_engine_end = 0,
                  t_bridge_end = 0, t_complete = 0;
    std::uint64_t engine_cycles = 0, mac_cycles = 0, work = 0;
    bool bridge_seen = false, engine_seen = false, done = false;
};

struct Profile {
    std::uint64_t cycles = 0;
    std::uint64_t engine = 0, admission = 0, adapter = 0, frontend = 0;
    std::uint64_t mac_active = 0;
    std::uint64_t seq_state_all[64] = {};
    std::uint64_t seq_state_frontend[64] = {};
    std::uint64_t bridge_state[32] = {};
    std::uint64_t adapter_state[4] = {};
    std::vector<Issue> issues;
    unsigned prev_bridge = 0;
    int open = -1;   // index of the issue the bridge is serving
};

inline Profile& P() { static Profile p; return p; }

template <class Dut>
inline void sample(Dut& dut, std::uint64_t cycle) {
    auto* r = dut.rootp;
    Profile& p = P();
    const unsigned seq = r->ot_a3_shipped_prefix_top__DOT__device__DOT__sequencer__DOT__state & 63u;
    const unsigned ad = r->ot_a3_shipped_prefix_top__DOT__adapter__DOT__state & 3u;
    const unsigned br = r->ot_a3_shipped_prefix_top__DOT__bridge__DOT__state & 31u;
    const bool mac = r->ot_a3_shipped_prefix_top__DOT__bridge__DOT__engines__DOT__fastmac__DOT__iss_v ||
                     r->ot_a3_shipped_prefix_top__DOT__bridge__DOT__engines__DOT__mac__DOT__busy;
    ++p.cycles;
    ++p.seq_state_all[seq];
    ++p.bridge_state[br];
    ++p.adapter_state[ad];
    const bool eng = (br == kBridgeStart) || (br == kBridgeEngineWait);
    if (eng) {
        ++p.engine;
        if (mac) ++p.mac_active;
    } else if (br != kBridgeIdle) {
        ++p.admission;
    } else if (ad != kAdapterIdle) {
        ++p.adapter;
    } else {
        ++p.frontend;
        ++p.seq_state_frontend[seq];
    }

    // -- per-issue timeline -------------------------------------------------
    if (dut.trace_issue_valid) {
        Issue is;
        is.family = dut.trace_issue_family;
        is.sub = dut.trace_issue_sub;
        is.index = dut.trace_issue_index;
        is.t_issue = cycle;
        p.issues.push_back(is);
    }
    if (p.prev_bridge == kBridgeIdle && br != kBridgeIdle) {
        // the bridge serves operations in issue order, one at a time
        for (std::size_t i = 0; i < p.issues.size(); ++i)
            if (!p.issues[i].bridge_seen) { p.open = (int)i; break; }
        if (p.open >= 0) { p.issues[p.open].bridge_seen = true; p.issues[p.open].t_bridge = cycle; }
    }
    if (p.open >= 0) {
        Issue& is = p.issues[p.open];
        if (eng) {
            if (!is.engine_seen) { is.engine_seen = true; is.t_engine = cycle; }
            is.t_engine_end = cycle;
            ++is.engine_cycles;
            if (mac) ++is.mac_cycles;
        }
        if (br == kBridgeResponse) is.work = dut.engine_work_count;
        if (br == kBridgeIdle && p.prev_bridge != kBridgeIdle) {
            is.t_bridge_end = cycle;
            is.done = true;
            p.open = -1;
        }
    }
    p.prev_bridge = br;
}

inline void report() {
    Profile& p = P();
    std::printf("PROFILE cycles %llu\n", (unsigned long long)p.cycles);
    std::printf("PROFILE engine %llu\n", (unsigned long long)p.engine);
    std::printf("PROFILE admission %llu\n", (unsigned long long)p.admission);
    std::printf("PROFILE adapter %llu\n", (unsigned long long)p.adapter);
    std::printf("PROFILE frontend %llu\n", (unsigned long long)p.frontend);
    std::printf("PROFILE mac_active %llu\n", (unsigned long long)p.mac_active);
    for (unsigned s = 0; s < 64; ++s)
        if (p.seq_state_all[s])
            std::printf("PROFILE seq_state_all %u %llu\n", s, (unsigned long long)p.seq_state_all[s]);
    for (unsigned s = 0; s < 64; ++s)
        if (p.seq_state_frontend[s])
            std::printf("PROFILE seq_state_frontend %u %llu\n", s, (unsigned long long)p.seq_state_frontend[s]);
    for (unsigned s = 0; s < 32; ++s)
        if (p.bridge_state[s])
            std::printf("PROFILE bridge_state %u %llu\n", s, (unsigned long long)p.bridge_state[s]);
    for (unsigned s = 0; s < 4; ++s)
        if (p.adapter_state[s])
            std::printf("PROFILE adapter_state %u %llu\n", s, (unsigned long long)p.adapter_state[s]);
    for (const Issue& is : p.issues)
        std::printf("PROFILE_ISSUE fam=%u sub=%u index=%u t_issue=%llu t_bridge=%llu "
                    "t_engine=%llu t_engine_end=%llu t_bridge_end=%llu engine_cycles=%llu "
                    "mac_cycles=%llu work=%llu\n",
                    is.family, is.sub, is.index, (unsigned long long)is.t_issue,
                    (unsigned long long)is.t_bridge, (unsigned long long)is.t_engine,
                    (unsigned long long)is.t_engine_end, (unsigned long long)is.t_bridge_end,
                    (unsigned long long)is.engine_cycles, (unsigned long long)is.mac_cycles,
                    (unsigned long long)is.work);
}

}  // namespace ot_profile
