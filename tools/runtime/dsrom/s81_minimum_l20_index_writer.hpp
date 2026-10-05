#pragma once
#include "s81_minimum_su256_ports.hpp"
#include "s81_minimum_index_hbm.hpp"
#include <memory>
class VDsromS81IndexWriter;
namespace dsrom_s81_minimum {
// I36 only. Construct AFTER Noether's SU KV sinks, then enroll this participant
// once in the SAME runtime. The writer owns only its retained pool_kwr clock;
// SUN256 and NativeIndexHbm keep their existing, separate clock owners.
class L20IndexWriter {
 struct Impl;
 std::shared_ptr<Impl> impl;
public:
 L20IndexWriter(DsromS81MinimumRuntime&,uint64_t identity,
               DsromS81NativeSuPorts&,std::shared_ptr<NativeIndexHbm>,
               const DsromS81PrefixOperation& actual_I36);
 VDsromS81IndexWriter& native()const;
 // Call inside the existing index backend's low-edge wiring callback, together
// with actual scorer ports. This copies ONLY native encoder record ports.
 void join_backend(VDsromS81IndexHbm&)const;
 bool source_idle()const;
 bool fault()const;
 DsromS81MinimumParticipant participant()const;
};
} // namespace dsrom_s81_minimum
