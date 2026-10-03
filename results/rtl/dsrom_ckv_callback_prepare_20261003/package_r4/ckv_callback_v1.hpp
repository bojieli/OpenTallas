#pragma once
// Prospective observer ABI only. No installed callback or hardware proof.
#include <cstdint>
#include <array>
#include <vector>
namespace ot_ckv_callback_v1 {
enum class Phase : std::uint8_t { QK, PV };
struct Identity { std::uint64_t group_ref, edge; std::uint16_t selection_epoch; std::uint8_t die; };
struct Row { std::uint16_t rank; std::uint32_t gid; std::uint8_t source; std::array<std::uint32_t,72> words; };
struct Snapshot { std::uint16_t count_before,count_after; bool valid,ready,actual_write; };
struct Selection { Identity id; bool valid,ready,old_lease_drained; std::uint16_t count_after; };
struct ResetBarrier { std::uint64_t group_ref,edge; bool all4_endpoints_drained; };
struct TablePublish { Identity id; std::uint16_t count; };
struct Broadcast { Identity id; std::uint16_t rank; bool valid,ready; };
enum class RejectReason : std::uint8_t { Stale, Duplicate, WrongGid, WrongOwner, Range, Malformed };
struct RejectedRx { Identity id; Row offered; std::uint16_t offered_epoch; Snapshot probe; std::array<std::uint32_t,72> before,after; bool row_present,fault,format_valid; RejectReason reason; };
struct OutputWrite { Identity id; Phase phase; std::uint16_t descriptor_generation; bool actual_write; /* Per-port actual o_we/o_addr/o_mask/o_data, width bound in generated source adapter. */ std::vector<std::uint32_t> enables,addresses,masks,data; };
struct Storage { Identity id; std::uint16_t offered_epoch; Row row; Snapshot probe; };
struct StoredAck { Identity id; std::uint8_t peer; std::uint16_t rank,echo_epoch; bool valid,ready,pending_before,pending_after; };
struct Stage { Identity id; Phase phase; std::uint16_t descriptor_generation,row_base,write_addr; std::uint8_t mask; bool valid,ready,actual_write; std::array<std::uint32_t,530> words; };
struct Retire { Identity id; Phase phase; std::uint16_t descriptor_generation; bool descriptor_done,engine_idle; std::uint32_t output_write_mask; };
struct OwnerWrite { Identity id; std::uint32_t gid,address; std::uint8_t stack,sector; std::array<std::uint32_t,8> words; bool valid,ready,actual_wr_done,actual_backing_write; };
struct Sink { virtual ~Sink()=default; virtual void reset_barrier(const ResetBarrier&)=0; virtual void table_publish(const TablePublish&)=0; virtual void broadcast_accept(const Broadcast&)=0; virtual void rx_reject(const RejectedRx&)=0; virtual void output_write(const OutputWrite&)=0; virtual void end(std::uint64_t group_ref,std::uint64_t edge)=0; virtual void selection(const Selection&)=0; virtual void storage(const Storage&)=0; virtual void stored_ack_emit(const StoredAck&)=0; virtual void stored_ack_return(const StoredAck&)=0; virtual void staging(const Stage&)=0; virtual void retire(const Retire&)=0; virtual void owner_write(const OwnerWrite&)=0; };
}
