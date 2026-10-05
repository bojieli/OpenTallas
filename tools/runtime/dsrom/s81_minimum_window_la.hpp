#pragma once
#include <stdexcept>

// Pure typed forwarding into Noether's SAME shared four-stack backend.
// These functions do not eval, tick, construct storage, authorize writes or ACK.
// The enclosing shared-edge owner settles both actual models before its edge.
namespace dsrom_s81_minimum {
template<class Window, class Backend>
void require_window_la_ports(Window& w, Backend& b) {
    if (!w.contextp() || w.contextp()!=b.contextp())
        throw std::runtime_error("WINDOW LA requires the same actual runtime context");
    static_assert(sizeof(w.wl_req_v)==4 && sizeof(b.wl_req_v)==4, "WINDOW LA req_v geometry mismatch");
    static_assert(sizeof(w.wl_req_rdy)==4 && sizeof(b.wl_req_rdy)==4, "WINDOW LA req_rdy geometry mismatch");
    static_assert(sizeof(w.wl_req_addr)==120 && sizeof(b.wl_req_addr)==120, "WINDOW LA req_addr geometry mismatch");
    static_assert(sizeof(w.wl_req_len)==16 && sizeof(b.wl_req_len)==16, "WINDOW LA req_len geometry mismatch");
    static_assert(sizeof(w.wl_req_tag)==52 && sizeof(b.wl_req_tag)==52, "WINDOW LA req_tag geometry mismatch");
    static_assert(sizeof(w.wl_rsp_v)==4 && sizeof(b.wl_rsp_v)==4, "WINDOW LA rsp_v geometry mismatch");
    static_assert(sizeof(w.wl_rsp_rdy)==4 && sizeof(b.wl_rsp_rdy)==4, "WINDOW LA rsp_rdy geometry mismatch");
    static_assert(sizeof(w.wl_rsp_tag)==52 && sizeof(b.wl_rsp_tag)==52, "WINDOW LA rsp_tag geometry mismatch");
    static_assert(sizeof(w.wl_rsp_beat)==16 && sizeof(b.wl_rsp_beat)==16, "WINDOW LA rsp_beat geometry mismatch");
    static_assert(sizeof(w.wl_rsp_data)==1024 && sizeof(b.wl_rsp_data)==1024, "WINDOW LA rsp_data geometry mismatch");
}
template<class Window, class Backend>
void wire_window_la_request(Window& w, Backend& b) {
    require_window_la_ports(w,b);
    b.wl_req_v=w.wl_req_v;
    b.wl_req_addr=w.wl_req_addr;
    b.wl_req_len=w.wl_req_len;
    b.wl_req_tag=w.wl_req_tag;
    b.wl_rsp_rdy=w.wl_rsp_rdy;
}
template<class Window, class Backend>
void wire_window_la_response(Window& w, Backend& b) {
    require_window_la_ports(w,b);
    w.wl_req_rdy=b.wl_req_rdy;
    w.wl_rsp_v=b.wl_rsp_v;
    w.wl_rsp_tag=b.wl_rsp_tag;
    w.wl_rsp_beat=b.wl_rsp_beat;
    w.wl_rsp_data=b.wl_rsp_data;
}
} // namespace dsrom_s81_minimum
