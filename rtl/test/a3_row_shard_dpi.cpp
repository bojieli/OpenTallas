// DPI services for rtl/test/tb_a3_row_shard.sv.
//
// Two things the testbench cannot do in SystemVerilog at this size:
//
// 1. The paged weight window.  A `reg [7:0] mem [0:N-1]` costs one resident
//    simulator byte per checkpoint byte -- 100 MB for one Qwen3-8B MLP
//    projection, 1.24 GB for the LM head -- and a `parameter integer` cannot
//    even express the second.  This serves the same little-endian BF16
//    halfword out of the checkpoint's own safetensors shards through a page
//    cache with a HARD resident cap, so the memory the run holds is the cap
//    and not the image.  Every fault is counted, so "it is paged" is a
//    measurement: the summary line below is parsed by the campaign.
//
// 2. The write stream.  One record per word the engine wrote, in launch
//    order, address AND value, so the composer outside can reassemble the
//    operator from its shards and compare by address as well as by value.
//
// The window manifest is `shard_weight_window.txt` in the run directory, one
// segment per line: <image_base> <bytes> <file_offset> <path>.
#include "svdpi.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <list>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

struct Segment {
    std::uint64_t image_base = 0;
    std::uint64_t bytes = 0;
    std::uint64_t file_offset = 0;
    std::string path;
    int fd = -1;
};

class Window {
public:
    std::uint64_t open() {
        if (opened_) return total_bytes_;
        page_bytes_ = env_u64("OT_A3_SHARD_PAGE_BYTES", 1ULL << 20);
        if (page_bytes_ < 4096 || (page_bytes_ & (page_bytes_ - 1)) != 0)
            fail("page size must be a power of two of at least 4096");
        resident_cap_bytes_ =
            env_u64("OT_A3_SHARD_RESIDENT_BYTES", 64ULL << 20);
        if (resident_cap_bytes_ < page_bytes_)
            resident_cap_bytes_ = page_bytes_;
        max_pages_ = static_cast<std::size_t>(
            resident_cap_bytes_ / page_bytes_);
        if (max_pages_ == 0) max_pages_ = 1;
        load_manifest("shard_weight_window.txt");
        std::uint64_t cursor = 0;
        for (const auto& segment : segments_) {
            if (segment.image_base != cursor)
                fail("weight window is not gap-free at byte " +
                     std::to_string(cursor));
            cursor += segment.bytes;
        }
        total_bytes_ = cursor;
        opened_ = true;
        return total_bytes_;
    }

    std::uint32_t halfword(std::uint64_t halfword_index) {
        ++stats_reads_;
        const std::uint64_t offset = halfword_index * 2ULL;
        if (offset + 2 > total_bytes_)
            fail("halfword " + std::to_string(halfword_index) +
                 " is past the declared image");
        if (hot_ != nullptr && offset >= hot_lo_ && offset + 2 <= hot_hi_) {
            ++stats_hits_;
            const std::uint8_t* at = hot_ + (offset - hot_lo_);
            return static_cast<std::uint32_t>(at[0]) |
                   (static_cast<std::uint32_t>(at[1]) << 8);
        }
        const std::uint8_t* page = fetch(offset / page_bytes_);
        const std::uint8_t* at = page + (offset % page_bytes_);
        return static_cast<std::uint32_t>(at[0]) |
               (static_cast<std::uint32_t>(at[1]) << 8);
    }

    void report() const {
        std::printf(
            "WINDOW bytes=%llu page_bytes=%llu resident_cap_bytes=%llu "
            "reads=%llu hits=%llu faults=%llu distinct_pages=%llu "
            "evicted=%llu peak_resident_bytes=%llu\n",
            static_cast<unsigned long long>(total_bytes_),
            static_cast<unsigned long long>(page_bytes_),
            static_cast<unsigned long long>(resident_cap_bytes_),
            static_cast<unsigned long long>(stats_reads_),
            static_cast<unsigned long long>(stats_hits_),
            static_cast<unsigned long long>(stats_faults_),
            static_cast<unsigned long long>(stats_distinct_),
            static_cast<unsigned long long>(stats_evicted_),
            static_cast<unsigned long long>(stats_peak_resident_));
        std::fflush(stdout);
    }

private:
    struct Page {
        std::vector<std::uint8_t> bytes;
        std::list<std::uint64_t>::iterator position;
    };

    [[noreturn]] static void fail(const std::string& why) {
        std::fprintf(stderr, "FAIL weight window: %s\n", why.c_str());
        std::fflush(stderr);
        std::exit(2);
    }

    static std::uint64_t env_u64(const char* name, std::uint64_t fallback) {
        const char* raw = std::getenv(name);
        if (raw == nullptr || *raw == '\0') return fallback;
        return std::strtoull(raw, nullptr, 0);
    }

    void load_manifest(const std::string& path) {
        std::ifstream input(path);
        if (!input) fail("cannot open " + path);
        std::string line;
        while (std::getline(input, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream fields(line);
            Segment segment;
            if (!(fields >> segment.image_base >> segment.bytes >>
                  segment.file_offset >> segment.path))
                fail("malformed line in " + path + ": " + line);
            segment.fd = ::open(segment.path.c_str(), O_RDONLY);
            if (segment.fd < 0) fail("cannot open shard " + segment.path);
            segments_.push_back(segment);
        }
        if (segments_.empty()) fail(path + " declares no segments");
    }

    const std::uint8_t* fetch(std::uint64_t page_index) {
        auto found = resident_.find(page_index);
        if (found != resident_.end()) {
            ++stats_hits_;
            order_.splice(order_.begin(), order_, found->second.position);
            arm_hot(page_index, found->second.bytes.data());
            return found->second.bytes.data();
        }
        ++stats_faults_;
        if (seen_.insert(page_index).second) ++stats_distinct_;
        while (resident_.size() >= max_pages_) {
            const std::uint64_t victim = order_.back();
            order_.pop_back();
            resident_.erase(victim);
            ++stats_evicted_;
        }
        Page page;
        page.bytes.assign(static_cast<std::size_t>(page_bytes_), 0);
        fill(page_index, page.bytes.data());
        order_.push_front(page_index);
        page.position = order_.begin();
        auto inserted = resident_.emplace(page_index, std::move(page)).first;
        const std::uint64_t resident_bytes = resident_.size() * page_bytes_;
        if (resident_bytes > stats_peak_resident_)
            stats_peak_resident_ = resident_bytes;
        arm_hot(page_index, inserted->second.bytes.data());
        return inserted->second.bytes.data();
    }

    void arm_hot(std::uint64_t page_index, const std::uint8_t* bytes) {
        hot_lo_ = page_index * page_bytes_;
        hot_hi_ = hot_lo_ + page_bytes_;
        hot_ = bytes;
    }

    void fill(std::uint64_t page_index, std::uint8_t* into) {
        const std::uint64_t lo = page_index * page_bytes_;
        const std::uint64_t hi = lo + page_bytes_;
        for (const auto& segment : segments_) {
            const std::uint64_t seg_lo = segment.image_base;
            const std::uint64_t seg_hi = seg_lo + segment.bytes;
            const std::uint64_t from = lo > seg_lo ? lo : seg_lo;
            const std::uint64_t to = hi < seg_hi ? hi : seg_hi;
            if (from >= to) continue;
            std::uint64_t want = to - from;
            std::uint64_t at = segment.file_offset + (from - seg_lo);
            std::uint8_t* out = into + (from - lo);
            while (want != 0) {
                const ssize_t got = ::pread(segment.fd, out,
                                            static_cast<std::size_t>(want),
                                            static_cast<off_t>(at));
                if (got <= 0)
                    fail("short read from " + segment.path + " at " +
                         std::to_string(at));
                want -= static_cast<std::uint64_t>(got);
                at += static_cast<std::uint64_t>(got);
                out += got;
            }
        }
    }

    bool opened_ = false;
    std::uint64_t page_bytes_ = 1ULL << 20;
    std::uint64_t resident_cap_bytes_ = 64ULL << 20;
    std::size_t max_pages_ = 64;
    std::uint64_t total_bytes_ = 0;
    std::vector<Segment> segments_;
    std::unordered_map<std::uint64_t, Page> resident_;
    std::list<std::uint64_t> order_;
    std::unordered_set<std::uint64_t> seen_;
    const std::uint8_t* hot_ = nullptr;
    std::uint64_t hot_lo_ = 0;
    std::uint64_t hot_hi_ = 0;
    std::uint64_t stats_reads_ = 0;
    std::uint64_t stats_hits_ = 0;
    std::uint64_t stats_faults_ = 0;
    std::uint64_t stats_distinct_ = 0;
    std::uint64_t stats_evicted_ = 0;
    std::uint64_t stats_peak_resident_ = 0;
};

Window& window() {
    static Window instance;
    return instance;
}

std::FILE*& stream() {
    static std::FILE* handle = nullptr;
    return handle;
}

}  // namespace

extern "C" {

std::uint64_t ot_a3_shard_window_open() { return window().open(); }

std::uint32_t ot_a3_shard_window_halfword(std::uint64_t halfword_index) {
    return window().halfword(halfword_index);
}

void ot_a3_shard_stream_open(const char* path) {
    if (stream() != nullptr) return;
    stream() = std::fopen(path, "wb");
    if (stream() == nullptr) {
        std::fprintf(stderr, "FAIL cannot open write stream %s\n", path);
        std::fflush(stderr);
        std::exit(2);
    }
}

void ot_a3_shard_stream_write(std::uint32_t address, std::uint32_t data) {
    if (stream() == nullptr) return;
    std::fprintf(stream(), "%u %u\n", address, data);
}

void ot_a3_shard_stream_close() {
    if (stream() != nullptr) {
        std::fclose(stream());
        stream() = nullptr;
    }
    window().report();
}

}  // extern "C"
