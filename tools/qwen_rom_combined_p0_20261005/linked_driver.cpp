// One released P8191 layer consumer/protected-provider protocol case.
// No model/weight engine, inference smoke, host read service or random payload.
// A legacy-header TU probe can reuse existing model objects; it cannot run the
// warm/held/identity case until the actual exposed endpoint ABI is compiled.
#if P0_REUSE_HEADER
#include "Vtb_qwen_rt_kv_stream4.h"
#include "Vtb_qwen_rt_kv_stream4___024root.h"
using Model = Vtb_qwen_rt_kv_stream4;
#define P0_MEMBER(name) tb_qwen_rt_kv_stream4__DOT__##name
#define P0_BACKING u_hbm__DOT__mem
#define P0_SLICES slice
#else
#include "Vjoin.h"
#include "Vjoin___024root.h"
using Model = Vjoin;
#define P0_MEMBER(name) tb_qwen_p0_linked__DOT__##name
#define P0_BACKING u_producer__DOT__u_hbm__DOT__mem
#define P0_SLICES u_consumer__DOT__slice
#endif
#include "clock.hpp"
#include "fixture_expected.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>


#define P0_PATH_EXPAND(name) P0_MEMBER(name)
static uint64_t hash_byte(uint64_t h,uint8_t c) { return (h^c)*1099511628211ULL; }
static uint64_t hash_bytes(const std::vector<uint8_t>& bytes) {
    uint64_t h=14695981039346656037ULL;for(auto c:bytes)h=hash_byte(h,c);return h;
}
constexpr int P=8191, NT=1536;
constexpr size_t ELEMENTS=4194304;
static void need(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
static uint32_t f32(uint8_t c) {
    const uint32_t s=c>>7,e=(c>>3)&15,m=c&7;
    if(e) return (s<<31)|((e+120)<<23)|(m<<20);
    if(m&4) return (s<<31)|(120<<23)|((m&3)<<21);
    if(m&2) return (s<<31)|(119<<23)|((m&1)<<22);
    return (s<<31)|(m?118u<<23:0);
}
static uint8_t code(uint32_t v) {
    uint32_t s=v>>31,e=(v>>23)&255,m=v&0x7fffff;
    if(e==0 && m==0) return uint8_t(s<<7);
    if(e>=121 && e<=135 && !(m&0xfffff)) return uint8_t((s<<7)|((e-120)<<3)|(m>>20));
    if(e==120 && !(m&0x1fffff)) return uint8_t((s<<7)|4|(m>>21));
    if(e==119 && !(m&0x3fffff)) return uint8_t((s<<7)|2|(m>>22));
    if(e==118 && !m) return uint8_t((s<<7)|1);
    throw std::runtime_error("released history value is not exact E4M3");
}
struct Fixture {
    std::vector<uint8_t> history;
    uint8_t k[2][128]{},v[2][128]{};
    Fixture(const char* history_path,const char* token_path) {
        FILE* f=std::fopen(history_path,"rb"); need(f,"history absent");
        std::vector<uint32_t> raw(ELEMENTS);
        size_t count=std::fread(raw.data(),4,raw.size(),f);
        int extra=std::fgetc(f); std::fclose(f);
        need(count==ELEMENTS && extra==EOF,"history extent differs from released P8191");
        history.reserve(ELEMENTS);
        for(auto bits:raw) {auto c=code(bits);need((c&127)!=127,"history nonfinite");history.push_back(c);}
        f=std::fopen(token_path,"r");need(f,"actual token KV fixture absent");
        bool seen[2][2][128]{};char kind;int h,d;unsigned c;
        while(std::fscanf(f," %c %d %d %x",&kind,&h,&d,&c)==4) {
            need((kind=='K'||kind=='V')&&h>=0&&h<2&&d>=0&&d<128&&c<=255&&(c&127)!=127,"invalid token KV row");
            int which=kind=='V';need(!seen[which][h][d],"duplicate token KV");
            seen[which][h][d]=true;(which?v:k)[h][d]=uint8_t(c);
        }
        need(std::feof(f),"malformed actual token KV");std::fclose(f);
        for(auto& family:seen)for(auto& head:family)for(bool value:head)need(value,"missing actual token KV");
        need(hash_bytes(history)==qwen_combined_p0::expected_history_fp8,"released history numerical hash differs");
        uint64_t hash=14695981039346656037ULL;
        for(int kind=0;kind<2;++kind)for(int h=0;h<2;++h)for(int d=0;d<128;++d)hash=hash_byte(hash,(kind?v:k)[h][d]);
        need(hash==qwen_combined_p0::expected_token_K_then_V,"released token numerical hash differs");
    }
};
template<class M> constexpr bool linked_abi=requires(M& m) {
    m.warm_rst_n; m.hold_rows; m.bad_ack_tag; m.join_debt;
    m.join_desc_accepted; m.join_go; m.join_row_take; m.join_row_valid; m.join_bad_ack_seen;
    m.join_desc_committed; m.join_go_committed;
    m.join_write_accepted; m.join_ack_valid;
    m.join_row_sec; m.join_row_layer; m.join_row_data;
};
template<class M> class Session {
    std::unique_ptr<M> top_;
    qwen_combined_p0::Clocks clocks_;
    uint64_t tick_=0, descriptors_=0, go_=0, rows_=0,acks_=0;
    uint64_t bad_ack_seen_=0;
    unsigned bad_debt_before_=0;
    uint64_t h_descriptors_=0,h_go_=0;
    uint64_t writes_=0;
public:
    M& m() {return *top_;}
    explicit Session():top_(new M) {
        m().clk=0;m().hclk=0;m().rst_n=0;m().start=0;m().kvd_v=0;m().kv_we=0;
        m().nx_layer=255;m().layer=0;m().pos=P;m().pos_hint=P;
        m().kv_free=0;m().early_go=0;m().posted_wb=0;m().kvd_pos=P;
        if constexpr(linked_abi<M>) {m().warm_rst_n=1;m().hold_rows=0;m().bad_ack_tag=0;}
        m().eval();
        for(int i=0;i<8;++i) step();
        m().rst_n=1;
        for(int i=0;i<8;++i) step();
    }
    void step(bool expect_fault=false) {
        auto ctl=[&](bool hi){
            if constexpr(linked_abi<M>) if(hi) {h_descriptors_+=m().join_desc_committed;h_go_+=m().join_go_committed;}
            m().hclk=hi;
        };
        auto settle=[&]{m().eval();};
        clocks_.edge(tick_*833333,ctl,[&]{m().clk=0;},settle);
        if constexpr(linked_abi<M>) {
            descriptors_+=m().join_desc_accepted;go_+=m().join_go;
            for(int word=0;word<4;++word) {rows_+=__builtin_popcount(m().join_row_take[word]);acks_+=__builtin_popcount(m().join_ack_valid[word]);}
            for(int word=0;word<4;++word) writes_+=__builtin_popcount(m().join_write_accepted[word]);
            if(m().join_bad_ack_seen) {++bad_ack_seen_;bad_debt_before_=m().join_debt;}
        }
        clocks_.edge(tick_*833333+416666,ctl,[&]{m().clk=1;},settle);
        ++tick_;
        if(!expect_fault)need(!m().fault,"actual linked endpoint fault");
    }
    template<class Predicate> void until(Predicate done,bool expect_fault=false) {
        while(!done())step(expect_fault); // no guessed simulation deadline
    }
    void preload(const Fixture& fixture) {
        auto& mem=m().rootp->P0_PATH_EXPAND(P0_BACKING);
        for(size_t sector=0;sector<ELEMENTS/32;++sector)for(int w=0;w<8;++w) {
            uint32_t bits=0;for(int j=0;j<4;++j)bits|=uint32_t(fixture.history[sector*32+w*4+j])<<(8*j);
            mem[sector][w]=bits;
        }
        auto& slices=m().rootp->P0_PATH_EXPAND(P0_SLICES);
        for(int t=0;t<NT;++t)for(int a=0;a<128;++a)for(int w=0;w<16;++w)slices[t][a][w]=0xa5a5a5a5;
    }
    void start() {m().start=1;step();m().start=0;}
    void token(const Fixture& f,bool corrupt=false) {
        for(int kind=0;kind<2;++kind)for(int h=0;h<2;++h)for(int half=0;half<2;++half) {
            until([&]{return m().kv_write_drained;},corrupt);
            for(int lane=0;lane<64;++lane) {
                int d=half*64+lane;
                uint32_t element=kind==0?2097152+(h*8192+P)*128+d:((h*512+P/16)*128+d)*16+P%16;
                for(int b=0;b<24;++b) {size_t bit=lane*24+b;auto& w=m().kv_waddr[bit/32];w=(w&~(1u<<(bit%32)))|(((element>>b)&1u)<<(bit%32));}
                m().kv_wdata[lane]=f32((kind==0?f.v:f.k)[h][d]);
            }
            m().kv_we=~uint64_t(0);step(corrupt);m().kv_we=0;
            // Actual consumer drain gates each producer write op; no fixed
            // free-ready return and no host-generated write completion.
        }
        m().kvd_v=1;step(corrupt);m().kvd_v=0;
    }
    uint64_t check_token(const Fixture& f) {
        auto& mem=m().rootp->P0_PATH_EXPAND(P0_BACKING);
        auto byte=[&](size_t e){return uint8_t(mem[e/32][(e%32)/4]>>(8*(e%4)));};
        for(int h=0;h<2;++h)for(int d=0;d<128;++d) {
            need(byte(((h*512+P/16)*128+d)*16+P%16)==f.k[h][d],"actual K writeback differs");
            need(byte(2097152+(h*8192+P)*128+d)==f.v[h][d],"actual V writeback differs");
        }
        auto expected=f.history;
        for(int h=0;h<2;++h)for(int d=0;d<128;++d) {
            expected[((h*512+P/16)*128+d)*16+P%16]=f.k[h][d];
            expected[2097152+(h*8192+P)*128+d]=f.v[h][d];
        }
        uint64_t hash=14695981039346656037ULL;
        for(size_t e=0;e<ELEMENTS;++e) {auto actual=byte(e);need(actual==expected[e],"actual backing changed outside token or differs");hash=hash_byte(hash,actual);}
        need(hash==qwen_combined_p0::expected_backing_after_ACK,"actual final backing numerical hash differs");
        return hash;
    }
    uint64_t check_slices(const Fixture& f) {
        std::vector<uint8_t> expected(size_t(NT)*128*64,0xa5);
        auto put=[&](int tile,int local,int b,uint8_t value){expected[(size_t(tile)*128+local)*64+b]=value;};
        for(int h=0;h<2;++h)for(int t=0;t<512;++t)for(int d=0;d<128;++d)for(int lane=0;lane<16;++lane) {
            int p=t*16+lane,g=(t%48)*128+d;
            uint8_t c=p==P?f.k[h][d]:f.history[((h*512+t)*128+d)*16+lane];
            put(g/4,(t/48)*2+h,(g%4)*16+lane,c);
        }
        for(int h=0;h<2;++h)for(int p=0;p<8192;++p)for(int q=0;q<8;++q)for(int lane=0;lane<16;++lane) {
            int g=q*512+p%512;
            uint8_t c=p==P?f.v[h][q*16+lane]:f.history[2097152+(h*8192+p)*128+q*16+lane];
            put(g/4,22+(p/512)*2+h,(g%4)*16+lane,c);
        }
        auto& slices=m().rootp->P0_PATH_EXPAND(P0_SLICES);
        uint64_t hash=14695981039346656037ULL;
        for(int t=0;t<NT;++t)for(int a=0;a<128;++a)for(int b=0;b<64;++b) {
            uint8_t actual=slices[t][a][b/4]>>(8*(b%4));
            need(actual==expected[(size_t(t)*128+a)*64+b],"actual masked slice differs from released history/token");
            hash=hash_byte(hash,actual);
        }
        need(hash==qwen_combined_p0::expected_registered_slices,"actual registered slice numerical hash differs");
        return hash;
    }
    void released_join(const Fixture& fixture) {
        if constexpr(linked_abi<M>) {
            preload(fixture);m().hold_rows=1;auto begin=tick_;auto hbegin=clocks_.controller_rises();start();
            until([&]{for(int w=0;w<4;++w)if(m().join_row_valid[w])return true;return false;});
            auto first_row=tick_;auto row_count=rows_;
            // Snapshot the existing producer output registers, not a new row buffer.
            std::array<uint32_t,4> held_valid{};
            std::array<uint32_t,68> held_sec{};
            std::array<uint32_t,32> held_layer{};
            std::array<uint32_t,1024> held_data{};
            for(int w=0;w<4;++w)held_valid[w]=m().join_row_valid[w];
            for(int w=0;w<68;++w)held_sec[w]=m().join_row_sec[w];
            for(int w=0;w<32;++w)held_layer[w]=m().join_row_layer[w];
            for(int w=0;w<1024;++w)held_data[w]=m().join_row_data[w];
            for(int i=0;i<24;++i) {
                step();
                for(int pc=0;pc<128;++pc)if((held_valid[pc/32]>>(pc%32))&1) {
                    need((m().join_row_valid[pc/32]>>(pc%32))&1,"held row lost valid");
                    for(int b=0;b<17;++b) {int bit=pc*17+b;need(((m().join_row_sec[bit/32]^held_sec[bit/32])>>(bit%32)&1)==0,"held row sector changed");}
                    need(((m().join_row_layer[pc/4]^held_layer[pc/4])>>(8*(pc%4))&255)==0,"held row layer changed");
                    for(int w=0;w<8;++w)need(m().join_row_data[pc*8+w]==held_data[pc*8+w],"held row payload changed");
                }
            }
            need(rows_==row_count,"held row retired without actual consumer pop");
            m().hold_rows=0;token(fixture);
            // Pause only after every real producer write acceptance. This
            // cannot revoke a caller's already-issued registered pulse.
            until([&]{return writes_==136;});
            need(m().wb_busy&&m().join_debt>0,"warm stimulus needs real accepted outstanding ACK debt");
            auto warm_begin=tick_;auto warm_debt=m().join_debt;
            m().warm_rst_n=0;
            for(int i=0;i<24;++i)step();
            auto warm_end=tick_;m().warm_rst_n=1;
            until([&]{return m().kv_ok&&m().kv_write_drained&&!m().wb_busy&&m().join_debt==0;});
            for(int i=0;i<3;++i)step(); // existing registered slice visibility
            need(descriptors_==1&&go_==1,"actual command/GO count differs");
            need(h_descriptors_==1&&h_go_==1,"protected descriptor/GO did not commit once to real controllers");
            need(writes_==136&&acks_==136,"actual K128/V8 acceptance/ACK count differs");
            auto drained=tick_;
            auto backing_hash=check_token(fixture),slice_hash=check_slices(fixture);
            std::printf("{\"case\":\"released_P8191_L0_rank0\",\"core_edges\":%llu,\"controller_edges\":%llu,\"first_row_core_edge\":%llu,\"warm_begin_core_edge\":%llu,\"warm_end_core_edge\":%llu,\"drain_core_edge\":%llu,\"warm_begin_debt\":%u,\"fill_cycles\":%u,\"fill_sectors\":%u,\"write_sectors\":%u,\"response_stall\":%u,\"write_latency_max\":%u,\"backing_fnv1a64\":\"%016llx\",\"slice_fnv1a64\":\"%016llx\",\"full_token\":false,\"physical_qualified\":false}\n",
                (unsigned long long)(tick_-begin),(unsigned long long)(clocks_.controller_rises()-hbegin),
                (unsigned long long)(first_row-begin),(unsigned long long)(warm_begin-begin),(unsigned long long)(warm_end-begin),(unsigned long long)(drained-begin),
                unsigned(warm_debt),unsigned(m().st_fill_cycles),unsigned(m().st_fill_sectors),unsigned(m().st_wr_sectors),unsigned(m().st_rsp_stall),unsigned(m().st_wr_lat_max),
                (unsigned long long)backing_hash,(unsigned long long)slice_hash);
            std::printf("PASS_RELEASED_P8191_LINKED_JOIN core_edges=%llu controller_edges=%llu descriptor=%llu go=%llu h_descriptor=%llu h_go=%llu rows=%llu ACK=%llu debt=%u warm_held=1\n",
                (unsigned long long)tick_,(unsigned long long)clocks_.controller_rises(),
                (unsigned long long)descriptors_,(unsigned long long)go_,(unsigned long long)h_descriptors_,(unsigned long long)h_go_,(unsigned long long)rows_,(unsigned long long)acks_,unsigned(m().join_debt));
        } else throw std::runtime_error("compiled producer ABI lacks real warm/held/ACK seam; no substitute run");
    }
    void bad_ack(const Fixture& fixture) {
        if constexpr(linked_abi<M>) {
            preload(fixture);start();
            // The first real ACK's write marker is corrupted at the existing
            // receiver boundary. Accepted debt must survive the rejected tag.
            m().bad_ack_tag=1;
            // One actual V64 fragment forms two sectors. Do not issue another
            // dependent op after the deliberately rejected ACK blocks drain.
            for(int half=0;half<1;++half) {
                until([&]{return m().kv_write_drained;},true);
                for(int lane=0;lane<64;++lane) {
                    int d=half*64+lane;uint32_t e=2097152+P*128+d;
                    for(int b=0;b<24;++b) {size_t bit=lane*24+b;auto& w=m().kv_waddr[bit/32];w=(w&~(1u<<(bit%32)))|(((e>>b)&1u)<<(bit%32));}
                    m().kv_wdata[lane]=f32(fixture.v[0][d]);
                }
                m().kv_we=~uint64_t(0);step(true);m().kv_we=0;
            }
            until([&]{return bad_ack_seen_>0||m().fault;},true);
            unsigned before=bad_debt_before_;need(before>0&&bad_ack_seen_>0,"mismatched ACK had no sampled accepted debt");
            need(m().fault&&(m().fault_code&4),"consumer accepted mismatched ACK identity");
            need(m().join_debt>=before&&m().wb_busy,"mismatched ACK released actual debt");
            std::printf("PASS_RELEASED_P8191_ACK_IDENTITY_REJECT debt_before=%u debt_after=%u fault=%04x\n",before,unsigned(m().join_debt),unsigned(m().fault_code));
        } else throw std::runtime_error("compiled producer ABI lacks ACK identity test seam");
    }
};
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--compile-probe") {
            std::printf("PASS_DRIVER_TU_LINK linked_endpoint_ABI=%d runtime_exercised=0\n",int(linked_abi<Model>));return 0;
        }
        need(argc==3,"usage: linked_driver HISTORY_BIN ACTUAL_TOKEN_KV_HEX");
        Fixture fixture(argv[1],argv[2]);
        {Session<Model> session;session.released_join(fixture);}
        {Session<Model> session;session.bad_ack(fixture);}
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"FAIL_LINKED_JOIN %s\n",e.what());return 1;}
}
