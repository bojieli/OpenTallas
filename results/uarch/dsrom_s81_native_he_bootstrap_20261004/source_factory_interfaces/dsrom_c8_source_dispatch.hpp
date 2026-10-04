#pragma once
#include <cstdint>
#include <stdexcept>

// Include after Arch's native C8 runtime (DSROM_C8_LIBRARY=1). Die is the
// actual retained DieBase/Die, not a host numerical implementation. Sample
// before a clock edge; invoke accepted_edge once after that same edge.
struct DsromC8SourceOffer {
    int die_id;
    uint32_t token, position, user;
    uint16_t epoch, entry;
    uint64_t identity;
};

class DsromC8SourceDispatch {
    DsromC8SourceOffer offer;
    bool accepted = false, driven = false, finished = false;
public:
    explicit DsromC8SourceDispatch(DsromC8SourceOffer descriptor): offer(descriptor) {
        if (offer.token >= (1u<<21) || offer.position >= (1u<<21) ||
            offer.user >= (1u<<10) || offer.entry >= (1u<<14) ||
            offer.identity != ((uint64_t(offer.epoch)<<31) |
                               (uint64_t(offer.user)<<21) | offer.position))
            throw std::runtime_error("source C8 retained context bounds/identity");
    }
    // restore_visible must inspect the actual producer's VM/lease visibility
    // for this descriptor. drain_visible must inspect native remote receipts.
    // Neither engine done nor local retire substitutes for remote drain.
    template<class Die, class Restore, class Drain>
    void before_edge(Die& die, int physical_die_id, Restore& restore_visible, Drain& drain_visible) {
        // The original Die.id is rank-local (0..3), not a physical stage ID.
        // The enclosing parent supplies its actual field_parameters.die_id.
        if (physical_die_id != offer.die_id)
            throw std::runtime_error("source C8 physical die mismatch");
        die.c8_restored(false);
        die.c8_offer(!accepted && !finished, offer.token, offer.position,
                     offer.user, offer.epoch, offer.entry);
        driven = !accepted && !finished && die.c8_ready();
        uint64_t identity; uint32_t token; uint16_t entry;
        if (die.c8_context(identity, token, entry)) {
            if (!accepted || identity != offer.identity || token != offer.token || entry != offer.entry)
                throw std::runtime_error("source C8 retained context mismatch");
            die.c8_restored(restore_visible(offer));
        }
        if (die.c8_retired(identity)) {
            if (!accepted || identity != offer.identity)
                throw std::runtime_error("source C8 unexpected retirement");
            retired = true;
        }
        if (retired && drain_visible(offer)) finished = true;
    }
    void accepted_edge() { if (driven) accepted = true; driven = false; }
    bool complete() const { return finished; }
private:
    bool retired = false;
};
