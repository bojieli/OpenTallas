#pragma once
#include "s81_minimum_embedding.hpp"
#include "s81_minimum_prefix_providers.hpp"
#include <fstream>
#include <cctype>
#include <iterator>
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
        struct BoundaryOperand {unsigned producer,address;std::vector<uint32_t> words;};
        std::vector<BoundaryOperand> boundary;
        unsigned boundary_index=0,boundary_offset=0;
        bool boundary_started=false;

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
        // Read only direct members, never a substring match inside another
        // object. Reject duplicate keys and malformed held metadata. This is
        // private loading logic, not a publication/receipt authority.
        static std::string member(const std::string& json,const std::string& key) {
            size_t i=0;auto ws=[&](){while(i<json.size()&&std::isspace(static_cast<unsigned char>(json[i])))++i;};
            ws();require(i<json.size()&&json[i++]=='{',"pre-I75 metadata object required");
            std::vector<std::string> seen;std::string result;bool found=false;
            for(;;) {
                ws();require(i<json.size(),"truncated pre-I75 metadata");
                if(json[i]=='}'){++i;break;}
                require(json[i++]=='"',"pre-I75 metadata key required");
                const size_t start=i;
                while(i<json.size()&&json[i]!='"') {
                    require(json[i]!='\\'&&static_cast<unsigned char>(json[i])>=32,
                            "escaped pre-I75 metadata key refused");++i;
                }
                require(i<json.size(),"truncated pre-I75 metadata key");
                const std::string name=json.substr(start,i-start);++i;
                for(const auto& old:seen)require(old!=name,"duplicate pre-I75 metadata key");
                seen.push_back(name);ws();require(i<json.size()&&json[i++]==':',"pre-I75 metadata colon required");
                ws();const size_t value=i;int depth=0;bool quoted=false,escape=false;
                for(;i<json.size();++i) {
                    const char c=json[i];
                    if(quoted){if(escape)escape=false;else if(c=='\\')escape=true;else if(c=='"')quoted=false;continue;}
                    if(c=='"'){quoted=true;continue;}
                    if(c=='{'||c=='['){++depth;continue;}
                    if(c=='}'||c==']'){if(depth==0)break;--depth;continue;}
                    if(c==','&&depth==0)break;
                }
                require(!quoted&&depth==0&&i<json.size(),"truncated pre-I75 metadata value");
                size_t end=i;while(end>value&&std::isspace(static_cast<unsigned char>(json[end-1])))--end;
                require(end>value,"empty pre-I75 metadata value");
                if(name==key){result=json.substr(value,end-value);found=true;}
                if(json[i]=='}'){++i;break;}
                require(json[i++]==',',"pre-I75 metadata separator required");
                ws();require(i<json.size()&&json[i]!='}',"trailing pre-I75 metadata comma");
            }
            ws();require(i==json.size()&&found,"missing/trailing pre-I75 metadata member");return result;
        }
        static std::string sha_member(const std::string& json,const std::string& key) {
            const auto value=member(json,key);
            require(value.size()==66&&value.front()=='"'&&value.back()=='"',"pre-I75 SHA256 required");
            const auto sha=value.substr(1,64);
            for(char c:sha)require((c>='0'&&c<='9')||(c>='a'&&c<='f'),"pre-I75 SHA256 encoding");
            return sha;
        }
        void install_sim_only_pre_i75(const std::string& directory) {
            require(enabled&&!started&&!stopped&&boundary.empty()&&runtime.stage==37&&
                    runtime.rank>=0&&runtime.rank<4&&!directory.empty(),"pre-I75 installation context/duplicate");
            std::ifstream file(directory+"/native_h_chain_inputs.json",std::ios::binary);
            require(bool(file),"actual pre-I75 manifest missing");
            const std::string manifest((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
            require(member(manifest,"scope")=="\"produced source operands before native L20.I75 -> L20.I76\""&&
                    member(manifest,"position")=="1048575"&&member(manifest,"token")=="16754"&&
                    member(manifest,"stage")=="37"&&member(manifest,"seed")=="20260930"&&
                    member(manifest,"instructions_completed")=="75"&&
                    member(manifest,"expected_outputs_used")=="false"&&
                    member(manifest,"native_publication_qualified")=="false",
                    "pre-I75 exported source/context/scope differs");
            // a18 exports the five source-file hashes as an OBJECT, not a
            // single digest. Validate each declared canonical provenance pin;
            // none of these hashes supplies native acceptance or a lease.
            const auto source_inputs=member(manifest,"source_inputs_sha256");
            const std::pair<const char*,const char*> source_pins[]={
                {"results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json",
                 "0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480"},
                {"results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json",
                 "47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815"},
                {"results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz",
                 "985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326"},
                {"results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz",
                 "fec91ca041e8b1640292ca06163def706c0d0dab8c5d524ba9e8f611dd925d0f"},
                {"results/uarch/dsrom_native_weight_address_join_20261002/r3/node_bindings.jsonl.gz",
                 "07a9a3ff9a371c4ef3fbe941661105b91da281636674c4045a7b961e81c2b434"}};
            for(const auto& pin:source_pins)
                require(sha_member(source_inputs,pin.first)==pin.second,
                        "pre-I75 source input provenance differs");
            const auto operands=member(manifest,"operands");
            struct Spec {const char* name;unsigned producer,address,count;const char* node;const char* sha;};
            const Spec specs[]={
                {"T",2545,20480,20480,"L20.I74","6221c07f4f6e43f73ad3d59203b695439613fc16a77fe94642fa4806af78b4e0"},
                {"CA",2531,41120,16,"L20.I60","00efbc6799379bee16adbf089be3ec713465142bc42c6c7c9aee099d62aa20dc"},
                {"POA",2528,41088,4,"L20.I57","2a69bea7440499e35ced0ca10a52c48e43f8cdefa5754cb54f8b19f6e97ece23"},
                {"Y",2543,84512,5120,"L20.I72","a6e0b31f76812c358612794889096418e39596048be9dd06139fc66950d0ff12"}};
            std::vector<BoundaryOperand> selected;
            for(const auto& spec:specs) {
                const auto item=member(operands,spec.name);
                require(member(item,"producer")==std::to_string(spec.producer)&&
                        member(item,"address")==std::to_string(spec.address)&&
                        member(item,"count")==std::to_string(spec.count)&&
                        member(item,"bytes_per_rank")==std::to_string(spec.count*4)&&
                        member(item,"source_node")==std::string("\"")+spec.node+"\""&&
                        sha_member(item,"template_sha256")==spec.sha,"pre-I75 canonical source extent differs");
                const auto filename=std::string("I75.")+spec.name+"_rank"+std::to_string(runtime.rank)+".u32";
                const auto pin=sha_member(member(item,"files"),filename);
                selected.push_back({spec.producer,spec.address,load((directory+"/"+filename).c_str(),spec.count*4,pin.c_str())});
            }
            const auto next=member(manifest,"I75"),last=member(manifest,"I76");
            require(member(next,"producer")=="2546"&&sha_member(next,"template_sha256")==
                    "fab801f2bcbcd4cdff06867c95bb963c9d1dd59a7416dd7a5460a4ad3322804d"&&
                    member(last,"producer")=="2547"&&sha_member(last,"template_sha256")==
                    "b697342bd2e9299a0cc2a141a25b26c011f4830af680c74cd7ec21357c5fd820",
                    "pre-I75 native successor source differs");
            for(const auto& operand:selected)
                publication.enroll_literal(operand.producer,{{operand.address,uint32_t(operand.words.size())}});
            boundary=std::move(selected); // descriptors/raw bits only; NO acceptance/ACK/lease
        }
        void prepare_boundary() {
            auto& operand=boundary.at(boundary_index);
            if(!boundary_started) {
                publication.begin(identity,operand.producer); // explicit SIM_ONLY actor admission
                boundary_started=true;
            }
            if(!held) {
                out={};out.vm_valid=1;out.vm_identity=identity;
                out.vm_address=operand.address+boundary_offset;
                count=std::min<unsigned>(16,operand.words.size()-boundary_offset);
                for(unsigned n=0;n<count;++n) {
                    out.vm_data[n]=operand.words.at(boundary_offset+n);
                    auto command=dsrom_s81_reserve_native_scalar_tag(
                        runtime,identity,operand.producer,out.vm_address+n,out.vm_data[n]);
                    publication.native_scalar(operand.producer,command,true);
                }
                held=true;offered=false;
            }
            if(!offered){offered=io.offer(out,count);return;}
            if(!io.visible(out,count))return; // ONLY the same target's matched native ACK
            require(io.span_lease(identity,out.vm_address,count),"SIM_ONLY prefix write lacks matched visible lease");
            held=false;offered=false;boundary_offset+=count;
            if(boundary_offset==operand.words.size()) {
                require(publication.complete(operand.producer)&&
                        io.span_lease(identity,operand.address,operand.words.size()),
                        "SIM_ONLY prefix operand lacks all actual VM ACKs");
                boundary_offset=0;boundary_started=false;++boundary_index;
                finished=boundary_index==boundary.size();
            }
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
                if(stage==3&&!boundary.empty()){prepare_boundary();return;}
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
                    finished=boundary.empty();
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
    // Explicit SIM_ONLY computed-prefix input; no native compute credit. Install before start/threads.
    void install_sim_only_pre_i75(const std::string& directory){state->install_sim_only_pre_i75(directory);}
    void start(){state->start();}
    bool complete() const{return state->enabled&&state->finished&&!fault();}
    bool fault() const{return state->stopped||(state->enabled&&(state->publication.fault()||state->h_sink.fault()));}
    DsromS81MinimumParticipant participant() const {
        auto s=state;
        return {s->boundary.empty()?"target L20 representative initial inputs":
                "target L20 initial inputs + SIM_ONLY pre-I75 actual VM writes",
            [s](const auto&){s->prepare();},
            [s](bool released){s->observe_reset(released);},
            [s](bool released){s->observe_reset(released);},
            [s](){return s->stopped||(s->enabled&&(s->publication.fault()||s->h_sink.fault()));}};
    }
};
} // namespace dsrom_s81_minimum
