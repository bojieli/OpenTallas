// Standalone check of the REAL_MEM ROM services through the ASAP7 macro models' own read path.
// scale bank: a random 50,112-word image (the largest layer scale image), 20,000 random reads;
// embedding ROM (array storage, the macro read contract): rows of 8 random tokens (incl. 0 and 151,935) and their scales; every read the
// cycle after re must equal the image; the hold behaviour and an out-of-range fault are checked.
#include "Vtb_qwen_rt_rom_services.h"
#include "Vtb_qwen_rt_rom_services___024root.h"
#include <cstdio>
#include <cstdint>
#include <random>
#include <vector>
#include <cstring>
static Vtb_qwen_rt_rom_services* t;
static void tick() { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }
static void via_set(uint32_t* arr, int a, int b, bool v) {
    size_t row = a / 8, col = size_t(b) * 8 + a % 8;
    uint32_t& w = arr[row * 67 + col / 32];
    if (v) w |= 1u << (col % 32); else w &= ~(1u << (col % 32));
}
#define R t->rootp
#include "rom_access_bench.hpp"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    t = new Vtb_qwen_rt_rom_services;
    std::mt19937 rng(11);
    t->rst_n = 0; tick(); tick(); t->rst_n = 1; tick();
    const int NS = 50112;
    std::vector<uint32_t> img(size_t(NS) * 8);
    for (auto& x : img) x = rng();
    for (int w = 0; w < NS; w++)
        for (int b = 0; b < 256; b++) via_set(bank_arr(w >> 12), w & 4095, b, (img[size_t(w) * 8 + b / 32] >> (b % 32)) & 1);
    long bad = 0, reads = 0;
    for (int i = 0; i < 20000; i++) {
        int a = rng() % NS;
        t->s_re = 1; t->s_addr = a; tick(); t->s_re = 0; tick(); tick();       // held after the read
        for (int k = 0; k < 8; k++) bad += t->s_q[k] != img[size_t(a) * 8 + k];
        reads++;
    }
    bool s_ok = bad == 0 && !t->s_fault;
    t->s_re = 1; t->s_addr = 13 * 4096; tick(); t->s_re = 0; tick();
    bool s_fault_ok = t->s_fault;
    // embedding
    int toks[8] = {0, 1, 4095, 4096, 50994, 86870, 151000, 151935};
    std::vector<uint8_t> codes(8 * 4096); std::vector<uint16_t> sc(8);
    for (auto& c : codes) c = rng(); for (auto& s : sc) s = rng();
    for (int i = 0; i < 8; i++) {
        uint32_t tok = toks[i];
        for (int j = 0; j < 64; j++)
            for (int k = 0; k < 16; k++) {
                uint32_t v = 0;
                for (int b = 0; b < 4; b++) v |= uint32_t(codes[i * 4096 + j * 64 + 4 * k + b]) << (8 * b);
                R->tb_qwen_rt_rom_services__DOT__u_emb__DOT__codes[size_t(tok) * 64 + j][k] = v;
            }
        R->tb_qwen_rt_rom_services__DOT__u_emb__DOT__scales[tok] = sc[i];
    }
    long ebad = 0;
    for (int i = 0; i < 8; i++) {
        uint32_t tok = toks[i];
        t->e_re = 1; t->e_addr = tok; tick(); t->e_re = 0;
        ebad += t->e_q != sc[i];
        for (int j = 0; j < 64; j++) {
            t->c_re = 1; t->c_addr = tok * 64 + j; tick(); t->c_re = 0;
            for (int k = 0; k < 64; k++) ebad += ((t->c_q[k / 4] >> (8 * (k % 4))) & 0xff) != codes[i * 4096 + j * 64 + k];
        }
    }
    bool e_ok = ebad == 0 && !t->e_fault;
    printf("%s SCALE_BANK reads=%ld mismatched_words=%ld out_of_range_fault=%d\n", s_ok && s_fault_ok ? "PASS" : "FAIL", reads, bad, int(s_fault_ok));
    printf("%s EMBED_ROM tokens=8 code_words=512 scale_reads=8 mismatches=%ld\n", e_ok ? "PASS" : "FAIL", ebad);
    bool all = s_ok && s_fault_ok && e_ok;
    printf("ROM_SERVICES_STANDALONE %s\n", all ? "PASS" : "FAIL");
    return all ? 0 : 1;
}
