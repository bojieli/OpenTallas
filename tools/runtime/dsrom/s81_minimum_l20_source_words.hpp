#pragma once
#include "s81_delayed_eid_sessions.hpp"

// Prestart-only source transport. No native model, tick, grant or publication.
enum class DsromS81L20WordKind { Field, MeRaw };
struct DsromS81L20StaticWordEnrollment {
    std::string node, source_node_sha256;
    unsigned rank=0, fragment=0;
    DsromS81L20WordKind kind=DsromS81L20WordKind::Field;
};
struct DsromS81L20SourceWordConfig {
    std::string python, source_bridge, qe_bridge, owner, checkpoint;
};
struct DsromS81L20RankSourceAuthority {
    DsromS81MinimumSourceIo io;
    std::function<bool(uint64_t,unsigned)> published;
};
// Resolve actual Boole bank/publication owners AFTER construction. nullopt
// refuses reads/leases/publication; callbacks never create or own a bank.
using DsromS81L20ResolveSourceAuthority=
    std::function<std::optional<DsromS81L20RankSourceAuthority>(unsigned)>;
class DsromS81MinimumL20SourceWords {
    struct Impl;
    std::shared_ptr<Impl> impl_;
    explicit DsromS81MinimumL20SourceWords(std::shared_ptr<Impl>);
public:
    using WordRead=std::function<std::array<uint32_t,9>(int,int,int,int)>;
    using HeRead=std::function<std::array<uint32_t,8>(bool,uint64_t)>;
    // Call BEFORE NativePair/Vnative_vm/model workers. Returns only when ALL
    // fixed static/dynamic children and the raw L20 HE source report READY.
    static std::shared_ptr<DsromS81MinimumL20SourceWords> prestart(
        const DsromS81L20SourceWordConfig&,
        const std::vector<DsromS81L20StaticWordEnrollment>&,
        const std::vector<DsromS81DelayedEidEnrollment>&,
        DsromS81L20ResolveSourceAuthority);
    // Each closure retains source owners through native drain; no later fork.
    WordRead word_reader(const std::string& node,unsigned rank,unsigned fragment=0);
    HeRead he_words(unsigned rank);
    // Actual mapped I93 producer2564 only; identity is the actual ID47 context.
    void captured_i93(unsigned rank,uint64_t identity,
                      const DsromS81DelayedEidSessions::Eids& raw_native_ids);
    bool advance_captured_bindings();
    bool bound(const std::string& node,unsigned rank,unsigned fragment=0);
    bool fault() const;
};
