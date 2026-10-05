#pragma once
#include "s81_minimum_prefix_providers.hpp"
#include "VDsromSu256.h"
// References/callbacks into the existing leaf. No operand, context or clock
// duplicate. Noether reads OLD native ports in his shared prepare callback.
struct DsromS81NativeSuPorts {
 std::function<const VDsromSu256&()> native;
 std::function<DsromS81PrefixOperation()> held_operation;
 std::function<bool()> accepts_on_current_shared_edge;
 // Captured source dynamic selector6 -> effective native value, including the
 // source ceil/div selector semantics. Missing values remain unavailable.
 std::function<std::optional<uint32_t>(unsigned)> actual_dynamic;
 // Actual destination consumer observes the registered native write strobes.
 // A write observation is NOT visibility. Completion is a separate predicate.
 std::function<void(const VDsromSu256&,const DsromS81PrefixOperation&)> kv_write;
 std::function<bool()> kv_writes_visible;
};
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_su256(
 DsromS81MinimumRuntime&,uint64_t,dsrom_s81_minimum::PrefixPublication&,
 const DsromS81MinimumSourceIo&,const DsromS81MinimumSourceTags&,
 DsromS81NativeSuPorts& borrowed_port_hooks);
