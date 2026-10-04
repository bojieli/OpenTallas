#pragma once
#include "s81_minimum_embedding.hpp"
#include "s81_minimum_prefix_providers.hpp"
#include <fstream>
#include <openssl/sha.h>

namespace dsrom_s81_minimum {
// Goodall 6b443: seeded representative L20 entry at position 1048575,
// token 16754. These are INITIAL inputs, not prompt-prefill evidence. No
// dense VM, current KV, later-layer carry, logits or expected outputs enter.
// Opt-in only. Caller borrows the existing target sink and SourceIo, installs
// participant(), then calls start() AFTER the shared cold fence/context bind.
// Caller keeps the native target bank as its sole clock/ACK owner and replaces
// the old bootstrap launch for this entry. Link the host caller with -lcrypto.
class DsromS81MinimumTargetEntry {
    struct State {
        DsromS81MinimumRuntime& runtime;
        uint64_t identity;
        PrefixPublication& publication;
        DsromS81MinimumSourceTags tags;
        DsromS81MinimumSourceIo io;
        DsromS81EmbeddingSink h_sink;
        std::vector<uint32_t> h,pf;
        bool enabled,started=false,stopped=false,held=false,offered=false,finished=false;
        unsigned stage=0,offset=0,count=0;
        S81EmbeddingOutput out{};
        static void require(bool ok,const char* why) {
            if(!ok)throw std::runtime_error(why);
        }
        static std::vector<uint32_t> load(const char* path,size_t size,const char* pin) {
            std::ifstream file(path,std::ios::binary);
            require(bool(file),"target entry input missing");
            std::vector<unsigned char> bytes(size);
            file.read(reinterpret_cast<char*>(bytes.data()),size);
            require(size_t(file.gcount())==size&&file.peek()==std::char_traits<char>::eof(),
                    "target entry input size differs from locator");
            unsigned char digest[SHA256_DIGEST_LENGTH];
            require(SHA256(bytes.data(),bytes.size(),digest)!=nullptr,"target entry SHA256 failed");
            static constexpr char hex[]="0123456789abcdef";
            std::string sha;
            for(auto b:digest){sha+=hex[b>>4];sha+=hex[b&15];}
            require(sha==pin,"target entry bytes differ from Goodall locator");
            std::vector<uint32_t> words(size/4);
            for(size_t i=0;i<words.size();++i)
                words[i]=uint32_t(bytes[4*i])|(uint32_t(bytes[4*i+1])<<8)|
                    (uint32_t(bytes[4*i+2])<<16)|(uint32_t(bytes[4*i+3])<<24);
            return words; // raw little-endian F32 bits; no arithmetic
        }
        State(DsromS81MinimumRuntime& r,uint64_t id,PrefixPublication& p,
              DsromS81MinimumSourceTags t,DsromS81MinimumSourceIo i,
              DsromS81EmbeddingSink sink,bool select):runtime(r),identity(id),
              publication(p),tags(std::move(t)),io(std::move(i)),h_sink(std::move(sink)),enabled(select) {
            if(!enabled)return;
            require(id<(1ull<<47)&&tags.record&&tags.scalar_accept&&io.offer&&io.visible&&
                    io.span_lease&&h_sink.offer&&h_sink.visible&&h_sink.fault,
                    "target entry requires existing native VM/tag/ACK bindings");
            h=load("/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L20_r0/io.h_in.bin",
                   81920,"a00c7f2922f58f7d2d694dc5397f425028f0aad2af2273e2969fc29184c17161");
            pf=load("/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L20_r0/io.pre_in.bin",
                    16,"dd0440a949965c14524ecc3b0cb500fc900236b8a3e5ae2f14a4590b4ccd46da");
        }
        void start() {
            try {
                require(enabled&&!started&&!stopped&&runtime.identity&&*runtime.identity==identity,
                        "target entry start requires opted-in actual context after shared cold fence");
                // Explicit fixture writer admission; neither begin creates an
                // acceptance nor an ACK. Existing source tags own all writes.
                publication.begin(identity,PrefixPublication::PF);
                publication.begin(identity,PrefixPublication::SSX);
                started=true;
            }catch(...){stopped=true;throw;}
        }
        void prepare() {
            if(!enabled||!started||finished||stopped)return;
            try {
                require(runtime.identity&&*runtime.identity==identity&&!h_sink.fault()&&
                        !publication.fault(),"target entry lost actual context or native target fault");
                if(!held) {
                    out={};out.vm_valid=1;out.vm_identity=identity;
                    if(stage==0) {
                        // Match existing sink/reader order: four 5120-word
                        // homes interleaved by 16-scalar batch, not a linear
                        // address sweep. Payload remains at its source address.
                        const unsigned batch=offset/16;
                        out.vm_address=(batch%4)*5120+(batch/4)*16;count=16;
                        for(unsigned n=0;n<count;++n)out.vm_data[n]=h.at(out.vm_address+n);
                    }else {
                        out.vm_address=stage==1?41152:40960;count=stage==1?4:1;
                        for(unsigned n=0;n<count;++n)out.vm_data[n]=stage==1?pf.at(n):0x46103308u;
                        const unsigned producer=stage==1?PrefixPublication::PF:PrefixPublication::SSX;
                        for(unsigned n=0;n<count;++n) {
                            auto command=dsrom_s81_reserve_native_scalar_tag(
                                runtime,identity,producer,out.vm_address+n,out.vm_data[n]);
                            publication.native_scalar(producer,command,true);
                        }
                    }
                    held=true;offered=false;
                }
                if(!offered) {
                    offered=stage==0?h_sink.offer(out):io.offer(out,count);
                    return; // admission cannot count as visibility
                }
                if(!(stage==0?h_sink.visible(out):io.visible(out,count)))return;
                require(io.span_lease(identity,out.vm_address,count),
                        "target entry matched visibility lacks source lease");
                held=false;offered=false;
                if(stage==0) {offset+=count;if(offset==h.size())++stage;}
                else ++stage;
                if(stage==3) {
                    require(publication.complete(PrefixPublication::PF)&&
                            publication.complete(PrefixPublication::SSX)&&
                            io.span_lease(identity,0,20480)&&io.span_lease(identity,41152,4)&&
                            io.span_lease(identity,40960,1),"target entry lacks all native input ACKs");
                    finished=true;
                }
            }catch(...){stopped=true;throw;}
        }
        void observe_reset(bool released) {
            if(enabled&&started&&!released){stopped=true;throw std::runtime_error("reset during target entry publication");}
        }
    };
    std::shared_ptr<State> state;
public:
    DsromS81MinimumTargetEntry(DsromS81MinimumRuntime& runtime,uint64_t identity,
        PrefixPublication& publication,const DsromS81MinimumSourceTags& tags,
        const DsromS81MinimumSourceIo& io,DsromS81EmbeddingSink h_sink,bool enable=false)
        :state(std::make_shared<State>(runtime,identity,publication,tags,io,std::move(h_sink),enable)) {}
    void start(){state->start();}
    bool complete() const{return state->enabled&&state->finished&&!fault();}
    bool fault() const{return state->stopped||(state->enabled&&(state->publication.fault()||state->h_sink.fault()));}
    DsromS81MinimumParticipant participant() const {
        auto s=state;
        return {"target L20 representative initial inputs",
            [s](const auto&){s->prepare();},
            [s](bool released){s->observe_reset(released);},
            [s](bool released){s->observe_reset(released);},
            [s](){return s->stopped||(s->enabled&&(s->publication.fault()||s->h_sink.fault()));}};
    }
};
} // namespace dsrom_s81_minimum
