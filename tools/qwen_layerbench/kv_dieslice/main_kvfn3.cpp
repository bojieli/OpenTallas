// KV-FN-3 10-31: START only after the die reports ready (no magic delay).  The KV die's peer token service is
// fail-closed: a START whose peer_service_fresh is false (local_service_ready = service_ready && program_ready low)
// sets a sticky fault and never latches token_epoch (KV-FN-2 unit vehicle).  program_ready needs the program commit
// (HREC kind 13).  Default here: the board queues START once the die's program_ready (hub_Wi o_host_auth_lp[80], the
// lane that carries {token_epoch_valid, program_ready, program_epoch, program_digest} to hub_C) has been high
// +HOST_TOKEN_READY_MARGIN core cycles (default 32), and not before +HOST_TOKEN_DELAY after mission START (default 0
// in wait mode).  +HOST_TOKEN_NOWAIT restores the KV-49-FN fixed-delay form (control).  AUTHLP lines print every
// change of program_ready / token_epoch_valid on that lane.
// +HOST_TOKEN_WAIT=status (default): protocol form.  The peer token service advertises its readiness to the package
// controller in its CTRL STATUS frame (opcode 0x21 version 2, src = role, ready bit 153, service epoch 169:154; sent on
// every ready/epoch change).  The board decodes every die->host word at its RX pad (u_host u_phy u_pad dq, after the
// real adapter) and queues START once it has seen a STATUS with ready 1 and service epoch == +HOST_TOKEN_SEPOCH, plus
// +HOST_TOKEN_READY_MARGIN core cycles.  +HOST_TOKEN_WAIT=lane uses the program_ready lane tap instead (diagnostic).
// D2H lines print every die->host word header.
// DIE-KV-49-FN: passive native token probe gate (main_gate.cpp) + the first token's HOST command.
// Bench stimulus only (no RTL change): the KV die is a TP8 peer (die_id 1, STRAPPED host root), so its host token
// command is the package controller's CTRL START frame (class 1, opcode 0x22 version 2, src die 0, target 1<<1,
// first sequence 0, hc[38:0] = {start, gen2, token18, pos18} at 86:48, token epoch 245:230 with [231:230] = user,
// epoch valid 246, service epoch 262:247).  It is appended to the bench's own host frame list after mission START
// (+HOST_TOKEN_DELAY core cycles, default 64) and sent through the same credited board port as the boot frames.
// +HOST_TOKEN_OFF disables it (control).  Fields: +HOST_TOKEN_TOK (1) +HOST_TOKEN_POS (CTX-1) +HOST_TOKEN_GEN (1)
// +HOST_TOKEN_EPOCH (4) +HOST_TOKEN_SEPOCH (0).
#include "verilated.h"
#include "Vtb_kvslice.h"
#include "Vtb_kvslice___024root.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <type_traits>
#ifndef DUTP
#define DUTP dut__DOT__u_bound__DOT__
#endif
#define CAT2(a, b) a##b
#define CAT(a, b) CAT2(a, b)
#define R(x) topp->rootp->CAT(tb_kvslice__DOT__, x)
#define F(x) R(u_far__DOT__u_c__DOT__u_core__DOT__##x)
#define K(x) topp->rootp->CAT(CAT(tb_kvslice__DOT__, DUTP), sys_c__DOT__u_d2d_kv__DOT__u_core__DOT__##x)
#define S(x) topp->rootp->CAT(CAT(tb_kvslice__DOT__, DUTP), sys_c__DOT__##x)
#define B(x) topp->rootp->CAT(CAT(tb_kvslice__DOT__, DUTP), x)
template <class T> static unsigned long long g(const T& x) {
    if constexpr (std::is_integral_v<T>) return (unsigned long long)x;
    else return (unsigned long long)x.at(0) | ((unsigned long long)x.at(1) << 32);
}
static long plus(VerilatedContext* c, const char* name, long dflt) {
    const char* m = c->commandArgsPlusMatch(name);
    if (!m || !*m) return dflt;
    const char* eq = std::strchr(m, '=');
    return eq ? std::strtol(eq + 1, nullptr, 0) : dflt;
}
template <class W> static void put(W& w, int lo, int width, unsigned long long v) {
    for (int b = 0; b < width; ++b) {
        const int bit = lo + b;
        if (v >> b & 1) w.at(bit / 32) |= (1u << (bit % 32));
        else w.at(bit / 32) &= ~(1u << (bit % 32));
    }
}
extern "C" int kvfn3_main(int argc, char** argv, char**) {
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->threads(1);
    contextp->commandArgs(argc, argv);
    const std::unique_ptr<Vtb_kvslice> topp{new Vtb_kvslice{contextp.get(), ""}};
    const bool tok_on = !contextp->commandArgsPlusMatch("HOST_TOKEN_OFF")[0];
    const bool wait_ready = !contextp->commandArgsPlusMatch("HOST_TOKEN_NOWAIT")[0];
    const long ctx = plus(contextp.get(), "CTX=", 8192), delay = plus(contextp.get(), "HOST_TOKEN_DELAY=", wait_ready ? 0 : 64),
               margin = plus(contextp.get(), "HOST_TOKEN_READY_MARGIN=", 32);
    long pr_since = -1; unsigned long long oalp = ~0ull;
    const char* wm = contextp->commandArgsPlusMatch("HOST_TOKEN_WAIT=");
    const bool wait_lane = wm && std::strstr(wm, "=lane");
    long st_since = -1; bool ovq = false; unsigned nd2h = 0; unsigned od0 = 0, od1 = 0;
    const unsigned long long tok = plus(contextp.get(), "HOST_TOKEN_TOK=", 1), pos = plus(contextp.get(), "HOST_TOKEN_POS=", ctx - 1),
                             gen = plus(contextp.get(), "HOST_TOKEN_GEN=", 1), ep = plus(contextp.get(), "HOST_TOKEN_EPOCH=", 4),
                             sep = plus(contextp.get(), "HOST_TOKEN_SEPOCH=", 0);
    int inj = -1; bool sent_seen = false;
    unsigned long long old = ~0ull, kab = 0, fab = 0, kfc = 0, ffc = 0; unsigned lines = 0, last = 0, lastc = ~0u, obs = 0;
    bool setup_seen = false; unsigned long long otep = ~0ull, otst = 0, ohi = 0, otv = 0;
    std::printf("HOSTTOK_WAIT ready_wait %d mode %s margin %ld\n", wait_ready, wait_lane ? "lane(program_ready hub_Wi o_host_auth_lp[80])" : "status(die CTRL STATUS 0x21 ready=1 at board RX)", margin);
    std::printf("HOSTTOK_CFG on %d delay %ld tok %llu pos %llu gen %llu epoch %04llx sepoch %04llx\n", tok_on, delay, tok, pos, gen, ep, sep);
    while (VL_LIKELY(!contextp->gotFinish())) {
        topp->eval();
        const unsigned cyc = R(cyc_core);
        setup_seen |= static_cast<int>(R(t_setup)) >= 0;
        const int msc = static_cast<int>(R(mission_start_cycle));
        {
            const unsigned long long alp = (g(B(x_hub_Wi_o_host_auth_lp_hub_C).at(2)) >> 16) & 3;  // [80] program_ready, [81] token_epoch_valid
            if (alp != oalp) {
                std::printf("AUTHLP cyc %u program_ready %llu token_epoch_valid %llu\n", cyc, alp & 1, alp >> 1 & 1);
                std::fflush(stdout); oalp = alp;
            }
            if (!(alp & 1)) pr_since = -1;
            else if (pr_since < 0) pr_since = (long)cyc;
        }
        {
            const bool vq = R(u_host__DOT__u_phy__DOT__u_pad__DOT__vq);
            const auto& d = R(u_host__DOT__u_phy__DOT__u_pad__DOT__dq);
            // vq can stay high across back-to-back words: a new word = vq rise or changed data (STATUS seq always differs)
            const bool neww = vq && (!ovq || d.at(1) != od1 || d.at(0) != od0);
            if (vq) { od0 = d.at(0); od1 = d.at(1); }
            if (neww) {
                auto bits = [&](int lo, int w) { unsigned long long v = 0; for (int b = 0; b < w; ++b) v |= (unsigned long long)(d.at((lo + b) / 32) >> ((lo + b) % 32) & 1) << b; return v; };
                const unsigned long long cls = bits(524, 4), op = bits(0, 8), ver = bits(8, 8), src = bits(16, 3), seq = bits(32, 16),
                                         rdy = bits(153, 1), lep = bits(154, 16);
                if (nd2h < 200) {
                    std::printf("D2H cyc %u n %u class %llu op %02llx ver %llu src %llu seq %llu ready %llu sepoch %04llx w0 %08x\n", cyc, nd2h,
                                cls, op, ver, src, seq, rdy, lep, d.at(0));
                    std::fflush(stdout);
                }
                ++nd2h;
                if (op == 0x21 && ver == 2) {
                    if (rdy && lep == (sep & 0xffff)) { if (st_since < 0) st_since = (long)cyc; }
                    else st_since = -1;
                }
            }
            ovq = vq;
        }
        const long rdy_since = wait_lane ? pr_since : st_since;
        const bool ready_ok = !wait_ready || (rdy_since >= 0 && (long)cyc >= rdy_since + margin);
        if (tok_on && inj < 0 && msc >= 0 && cyc >= (unsigned)(msc + delay) && ready_ok && R(sent) == R(nfr)) {
            const unsigned n = R(nfr);
            auto& f = R(frames)[n];
            for (int i = 0; i < 17; ++i) f.at(i) = 0;
            put(f, 0, 8, 0x22); put(f, 8, 8, 2); put(f, 16, 3, 0); put(f, 24, 8, 1u << 1); put(f, 32, 16, 0);
            const unsigned long long hc = (1ull << 38) | ((gen & 3) << 36) | ((tok & 0x3ffff) << 18) | (pos & 0x3ffff);
            put(f, 48, 39, hc); put(f, 230, 16, ep); put(f, 246, 1, 1); put(f, 247, 16, sep); put(f, 524, 4, 1);
            R(nfr) = n + 1; inj = (int)n;
            std::printf("HOSTTOK_QUEUED cyc %u frame %u mission_start %d ready_since %ld hc %010llx w0 %08x\n", cyc, n, msc,
                        wait_ready ? rdy_since : -1L, hc, f.at(0));
            std::fflush(stdout);
        }
        if (inj >= 0 && !sent_seen && (int)R(sent) > inj) {
            sent_seen = true; std::printf("HOSTTOK_SENT cyc %u\n", cyc); std::fflush(stdout);
        }
        if (setup_seen) {
            const unsigned long long ka = g(K(ab)), kf = g(K(fc)), fa = g(F(ab)), ff = g(F(fc));
            kab |= ka; fab |= fa; kfc |= kf; ffc |= ff; last = cyc;
            const unsigned long long st = ka | kf << 1 | fa << 9 | ff << 10;
            if (st != old && lines < 200) {
                std::printf("GATE cyc %u farcyc %llu kv ab %llu fc %02llx | far ab %llu fc %02llx\n", cyc, g(R(u_far__DOT__cyc)), ka, kf, fa, ff);
                std::fflush(stdout); ++lines; old = st;
            }
            if (cyc != lastc && obs < 400) {
                lastc = cyc;
                const unsigned long long tep = g(S(i_host_token_epoch_q)), tst = g(S(w_dcal_tok_start));
                const auto& rt = S(i_host_rec_tx_q);
                const unsigned long long hi = rt.at(16), top = rt.at(17);
                const unsigned long long tv = g(K(tv)), fire = g(K(u_end__DOT__fire));
                if (tep != otep || tst != otst) { std::printf("CTL cyc %u token_epoch %04llx tok_start %llx\n", cyc, tep, tst); ++obs; }
                if (hi != ohi) { std::printf("HREC cyc %u obs %llu kind %llu ep %04llx\n", cyc, top >> 4 & 1, (top << 5 | hi >> 27) & 0xf, hi >> 5 & 0xffff); ++obs; }
                if (((tv ^ otv) & 2) || (fire & 2)) { std::printf("P1 cyc %u tv %llu fire %llu\n", cyc, tv >> 1 & 1, fire >> 1 & 1); ++obs; }
                otep = tep; otst = tst; ohi = hi; otv = tv;
                std::fflush(stdout);
            }
        }
        if (!topp->eventsPending()) break;
        contextp->time(topp->nextTimeSlot());
    }
    const auto admissions = g(R(u_far__DOT__n_adm));
    const auto tokens = g(R(u_far__DOT__n_tok));
    const bool pass = setup_seen && admissions && tokens && !kab && !kfc && !fab && !ffc;
    std::printf("HOSTTOK_END injected %d sent %d\n", inj >= 0, sent_seen);
    std::printf("GATE_END last_cyc %u setup %d admissions %llu tokens %llu kv_ab %llu kv_fc %02llx far_ab %llu far_fc %02llx verdict %s\n",
                last, setup_seen, admissions, tokens, kab, kfc, fab, ffc, pass ? "PASS" : "FAIL");
    std::fflush(stdout);
    topp->final();
    contextp->statsPrintSummary();
    return 0;
}
