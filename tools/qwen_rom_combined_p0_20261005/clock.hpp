#pragma once
#include <cstdint>
#include <stdexcept>

namespace qwen_combined_p0 {
// Both roots remain independent. A clock event updates all die clock pins
// before evaluating any model, including coincident source/controller edges.
// Callbacks perform the existing RTL/fabric/collective combinational settle.
class Clocks {
    uint64_t next_h_;
    bool h_ = false;
    uint64_t now_ = 0;
    uint64_t controller_rises_ = 0;
public:
    static constexpr uint64_t core_fs = 833333, controller_half_fs = 512000;
    explicit Clocks(uint64_t phase_fs = 0) : next_h_(phase_fs) {}
    uint64_t controller_rises() const { return controller_rises_; }
    uint64_t elapsed_fs() const { return now_; }
    template<class SetController, class SetCore, class Settle>
    void edge(uint64_t time_fs, SetController controller, SetCore core, Settle settle) {
        if (time_fs < now_) throw std::logic_error("P0 clock time moved backwards");
        while (next_h_ < time_fs) {
            h_ = !h_; controller_rises_ += h_; controller(h_); settle();
            next_h_ += controller_half_fs;
        }
        if (next_h_ == time_fs) {
            h_ = !h_; controller_rises_ += h_; controller(h_); next_h_ += controller_half_fs;
        }
        core(); settle(); now_ = time_fs;
    }
};
}
