#pragma once
#include "s81_native_bf_head_producer.hpp"
#include "s81_minimum_source_bindings.hpp"
#include "Vretn.h"
#include "Vroot.h"
#include "s81_minimum_pair_source.hpp"
#include "s81_native_bf_head_phase_select.hpp"

// ReleasedHeadByteProvider.native_bf_word supplies these nine little-endian
// uint32 words; the factory never reads expected logits or constructs roots.
using DsromS81NativeHeadByteRead=dsrom_s81_minimum::NativeBfHeadRom::Read;
using DsromS81NativeHeadSink=std::function<bool(const dsrom_s81_minimum::NativeBfHeadRoots&)>;
using DsromS81NativeHeadProducer=dsrom_s81_minimum::NativeBfHeadProducer<Vretn,Vroot>;

class DsromS81NativeHeadBinding {
    DsromS81MinimumRuntime& runtime;
    std::array<DsromS81MinimumSourceIo,4> source_ios{};
    unsigned source_rank=0;
    bool rank_scoped=false;
    DsromS81NativeHeadProducer producer;
    bool started=false;
    int owner_stage,owner_rank,owner_pair;
    void require_owner(int s,int r,int p)const {
        if(s!=owner_stage||r!=owner_rank||p!=owner_pair)
            throw std::runtime_error("head raw provider request from foreign runtime pair");
    }
public:
    DsromS81NativeHeadBinding(DsromS81MinimumRuntime& r,Vcut& actual_shared_cut,const DsromS81MinimumSourceIo& io,
        DsromS81NativeHeadByteRead released,DsromS81NativeHeadSink actual_carried_sink,bool install_source=true)
        :runtime(r),producer(r,actual_shared_cut,io.read_word,io.span_lease,std::move(released),std::move(actual_carried_sink)),
         owner_stage(r.stage),owner_rank(r.rank),owner_pair(r.pair) {
        if(install_source)bind_source();
    }
    DsromS81NativeHeadBinding(DsromS81MinimumRuntime& r,Vcut& actual_shared_cut,
        const std::array<DsromS81MinimumSourceIo,4>& rank_inputs,
        DsromS81NativeHeadByteRead released,DsromS81NativeHeadSink actual_carried_sink,bool install_source=true)
        :runtime(r),source_ios(rank_inputs),rank_scoped(true),
         producer(r,actual_shared_cut,[this](uint64_t id,uint32_t address){return source_ios[source_rank].read_word(id,address);},
           [this](uint64_t id,uint32_t address,unsigned words){return source_ios[source_rank].span_lease(id,address,words);},
           std::move(released),std::move(actual_carried_sink)),
         owner_stage(r.stage),owner_rank(r.rank),owner_pair(r.pair) {
        for(const auto& io:source_ios)if(!io.read_word||!io.span_lease)
            throw std::runtime_error("four actual rank-normalized XN homes required");
        if(install_source)bind_source();
    }
    // Install once before shared cold_start. If Cicero already owns a field
    // selector, pass install_source=false and compose the public reads below
    // in his ONE existing bind_native_pair_source closure instead.
    void bind_source() {
        dsrom_s81_minimum::bind_native_pair_source(runtime,
          [this](){return source_selected();},
          [this](unsigned bank,unsigned address){return raw_word(bank,address);},
          [this](unsigned address){return cfg_word(address);});
    }
    bool source_selected()const{return started;}
    dsrom_s81_minimum::NativeBfHeadRom::Word raw_word(unsigned bank,unsigned address)const {
        require_owner(runtime.stage,runtime.rank,runtime.pair);
        return producer.raw_word(bank,address);
    }
    uint64_t cfg_word(unsigned address)const {
        require_owner(runtime.stage,runtime.rank,runtime.pair);
        return producer.cfg_word(address);
    }
    void start(uint64_t actual_identity,uint64_t request_sequence,unsigned rank) {
        if(rank>=4||(!rank_scoped&&(started||rank!=unsigned(runtime.rank))))
            throw std::runtime_error("head rank/source home not enrolled");
        // No substitute input publication: all XN must be actual SourceIo.
        producer.start(actual_identity,request_sequence,rank);source_rank=rank;started=true;
    }
    void advance(){producer.advance();}
    DsromS81MinimumParticipant input_participant(){return producer.input_participant();}
    DsromS81MinimumParticipant return_participant(){return producer.return_participant();}
    // Main Boole469b helper preserves one chosen pre-edge phase through the
    // falling edge. Inactive HEAD cannot touch/eval/reset the borrowed cut.
    DsromS81MinimumParticipant selected_input_participant() {
        return dsrom_s81_minimum::dsrom_s81_select_native_bf_head_phase(runtime,producer.native_cut(),
            [this](){return source_selected();},producer.input_participant());
    }
    DsromS81MinimumParticipant selected_return_participant() {
        return dsrom_s81_minimum::dsrom_s81_select_native_bf_head_phase(runtime,producer.native_cut(),
            [this](){return source_selected();},producer.return_participant());
    }
    void observe_shared_cold_reset(){producer.observe_shared_cold_reset();}
    bool all_roots_accepted()const{return producer.all_roots_accepted();}
    bool snapshot_ready()const{return producer.snapshot_ready();}
};
// Lifetime: keep the returned owner through Runtime/model destruction; its
// registered native participants and host read hooks capture this object.
std::unique_ptr<DsromS81NativeHeadBinding> dsrom_s81_bind_native_bf_head_producer(
    DsromS81MinimumRuntime&,Vcut&,const DsromS81MinimumSourceIo&,
    DsromS81NativeHeadByteRead,DsromS81NativeHeadSink,bool install_source=true);

std::unique_ptr<DsromS81NativeHeadBinding> dsrom_s81_bind_native_bf_head_producer(
    DsromS81MinimumRuntime&,Vcut&,const std::array<DsromS81MinimumSourceIo,4>&,
    DsromS81NativeHeadByteRead,DsromS81NativeHeadSink,bool install_source=true);
