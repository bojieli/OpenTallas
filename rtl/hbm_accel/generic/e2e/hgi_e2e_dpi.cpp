// hgi-e2e (2026-10-09): the die-level harness's memories and golden scoreboard (DPI-C, Verilator).
//
// MODELS (labelled as such in every report):
//   VM   262,144 FP32 words (the HGI VM's address space); packet clients and synchronous ports both land here.
//   HBM  a sparse 40-bit byte space of 32 B sectors, loaded with the byte ranges the layer touches (hbm.bin) and the
//        program image at image_base.
// GOLDEN (tools/hgi_e2e/export.py -> prep -> recs.txt): one entry per record the in-order CP dispatches, in dispatch
// order: unit, header, effective base / n of each operand, the simulator's VM / HBM writes of that record.
//   e2e_dispatch   the CP's dispatch (unit, header, effective descriptors, n) == the golden record k, field for field
//   e2e_stub_retire   a STUB unit retires record k: its golden writes are applied (replay; the stub computes nothing)
//   e2e_real_retire   a REAL unit retired record k: every golden-written VM word / HBM byte must already hold the
//                  golden value, and every word the unit wrote during k must be in the golden write set
//   e2e_finish     whole-VM compare with the golden final VM, every golden HBM write range compared, per-record log
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <map>
#include "svdpi.h"

static const int VMW = 1 << 18;
static uint32_t vm[VMW];
static std::vector<uint32_t> vm_final;
static std::unordered_map<uint64_t, std::vector<uint8_t>> hbm;   // sector index -> 32 bytes
static std::string dir;
static FILE* logf = nullptr;

struct Op { bool p; uint64_t base; uint32_t n; };
struct Rec {
    int k, unit, op; uint32_t hdr[4]; Op o[7]; double cost; uint64_t vm_off, vm_n, hbm_off, hbm_n; double s2s, s2e, s2d;
    std::string tag;
    long long disp = -1, ret = -1; int real = 0, mism = 0, stray = 0, dmism = 0, checked = 0;
};
static std::vector<Rec> recs;
static std::vector<uint32_t> vmw;        // golden VM writes {addr, value} pairs
static std::vector<uint8_t> hbmw;        // golden HBM writes {u64 addr, u64 len, bytes}
static int ndisp = 0, nerr_disp = 0, unloaded_hbm = 0, n_ret = 0;
static std::unordered_map<int, std::unordered_set<uint32_t>> wrote;   // unit -> VM words written since its dispatch
static std::unordered_set<int> skip_final;                            // VM words excluded from the final compare

static std::vector<uint8_t>& sector(uint64_t s) {
    auto it = hbm.find(s);
    if (it == hbm.end()) { auto& v = hbm[s]; v.assign(32, 0); return v; }
    return it->second;
}

static bool read_file(const std::string& p, std::vector<uint8_t>& out) {
    FILE* f = fopen(p.c_str(), "rb");
    if (!f) return false;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    out.resize(n);
    size_t r = n ? fread(out.data(), 1, n, f) : 0;
    fclose(f);
    return (long)r == n;
}

static void hbm_load(uint64_t a, const uint8_t* p, uint64_t n) {
    for (uint64_t i = 0; i < n; i++) sector((a + i) >> 5)[(a + i) & 31] = p[i];
}

extern "C" int e2e_init(const char* d, const char* outp) {
    dir = d;
    std::vector<uint8_t> b;
    if (!read_file(dir + "/vm0.bin", b) || b.size() != 4u * VMW) { fprintf(stderr, "E2E: vm0.bin\n"); return -1; }
    memcpy(vm, b.data(), 4u * VMW);
    if (!read_file(dir + "/vm_final.bin", b) || b.size() != 4u * VMW) { fprintf(stderr, "E2E: vm_final.bin\n"); return -1; }
    vm_final.resize(VMW); memcpy(vm_final.data(), b.data(), 4u * VMW);
    if (!read_file(dir + "/hbm.bin", b)) { fprintf(stderr, "E2E: hbm.bin\n"); return -1; }
    for (size_t o = 0; o + 16 <= b.size();) {
        uint64_t a, n; memcpy(&a, &b[o], 8); memcpy(&n, &b[o + 8], 8); o += 16;
        hbm_load(a, &b[o], n); o += n;
    }
    // the image (+ the harness's appended CTL.END, if any) at its base
    FILE* f = fopen((dir + "/prep.txt").c_str(), "r");
    if (!f) { fprintf(stderr, "E2E: prep.txt\n"); return -1; }
    unsigned long long ibase; char ipath[512];
    if (fscanf(f, "%llu %511s", &ibase, ipath) != 2) return -1;
    if (!read_file(dir + "/" + ipath, b)) { fprintf(stderr, "E2E: image\n"); return -1; }
    hbm_load(ibase, b.data(), b.size());
    int nskip; if (fscanf(f, "%d", &nskip) != 1) return -1;
    for (int i = 0; i < nskip; i++) { unsigned a, v; if (fscanf(f, "%u %u", &a, &v) != 2) return -1; vm[a] = v; skip_final.insert(a); }
    fclose(f);
    if (!read_file(dir + "/vmw.bin", b)) return -1;
    vmw.resize(b.size() / 4); memcpy(vmw.data(), b.data(), b.size());
    if (!read_file(dir + "/hbmw.bin", hbmw)) return -1;
    f = fopen((dir + "/recs.txt").c_str(), "r");
    if (!f) { fprintf(stderr, "E2E: recs.txt\n"); return -1; }
    char tag[256];
    while (true) {
        Rec r;
        if (fscanf(f, "%d %d %d %x %x %x %x", &r.k, &r.unit, &r.op, &r.hdr[3], &r.hdr[2], &r.hdr[1], &r.hdr[0]) != 7) break;
        for (int j = 0; j < 7; j++) { int p; unsigned long long bs; unsigned n;
            if (fscanf(f, "%d %llx %u", &p, &bs, &n) != 3) return -1; r.o[j] = {p != 0, bs, n}; }
        unsigned long long vo, vn, ho, hn;
        if (fscanf(f, "%lf %llu %llu %llu %llu %lf %lf %lf %255s", &r.cost, &vo, &vn, &ho, &hn, &r.s2d, &r.s2s, &r.s2e, tag) != 9) return -1;
        r.vm_off = vo; r.vm_n = vn; r.hbm_off = ho; r.hbm_n = hn; r.tag = tag;
        recs.push_back(r);
    }
    fclose(f);
    logf = fopen(outp, "w");
    fprintf(stderr, "E2E: %zu golden records, %zu HBM sectors loaded\n", recs.size(), hbm.size());
    return (int)recs.size();
}

// ------------------------------------------------------------------------------------------------ memories
extern "C" void e2e_vm_sector(int unit, int sec, svBit we, const svBitVecVal* wd, const svBitVecVal* mask, svBitVecVal* rd) {
    if (sec < 0 || sec >= VMW / 8) { for (int i = 0; i < 8; i++) rd[i] = 0xDEADBEEF; return; }
    for (int i = 0; i < 8; i++) {
        uint32_t a = sec * 8 + i;
        if (we) {
            uint32_t m = (mask[0] >> (4 * i)) & 0xF;
            if (m == 0xF) { vm[a] = wd[i]; wrote[unit].insert(a); }
            rd[i] = 0;
        } else rd[i] = vm[a];
    }
}
extern "C" int e2e_vm_rd(int a) { return (a >= 0 && a < VMW) ? (int)vm[a] : (int)0xDEADBEEF; }
extern "C" void e2e_vm_wr(int unit, int a, int v) { if (a >= 0 && a < VMW) { vm[a] = (uint32_t)v; wrote[unit].insert(a); } }

extern "C" void e2e_hbm_sector(long long addr, svBit we, const svBitVecVal* wd, const svBitVecVal* strb, svBitVecVal* rd) {
    uint64_t s = (uint64_t)addr >> 5;
    bool known = hbm.count(s) != 0;
    auto& v = sector(s);
    if (we) {
        for (int i = 0; i < 32; i++) if ((strb[0] >> i) & 1) v[i] = (wd[i / 4] >> (8 * (i % 4))) & 0xFF;
        for (int i = 0; i < 8; i++) rd[i] = 0;
    } else {
        if (!known) unloaded_hbm++;
        for (int i = 0; i < 8; i++) rd[i] = v[4 * i] | v[4 * i + 1] << 8 | v[4 * i + 2] << 16 | (uint32_t)v[4 * i + 3] << 24;
    }
}

// ------------------------------------------------------------------------------------------------ scoreboard
static uint32_t bits(const svBitVecVal* v, int lsb, int w) {
    uint64_t r = 0;
    for (int i = 0; i < w; i++) r |= (uint64_t)((v[(lsb + i) >> 5] >> ((lsb + i) & 31)) & 1) << i;
    return (uint32_t)r;
}
static uint64_t bits64(const svBitVecVal* v, int lsb, int w) {
    uint64_t r = 0;
    for (int i = 0; i < w; i++) r |= (uint64_t)((v[(lsb + i) >> 5] >> ((lsb + i) & 31)) & 1) << i;
    return r;
}

extern "C" int e2e_dispatch(int unit, const svBitVecVal* hdr, const svBitVecVal* desc, const svBitVecVal* n, long long cyc) {
    int k = ndisp++;
    if (k >= (int)recs.size()) { fprintf(stderr, "E2E DISPATCH %d: extra dispatch unit %d\n", k, unit); nerr_disp++; return -1; }
    Rec& r = recs[k];
    r.disp = cyc;
    int bad = 0;
    if (unit != r.unit) bad |= 1;
    for (int i = 0; i < 4; i++) if (hdr[i] != r.hdr[i]) bad |= 2;
    for (int j = 0; j < 7; j++) {
        if (!r.o[j].p) continue;
        uint64_t b = bits64(desc, j * 256 + 8, 40);
        uint32_t nn = bits(n, j * 21, 21);
        if (b != r.o[j].base) bad |= 4 << j;
        if (nn != r.o[j].n) bad |= 0x200 << j;
    }
    if (bad) {
        r.dmism = bad; nerr_disp++;
        if (nerr_disp < 20) {
            fprintf(stderr, "E2E DISPATCH %d (%s) MISMATCH %x: unit %d/%d hdr %08x%08x%08x%08x/%08x%08x%08x%08x\n", k, r.tag.c_str(), bad,
                    unit, r.unit, hdr[3], hdr[2], hdr[1], hdr[0], r.hdr[3], r.hdr[2], r.hdr[1], r.hdr[0]);
            for (int j = 0; j < 7; j++) if (r.o[j].p)
                fprintf(stderr, "    op %d base %llx/%llx n %u/%u\n", j, (unsigned long long)bits64(desc, j * 256 + 8, 40),
                        (unsigned long long)r.o[j].base, bits(n, j * 21, 21), r.o[j].n);
        }
    }
    wrote[unit].clear();
    return k;
}

extern "C" int e2e_cost(int k) { return (k >= 0 && k < (int)recs.size()) ? (int)(recs[k].cost + 0.5) : 1; }
extern "C" int e2e_unit_of(int k) { return (k >= 0 && k < (int)recs.size()) ? recs[k].unit : -1; }

static void apply(const Rec& r) {
    for (uint64_t i = 0; i < r.vm_n; i++) vm[vmw[2 * (r.vm_off + i)]] = vmw[2 * (r.vm_off + i) + 1];
    size_t o = r.hbm_off;
    for (uint64_t i = 0; i < r.hbm_n; i++) {
        uint64_t a, n; memcpy(&a, &hbmw[o], 8); memcpy(&n, &hbmw[o + 8], 8); o += 16;
        hbm_load(a, &hbmw[o], n); o += n;
    }
}

extern "C" void e2e_stub_retire(int k, long long cyc) {
    if (k < 0 || k >= (int)recs.size()) return;
    Rec& r = recs[k];
    r.ret = cyc; r.real = 0; n_ret++;
    apply(r);
}

extern "C" int e2e_real_retire(int k, long long cyc) {
    if (k < 0 || k >= (int)recs.size()) return 1;
    Rec& r = recs[k];
    r.ret = cyc; r.real = 1; n_ret++;
    std::unordered_set<uint32_t> gold;
    int bad = 0;
    for (uint64_t i = 0; i < r.vm_n; i++) {
        uint32_t a = vmw[2 * (r.vm_off + i)], v = vmw[2 * (r.vm_off + i) + 1];
        gold.insert(a);
        if (vm[a] != v) { if (bad < 8) fprintf(stderr, "E2E REAL %d (%s) VM[%u] = %08x golden %08x\n", k, r.tag.c_str(), a, vm[a], v); bad++; }
    }
    size_t o = r.hbm_off;
    for (uint64_t i = 0; i < r.hbm_n; i++) {
        uint64_t a, n; memcpy(&a, &hbmw[o], 8); memcpy(&n, &hbmw[o + 8], 8); o += 16;
        for (uint64_t j = 0; j < n; j++) {
            uint8_t g = hbmw[o + j], h = sector((a + j) >> 5)[(a + j) & 31];
            if (g != h) { if (bad < 8) fprintf(stderr, "E2E REAL %d (%s) HBM[%llx] = %02x golden %02x\n", k, r.tag.c_str(), (unsigned long long)(a + j), h, g); bad++; }
        }
        o += n;
    }
    int stray = 0;
    for (uint32_t a : wrote[r.unit]) if (!gold.count(a) && vm[a] != vm_final[a]) stray++;
    r.mism = bad; r.stray = stray; r.checked = (int)(r.vm_n);
    return bad + stray;
}

extern "C" int e2e_finish(long long cyc, int token, int status) {
    int vbad = 0;
    for (int a = 0; a < VMW; a++) if (!skip_final.count(a) && vm[a] != vm_final[a]) {
        if (vbad < 8) fprintf(stderr, "E2E FINAL VM[%d] = %08x golden %08x\n", a, vm[a], vm_final[a]);
        vbad++;
    }
    int hbad = 0;
    // final HBM: the last golden write of each byte
    std::map<uint64_t, uint8_t> last;
    for (const Rec& r : recs) {
        size_t o = r.hbm_off;
        for (uint64_t i = 0; i < r.hbm_n; i++) {
            uint64_t a, n; memcpy(&a, &hbmw[o], 8); memcpy(&n, &hbmw[o + 8], 8); o += 16;
            for (uint64_t j = 0; j < n; j++) last[a + j] = hbmw[o + j];
            o += n;
        }
    }
    for (auto& kv : last) if (sector(kv.first >> 5)[kv.first & 31] != kv.second) hbad++;
    if (logf) {
        fprintf(logf, "# k unit op tag real dispatch retire cost s2_disp s2_start s2_end dispatch_mismatch vm_checked mismatch stray\n");
        for (const Rec& r : recs)
            fprintf(logf, "%d %d %d %s %d %lld %lld %.1f %.1f %.1f %.1f %x %d %d %d\n", r.k, r.unit, r.op, r.tag.c_str(), r.real,
                    r.disp, r.ret, r.cost, r.s2d, r.s2s, r.s2e, r.dmism, r.checked, r.mism, r.stray);
        fprintf(logf, "SUMMARY cycles %lld token %d status %d dispatched %d/%zu retired %d dispatch_mismatch %d final_vm_mismatch %d "
                      "final_hbm_mismatch %d unloaded_hbm_reads %d\n", cyc, token, status, ndisp, recs.size(), n_ret, nerr_disp,
                vbad, hbad, unloaded_hbm);
        fclose(logf); logf = nullptr;
    }
    fprintf(stderr, "E2E SUMMARY cycles %lld token %d status %d dispatched %d/%zu dispatch_mismatch %d final_vm_mismatch %d final_hbm_mismatch %d unloaded_hbm_reads %d\n",
            cyc, token, status, ndisp, recs.size(), nerr_disp, vbad, hbad, unloaded_hbm);
    return nerr_disp + vbad + hbad;
}
