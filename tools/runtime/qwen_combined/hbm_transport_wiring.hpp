#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>

// Include after the runtime's getb/setb/rt_set primitives. This transports
// literal ot_qwen_rom_combined_die pins to one NPC=32, TAGW=13 HBM model.
// The caller owns all instances, clocks, resets, evaluation and settling.
namespace qwen_combined {

template<class Die, class Hbm>
bool wire_hbm_transport(Die& die, Hbm& hbm, unsigned stack) {
    if (stack >= 4)
        throw std::out_of_range("qwen_combined HBM stack must be 0..3");

    bool changed = false;
    changed |= rt_set(hbm.req_v, uint8_t(getb(die.h_req_v, stack, 1)));
    changed |= rt_set(hbm.req_we, uint8_t(getb(die.h_req_we, stack, 1)));
    changed |= rt_set(hbm.req_addr, uint32_t(getb(die.h_req_addr, stack * 24, 24)));
    changed |= rt_set(hbm.req_len, uint8_t(getb(die.h_req_len, stack * 5, 5)));
    changed |= rt_set(hbm.req_tag, uint16_t(getb(die.h_req_tag, stack * 13, 13)));
    changed |= rt_set(hbm.rsp_rdy, uint32_t(getb(die.h_rsp_ready, stack * 32, 32)));
    // Each 256-bit payload starts on a 32-bit VlWide word boundary.
    for (unsigned word = 0; word < 8; ++word)
        changed |= rt_set(hbm.req_wdata[word], die.h_req_wdata[stack * 8 + word]);

    auto copy_bits = [&](auto& bus, std::size_t offset, int width, uint64_t value) {
        if (getb(bus, offset, width) != value) {
            setb(bus, offset, width, value);
            changed = true;
        }
    };
    copy_bits(die.h_req_ready, stack, 1, hbm.req_rdy);
    copy_bits(die.h_pc_room, stack * 32, 32, hbm.pc_room);
    copy_bits(die.h_rsp_v, stack * 32, 32, hbm.rsp_v);
    copy_bits(die.h_rsp_wr, stack * 32, 32, hbm.rsp_wr);
    for (unsigned pc = 0; pc < 32; ++pc) {
        copy_bits(die.h_rsp_tag, (stack * 32 + pc) * 13, 13,
                  getb(hbm.rsp_tag, pc * 13, 13));
        copy_bits(die.h_rsp_beat, (stack * 32 + pc) * 4, 4,
                  getb(hbm.rsp_beat, pc * 4, 4));
    }
    for (unsigned word = 0; word < 32 * 8; ++word)
        changed |= rt_set(die.h_rsp_data[stack * 32 * 8 + word], hbm.rsp_data[word]);

    return changed;
}

} // namespace qwen_combined
