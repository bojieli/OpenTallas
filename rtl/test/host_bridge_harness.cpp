// Host bridge for the host-interface simulation tops (rtl/test/tb_host_*.sv).
//
// The harness is the host side of the chip's PCIe-style interface:
//   * host memory: a file mapped MAP_SHARED (+HOSTMEM=<path>), so the runtime
//     (runtime/hdc/device.py) builds rings and prompts in it and reads
//     completions from it directly, as a driver does in pinned DMA memory;
//   * the DMA target: the chip's AXI4 master reads and writes that memory,
//     each access completing +DMA_LAT=<cycles> after it is accepted (the PCIe
//     round trip at the chip clock);
//   * the interrupt controller: a DMA write at or above MSI_BASE is an MSI,
//     recorded rather than stored;
//   * the CPU's register accesses: AXI4-Lite reads and writes of the BAR.
//
// Commands on stdin, one per line, each answered by one line on stdout:
//   w <addr> <data>   register write               -> "ok <cycle>"
//   r <addr>          register read                -> "<value> <cycle>"
//   run <n>           clock until an MSI arrives or n cycles pass
//                                                  -> "msi <count> <data> <cycle>" | "idle <cycle>"
//   cycle             -> "<cycle>"
//   quit
// Numbers are decimal or 0x-prefixed hex.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fcntl.h>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "verilated.h"
// host_top.h (written by the build) includes the Verilated top and defines VTOP
#include "host_top.h"

static const uint64_t MSI_BASE = 0xFEE00000ull;

struct Bridge {
    VTOP* top;
    uint8_t* mem = nullptr;
    uint64_t mem_bytes = 0;
    uint64_t cycle = 0;
    uint64_t dma_lat = 64;
    struct Rd { uint64_t due, addr; };
    struct Wr { uint64_t due; };
    std::deque<Rd> rq;
    std::deque<Wr> bq;
    // captured write address / data (the channels are independent in AXI)
    bool aw_have = false, w_have = false;
    uint64_t aw_addr = 0, w_data = 0;
    uint8_t w_strb = 0;
    uint64_t msi_count = 0;
    uint32_t msi_last = 0;
    bool msi_new = false;

    uint64_t load(uint64_t a) {
        uint64_t v = 0;
        if (a + 8 <= mem_bytes) memcpy(&v, mem + a, 8);
        return v;
    }
    void store(uint64_t a, uint64_t d, uint8_t strb) {
        if (a >= MSI_BASE) {
            uint32_t v = (strb & 0x0F) ? (uint32_t)d : (uint32_t)(d >> 32);
            msi_count++; msi_last = v; msi_new = true;
            return;
        }
        for (int i = 0; i < 8; i++)
            if (((strb >> i) & 1) && a + i < mem_bytes) mem[a + i] = (uint8_t)(d >> (8 * i));
    }

    // One clock: drive the inputs for this cycle from the state, let the
    // combinational readies settle, record the handshakes, then the edge.
    void tick() {
        top->clk = 0;
        // DMA responses
        top->m_arready = 1;
        top->m_awready = !aw_have;
        top->m_wready = !w_have;
        top->m_rvalid = 0; top->m_rresp = 0; top->m_rdata = 0;
        if (!rq.empty() && rq.front().due <= cycle) {
            top->m_rvalid = 1;
            top->m_rdata = load(rq.front().addr);
        }
        top->m_bvalid = 0; top->m_bresp = 0;
        if (!bq.empty() && bq.front().due <= cycle) top->m_bvalid = 1;
        top->eval();
        bool ar = top->m_arvalid && top->m_arready;
        bool aw = top->m_awvalid && top->m_awready;
        bool w = top->m_wvalid && top->m_wready;
        uint64_t ar_addr = top->m_araddr;
        uint64_t awa = top->m_awaddr, wd = top->m_wdata;
        uint8_t ws = top->m_wstrb;
        bool r_done = top->m_rvalid, b_done = top->m_bvalid;
        top->clk = 1;
        top->eval();
        cycle++;
        if (r_done) rq.pop_front();
        if (b_done) bq.pop_front();
        if (ar) rq.push_back({cycle + dma_lat, ar_addr});
        if (aw) { aw_have = true; aw_addr = awa; }
        if (w) { w_have = true; w_data = wd; w_strb = ws; }
        if (aw_have && w_have) {
            store(aw_addr, w_data, w_strb);
            bq.push_back({cycle + dma_lat});
            aw_have = w_have = false;
        }
    }

    void reg_write(uint32_t a, uint32_t d) {
        top->s_awvalid = 1; top->s_awaddr = a; top->s_wvalid = 1; top->s_wdata = d; top->s_bready = 1;
        for (int n = 0; n < 1000; n++) {
            top->clk = 0; top->eval();
            bool hs = top->s_awready;
            tick();
            if (hs) break;
        }
        top->s_awvalid = 0; top->s_wvalid = 0;
        for (int n = 0; n < 1000 && !top->s_bvalid; n++) tick();
        tick();                                  // B handshake
        top->s_bready = 0;
    }
    uint32_t reg_read(uint32_t a) {
        top->s_arvalid = 1; top->s_araddr = a; top->s_rready = 1;
        for (int n = 0; n < 1000; n++) {
            top->clk = 0; top->eval();
            bool hs = top->s_arready;
            tick();
            if (hs) break;
        }
        top->s_arvalid = 0;
        for (int n = 0; n < 1000 && !top->s_rvalid; n++) tick();
        uint32_t v = top->s_rdata;
        tick();
        top->s_rready = 0;
        return v;
    }
};

static uint64_t num(const char* s) { return strtoull(s, nullptr, 0); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const char* path = nullptr;
    uint64_t bytes = 1 << 20, lat = 64;
    for (int i = 1; i < argc; i++) {
        if (!strncmp(argv[i], "+HOSTMEM=", 9)) path = argv[i] + 9;
        if (!strncmp(argv[i], "+HOSTMEM_BYTES=", 15)) bytes = num(argv[i] + 15);
        if (!strncmp(argv[i], "+DMA_LAT=", 9)) lat = num(argv[i] + 9);
    }
    Bridge b;
    b.top = new VTOP;
    b.dma_lat = lat;
    if (path) {
        int fd = open(path, O_RDWR);
        if (fd < 0) { perror("HOSTMEM"); return 2; }
        struct stat st;
        fstat(fd, &st);
        b.mem_bytes = (uint64_t)st.st_size < bytes ? (uint64_t)st.st_size : bytes;
        b.mem = (uint8_t*)mmap(nullptr, b.mem_bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (b.mem == MAP_FAILED) { perror("mmap"); return 2; }
    }
    VTOP* t = b.top;
    t->s_awvalid = t->s_wvalid = t->s_arvalid = t->s_bready = t->s_rready = 0;
    t->rst_n = 0;
    for (int i = 0; i < 8; i++) b.tick();
    t->rst_n = 1;
    for (int i = 0; i < 4; i++) b.tick();
    printf("ready %llu\n", (unsigned long long)b.cycle);
    fflush(stdout);

    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        char cmd[16] = {0}, a1[64] = {0}, a2[64] = {0};
        int n = sscanf(line, "%15s %63s %63s", cmd, a1, a2);
        if (n < 1) continue;
        std::string c(cmd);
        if (c == "w" && n == 3) {
            b.reg_write((uint32_t)num(a1), (uint32_t)num(a2));
            printf("ok %llu\n", (unsigned long long)b.cycle);
        } else if (c == "r" && n == 2) {
            uint32_t v = b.reg_read((uint32_t)num(a1));
            printf("%u %llu\n", v, (unsigned long long)b.cycle);
        } else if (c == "run" && n == 2) {
            uint64_t lim = num(a1);
            b.msi_new = false;
            for (uint64_t k = 0; k < lim && !b.msi_new && !Verilated::gotFinish(); k++) b.tick();
            if (b.msi_new)
                printf("msi %llu %u %llu\n", (unsigned long long)b.msi_count, b.msi_last,
                       (unsigned long long)b.cycle);
            else
                printf("idle %llu\n", (unsigned long long)b.cycle);
        } else if (c == "cycle") {
            printf("%llu\n", (unsigned long long)b.cycle);
        } else if (c == "quit") {
            break;
        } else {
            printf("error %s\n", cmd);
        }
        fflush(stdout);
    }
    t->final();
    delete t;
    return 0;
}
