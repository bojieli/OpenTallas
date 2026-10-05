// Native tagged near-row hook of the combined STREAM4 runtime (tools/runtime/qwen_combined/
// stream4_runtime_binding.hpp declares it).  Vhbm MUST be Verilated from the additive successor
// backend rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv (top ot_qwen_hbm_stream4_tagged, prefix Vhbm,
// sources rtl/model_ready_hbm_r14/ot_hbm_r14_stream_{pc,stack}.sv): its t_* port is served by the
// SAME 128 pseudo-channel controllers and the SAME backing array `mem` as the descriptor stream
// that wire_stream4_transport() connects.
//
// COMBINATIONAL PIN WIRING ONLY (no eval, clock edge, model, memory or response of its own): the
// die's protected hclk row boundary to the model's tagged port, its clock and reset included
// (t_clk = die.hclk, t_rst_n = die.hrst_n; the model owns the t_clk <-> controller crossing).
//   die outputs -> model : h_req_v/we [4], h_req_addr 4x24, h_req_len 4x5, h_req_tag 4x13,
//                          h_req_wdata 4x256, h_rsp_ready [128]
//   model -> die inputs  : t_req_ready [4], t_pc_room/t_rsp_v/t_rsp_wr [128], t_rsp_tag 128x13,
//                          t_rsp_beat 128x4, t_rsp_data 128x256
// Returns whether any pin changed (the caller's settle loop iterates until stable).
#include "Vdie.h"
#include "Vhbm.h"
#include <cstddef>
#include <type_traits>

namespace {
template <class D, class S> bool pin(D& dst, const S& src) {
    if constexpr (std::is_arithmetic_v<D>) {
        if (dst == D(src)) return false;
        dst = D(src);
        return true;
    } else {
        static_assert(sizeof(D) == sizeof(S), "tagged row port widths differ between Vdie and Vhbm");
        bool changed = false;
        for (std::size_t i = 0; i < sizeof(D) / sizeof(EData); ++i)
            if (dst[i] != src[i]) { dst[i] = src[i]; changed = true; }
        return changed;
    }
}
}  // namespace

bool qwen_stream4_wire_native_tagged_rows(Vdie& d, Vhbm& m) {
    bool c = false;
    c |= pin(m.t_clk, d.hclk);
    c |= pin(m.t_rst_n, d.hrst_n);
    c |= pin(m.t_req_v, d.h_req_v);
    c |= pin(m.t_req_we, d.h_req_we);
    c |= pin(m.t_req_addr, d.h_req_addr);
    c |= pin(m.t_req_len, d.h_req_len);
    c |= pin(m.t_req_tag, d.h_req_tag);
    c |= pin(m.t_req_wdata, d.h_req_wdata);
    c |= pin(m.t_rsp_ready, d.h_rsp_ready);
    c |= pin(d.h_req_ready, m.t_req_ready);
    c |= pin(d.h_pc_room, m.t_pc_room);
    c |= pin(d.h_rsp_v, m.t_rsp_v);
    c |= pin(d.h_rsp_wr, m.t_rsp_wr);
    c |= pin(d.h_rsp_tag, m.t_rsp_tag);
    c |= pin(d.h_rsp_beat, m.t_rsp_beat);
    c |= pin(d.h_rsp_data, m.t_rsp_data);
    return c;
}
