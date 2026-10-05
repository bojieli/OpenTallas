#pragma once
#include "s81_minimum_runtime.hpp"
#include "VDsromS81IndexHbm.h"
#include <memory>
#include <stdexcept>
namespace dsrom_s81_minimum {
struct IndexHbmPortTraffic {
 uint64_t accepted_read_beats=0,delivered_read_beats=0,accepted_write_beats=0,
          accepted_write_bytes=0,write_done=0,migration_read_beats=0,migration_delivered_beats=0;
 std::optional<long> first_cycle,last_cycle;
};
struct IndexCurrentRecordStatus {
 uint64_t accepted_records=0,committed_records=0,accepted_writes=0,acknowledged_writes=0;
 uint32_t last_position=0;
 std::optional<long> accepted_cycle,committed_cycle;
};
struct IndexHbmTraffic {std::array<IndexHbmPortTraffic,128> pc{};};
// Owns ONLY ring writer + 4 B arbiters/backends. Scorer/selector and current
// encoder clocks remain owned by their existing participants. Never attach
// this model to a second clock loop or use it as a KV replacement.
class NativeIndexHbm:public std::enable_shared_from_this<NativeIndexHbm> {
 DsromS81MinimumRuntime& runtime;
 VDsromS81IndexHbm model;
 std::function<void()> join;
 bool admitted=false;
 long prepared=-1;
 std::array<uint64_t,128> reads{},writes{},writer_reads{};
 IndexCurrentRecordStatus current_record;
 bool old_record_accept=false;
 uint32_t old_record_position=0;
 struct Edge {bool accept=false,we=false,response=false,done=false,migration=false,response_migration=false;
              unsigned length=0;uint32_t strobe=0;};
 std::array<Edge,128> edges{};
 IndexHbmTraffic counters;
public:
 NativeIndexHbm(DsromS81MinimumRuntime&,const std::string&);
 void preload_ring(const std::string& rank_ring_directory);
 bool initialized()const{return model.history_ready;}
 bool drained()const;
 // Positive native record/ACK certificate, retained through downstream scan reads.
 bool current_committed()const;
 bool current_committed(uint32_t expected_position)const {
  return current_committed()&&current_record.last_position==expected_position;
 }
 IndexCurrentRecordStatus current_record_status()const{return current_record;}
 uint32_t capacity_words()const{return model.capacity_words;}
 IndexHbmTraffic traffic()const{return counters;}
 // Writer is actual ot_hdc_v41x_idx_pool_kwr RING1 record producer.
 // Its outputs MUST be held until w_rdy. No host key/QDQ generation here.
 template<class Index,class Writer> void wire(Index& index,Writer& writer) {
  model.r_v=index.h_req_v;model.r_addr=index.h_req_addr;
  model.r_len=index.h_req_len;model.r_tag=index.h_req_tag;
  model.r_rsp_rdy=index.h_rsp_rdy;
  model.w_v=writer.w_v;model.w_csec=writer.w_csec;model.w_ssec=writer.w_ssec;
  model.w_codes=writer.w_codes;model.w_scales=writer.w_scales;model.w_sslot=writer.w_sslot;
  model.eval();
  index.h_req_rdy=model.r_rdy;index.h_rsp_v=model.r_rsp_v;
  index.h_rsp_tag=model.r_rsp_tag;index.h_rsp_beat=model.r_rsp_beat;
  index.h_rsp_data=model.r_rsp_data;writer.w_rdy=model.w_rdy;
  index.eval();writer.eval();
  if(model.fault)throw std::runtime_error("native index ring/backend fault");
 }
 template<class Index,class Writer> void bind(Index& index,Writer& writer) {
  if(join||index.contextp()!=runtime.context||writer.contextp()!=runtime.context)
   throw std::runtime_error("index backend requires one shared-context scorer/current writer");
  join=[this,&index,&writer](){wire(index,writer);};
 }
 // For a source-owned adapter with different record names: explicit callback
 // gets the native model; caller must wire ONLY combinationally, never clock it.
 void bind_wiring(std::function<void(VDsromS81IndexHbm&)>);
 // Settle the already-bound actual ports at low clock; owns no clock edge.
 // Scorer preparation uses the same join as the backend participant.
 void join_ports() {
  if(!join||model.clk)throw std::runtime_error("index port join lacks bound low edge");
  join();model.eval();
 }
 DsromS81MinimumParticipant participant();
};
}
