// Exhaustive gate of ot_qwen_nearhbm_prod against the golden mul on all 2^16 BF16 x 2^8 E4M3 operand pairs.
// Expected: the binary32 product computed by the host (IEEE RNE, gradual underflow, no FTZ: the same operation as
// numpy's float32 multiply in tools/hdc_golden.py mul), zero canonicalised to +0; Inf/NaN/overflow -> fault.
#include "Vot_qwen_nearhbm_prod.h"
#include "verilated.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
static float f_of(uint32_t b) { float f; memcpy(&f, &b, 4); return f; }
static uint32_t b_of(float f) { uint32_t b; memcpy(&b, &f, 4); return b; }
static float fp8(uint8_t k) {
    int s = k >> 7, e = (k >> 3) & 15, m = k & 7;
    double v = (e == 0) ? (m / 8.0) * std::ldexp(1.0, -6) : (1 + m / 8.0) * std::ldexp(1.0, e - 7);
    return (float)(s ? -v : v);
}
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_qwen_nearhbm_prod* t = new Vot_qwen_nearhbm_prod;
    const int LAT = 4;                // registers; the result of input c is readable after edge c + LAT - 1
    t->rst_n = 0; t->clk = 0; t->eval(); t->clk = 1; t->eval(); t->rst_n = 1;
    uint64_t n = 0, bad = 0, faults_expected = 0, faults_seen = 0, exact_checked = 0;
    static uint32_t qa[8], qk[8];
    uint64_t total = 65536ull * 256;
    for (uint64_t c = 0; c < total + LAT; c++) {
        if (c < total) { t->a = (uint16_t)(c >> 8); t->k = (uint8_t)(c & 255); t->valid_in = 1; qa[c % 8] = t->a; qk[c % 8] = t->k; }
        else t->valid_in = 0;
        t->clk = 0; t->eval(); t->clk = 1; t->eval();
        if (c >= LAT - 1 && c - (LAT - 1) < total) {
            uint64_t i = c - (LAT - 1);
            uint32_t a = qa[i % 8], k = qk[i % 8];
            bool nonfin = ((a >> 7) & 0xFF) == 0xFF || (k & 0x7F) == 0x7F;
            float p = f_of(a << 16) * fp8((uint8_t)k);
            bool ovf = !nonfin && std::isinf(p);
            uint32_t exp = (p == 0.0f) ? 0u : b_of(p);
            if (nonfin || ovf) {
                faults_expected++;
                if (t->fault) faults_seen++; else bad++;
                if (t->y != 0) bad++;
            } else {
                // exactness of the reference itself: the double product equals the float product
                if ((double)f_of(a << 16) * (double)fp8((uint8_t)k) != (double)p) { fprintf(stderr, "reference inexact a=%04x k=%02x\n", a, k); return 3; }
                exact_checked++;
                if (t->fault || t->y != exp) {
                    if (bad < 10) fprintf(stderr, "MISMATCH a=%04x k=%02x rtl=%08x fault=%d gold=%08x\n", a, k, t->y, t->fault, exp);
                    bad++;
                }
            }
            if (!t->valid_out) bad++;
            n++;
        }
    }
    printf("{\"unit\": \"ot_qwen_nearhbm_prod\", \"pairs\": %llu, \"finite_pairs_checked\": %llu, \"faults_expected\": %llu, "
           "\"faults_seen\": %llu, \"mismatches\": %llu, \"exhaustive\": true, \"verdict\": \"%s\"}\n",
           (unsigned long long)n, (unsigned long long)exact_checked, (unsigned long long)faults_expected,
           (unsigned long long)faults_seen, (unsigned long long)bad, bad ? "FAIL" : "PASS");
    delete t;
    return bad ? 1 : 0;
}
