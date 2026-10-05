// Host-only optional successor of the measured W12 Fabric::edge() loop.
// No die, collective, settle, stage-switch, or ACK work belongs in this helper.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>

// FUTURE caller integration at the existing enabled-fabric edge loop ONLY:
//   Fabric* edge_fab[D];
//   for (int d = 0; d < D; ++d) edge_fab[d] = fab[d].get();
//   qwen_rt_batch_tile_edges(pool, edge_fab, tile_en, D, NT, NWS_EXT,
//                            host_batch_tile_edges); // default false
// Keep tile_en's original pre-edge ME/previous-KV sampling unchanged.
// Keep the preceding die/coll rising eval and following settle/ACK unchanged.
//
// Contract: Pool::run is blocking and assigns task j to worker j % size().
// Every Fabric has tiles tiles, whose model contexts belong to worker i % size().
// Fabric fields/methods are those of the pinned W12 caller: t, hl, hp, ext,
// set_clk, word, valid, edge. ext has ext_stages entries for every tile.
// Different fabrics have independent tile models and extension registers;
// their only cross-die path is the collective, which is NOT evaluated here.
// The original per-fabric low phase is conditional on ANY tile having clk=1.
// Batching retains that condition, including when a previously gated die wakes.
// These are host barriers, not extra simulated pipeline stages.
template <class Pool, class Fabric, std::size_t D>
void qwen_rt_batch_tile_edges(Pool& pool, Fabric* const (&fabrics)[D],
                             const uint8_t* enabled, std::size_t dies,
                             std::size_t tiles, int ext_stages,
                             bool batch = false) {
    if (dies != D)
        throw std::invalid_argument("Qwen batched edge: incompatible die count");
    if (!batch) {
        for (std::size_t d = 0; d < dies; ++d)
            if (enabled[d]) fabrics[d]->edge();
        return;
    }
    // Reject incompatible worker ownership before mutating clocks/registers.
    const int workers = pool.size();
    if (workers <= 0 || tiles == 0 || tiles % std::size_t(workers) != 0 ||
        ext_stages < 0 || dies > std::numeric_limits<std::size_t>::max() / tiles)
        throw std::invalid_argument("Qwen batched edge: incompatible partition/shape");
    for (std::size_t d = 0; d < dies; ++d)
        if (!fabrics[d] || fabrics[d]->t.size() != tiles)
            throw std::invalid_argument("Qwen batched edge: incompatible fabric");

    std::array<uint8_t, D> low{}; // no per-edge heap allocation
    bool any_enabled = false, any_low = false;
    for (std::size_t d = 0; d < dies; ++d) {
        if (!enabled[d]) continue;
        any_enabled = true;
        for (const auto& tile : fabrics[d]->t)
            if (tile->clk) { low[d] = 1; any_low = true; break; }
    }
    if (!any_enabled) return;
    // Flattened j=d*tiles+i still maps to worker i%workers because tiles is
    // divisible by workers. Never move a model to another context/worker.
    const std::size_t count = dies * tiles;

    // LOW: finish every required low evaluation before any snapshot.
    for (std::size_t d = 0; d < dies; ++d)
        if (low[d]) fabrics[d]->set_clk(0);
    if (any_low)
        pool.run(count, [&](std::size_t j) {
            const auto d = j / tiles, i = j % tiles;
            if (low[d]) fabrics[d]->t[i]->eval();
        });

    // EXT: all snapshots use completed LOW outputs, and precede every HIGH.
    if (ext_stages > 0)
        pool.run(count, [&](std::size_t j) {
            const auto d = j / tiles, i = j % tiles;
            if (!enabled[d]) return;
            auto& f = *fabrics[d];
            if (!f.hl[i]) return;
            auto& e = f.ext[i];
            for (int s = ext_stages - 1; s > 0; --s) e[s] = e[s - 1];
            e[0].a = f.word(f.hl[i] - 1, 2 * f.hp[i]);
            e[0].b = f.word(f.hl[i] - 1, 2 * f.hp[i] + 1);
            e[0].va = f.valid(f.hl[i] - 1, 2 * f.hp[i]);
        });

    // HIGH: exactly one high evaluation of every enabled tile.
    for (std::size_t d = 0; d < dies; ++d)
        if (enabled[d]) fabrics[d]->set_clk(1);
    pool.run(count, [&](std::size_t j) {
        const auto d = j / tiles, i = j % tiles;
        if (enabled[d]) fabrics[d]->t[i]->eval();
    });
}
