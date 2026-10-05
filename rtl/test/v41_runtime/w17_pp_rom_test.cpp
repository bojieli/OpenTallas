#include "Vtb_w17_pp_rom.h"
#include "verilated.h"
#include "svdpi.h"
#include <unordered_map>
#include <string>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <array>

static std::unordered_map<svScope,int> banks;
static uint32_t word(int bank, int addr, int limb) {
    uint32_t value = 0x9e3779b9u * uint32_t(addr + 1) ^ (0x71028193u * uint32_t(bank+1)) ^ (0x31415927u * uint32_t(limb+1));
    return limb==8 ? value & 0x3ffffu : value;
}
extern "C" void v41rt_rom_register(const char* inst) {
    std::string label(inst ? inst : "");
    if (label.find('_')!=std::string::npos) { puts("FAIL registration retained parity suffix"); exit(2); }
    banks[svGetScope()] = !label.empty() && label.back()=='b';
}
extern "C" void v41rt_rom_read(int addr, svBitVecVal* q) {
    if (!banks.count(svGetScope()) || addr<0 || addr>8191) { puts("FAIL scope/range"); exit(2); }
    int bank=banks.at(svGetScope());
    const char* mutant=getenv("W17_PP_MUTANT");
    if (mutant && !strcmp(mutant,"bank")) bank^=1;
    if (mutant && !strcmp(mutant,"parity")) addr^=1;
    for (int k=0;k<9;k++) q[k]=word(bank,addr,k);
}
int main(int argc,char** argv) {
    Verilated::commandArgs(argc,argv);
    Vtb_w17_pp_rom m;
    m.clk=0; m.ce=0; m.addr=0; m.eval();
    std::array<std::array<uint32_t,9>,8> expected{};
    unsigned checks=0;
    auto tick=[&](int addr, unsigned ce) {
        m.clk=0;m.addr=addr;m.ce=ce;m.eval();
        // Address/enable changes on a falling edge must not produce a read.
        for (int g=0;g<8;g++) for (int k=0;k<9;k++)
            if (m.q[g][k]!=expected[g][k]) { puts("FAIL non-rising edge"); return false; }
        m.clk=1;m.eval();
        for (int g=0;g<8;g++) {
            if ((ce>>g)&1) for (int k=0;k<9;k++) expected[g][k]=word((g%4)/2,2*addr+(g%2),k);
            for (int k=0;k<9;k++) {
                checks++;
                if (m.q[g][k]!=expected[g][k]) { printf("FAIL addr=%d bank=%d parity=%d limb=%d\n",addr,(g%4)/2,g%2,k);return false; }
            }
        }
        return true;
    };
    for (int a=0;a<4096;a++) {
        if (!tick(a,0x55) || !tick(a,0xaa)) return 1; // odd/even alternation on both logical banks
        if (a%17==0 && !tick((a+91)%4096,0)) return 1; // output holds across bubbles
    }
    if (!tick(4095,0xff) || !tick(0,0) || !tick(0,0xff)) return 1;
    printf("PASS checks=%u addresses=4096 logical_banks=2 name_forms=2 max_logical_addr=8191\n",checks);
    return 0;
}
