#pragma once
#include "s81_minimum_source_bindings.hpp"
#include "Vcut.h"
#include <memory>

// Actual native word reader: same four coordinates as ReleasedQeWordBinding.
// Values are copied as nine little-endian32 words; no host dequantization.
using DsromS81QeWordReader=std::function<std::array<uint32_t,9>(int,int,int,int)>;
struct DsromS81QePairBinding {
    dsrom_s81_minimum::ReturnPhaseBinding returned;
    bool physical_bf_site=false;
    std::vector<uint64_t> config;
};
struct DsromS81QePhase {
    DsromS81PrefixOperation operation;
    uint32_t xbase=0,ops=0,cut_output_alias=0,cut_input_alias=0;
    std::array<uint64_t,2> phrom{};
    std::vector<uint64_t> stream;
    // Mandatory for original ME weight frames: exact source ordered-K input
    // and native output-address mappings. No inferred contiguous ME layout.
    std::vector<uint32_t> actual_input_addresses,actual_output_addresses;
    std::vector<DsromS81QePairBinding> pairs;
};
// This observer shares Popper's actual callbacks. offer() is NOT acceptance.
// The factory must compose these after the existing tag accept/ACK handlers.
class DsromS81NativeQe {
    struct Impl;
    std::shared_ptr<Impl> impl;
public:
    DsromS81NativeQe(DsromS81MinimumRuntime&,uint64_t,
        dsrom_s81_minimum::PrefixPublication&,const DsromS81MinimumSourceIo&,
        Vcut& borrowed_native_cut,DsromS81QePhase,DsromS81QeWordReader, std::function<bool()> actual_prior_publication_drained);
    DsromS81PrefixNativeEngine engine();
    void scalar_accept(unsigned,const dsrom_s81_minimum::MacroWrite&);
    void scalar_visible(unsigned,const dsrom_s81_minimum::MacroWrite&,
                        const dsrom_s81_minimum::VmReceipt&);
    bool owns(const dsrom_s81_minimum::MacroWrite&) const;
    unsigned producer() const;
    bool active() const;
    bool complete() const;
};

// Use Arch's source-exact native_field_bindings.hpp plus selected stage-map
// BF_site_IDs. Callback uses Goodall67cf serve_connection/borrowed Checkpoint;
// caller owns the inherited fd and closes it only after native debts drain.
DsromS81QeWordReader dsrom_s81_qe_word_reader(int borrowed_fd);
DsromS81QePhase dsrom_s81_qe_load_controls(const DsromS81PrefixOperation&,
 const std::vector<dsrom_s81_minimum::ReturnPhaseBinding>&,
 const std::vector<unsigned>& actual_BF_site_IDs,const std::string& emitted_directory,
 uint32_t actual_input_base,uint32_t private_cut_only_output_alias);

// Selected field-fragment dispatcher (QE0 / ME weight only). Parent chooses
// ME weight versus actual KV/ATT engine; no automatic ME arithmetic relabeling.
// Every fragment requires source-exact emitted PHROM/CFG/return ownership.
DsromS81PrefixNativeEngine dsrom_s81_qe_dispatch(
 const std::vector<std::shared_ptr<DsromS81NativeQe>>&);
