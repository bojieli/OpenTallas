// Independent Verilator checker for the exact shipped ABI 3.0 engine prefix.
// It parses the memory images itself, observes every completion handshake, and
// never consumes an expectation through the RTL design.
#include "Vot_a3_shipped_prefix_top.h"
#include "Vot_a3_shipped_prefix_top__Dpi.h"
#include "verilated.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <list>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

// ---------------------------------------------------------------------------
// The paged weight window (rung G1a-G1d sizing).
//
// The verification top used to declare `reg [7:0] matmul_weight_mem
// [0:MATMUL_WEIGHT_BYTES-1]` and $fread the whole blob at time 0.  One
// resident simulator byte per checkpoint byte: 48 MiB for the shipped
// prefix, 386 MB for a Qwen3-8B layer, 1.24 GB for the LM head, 16.4 GB for
// the model -- and above 2 GiB the declaration could not be written at all,
// because `parameter integer` is 32-bit.
//
// This serves the same little-endian BF16 halfword out of the real
// safetensors shards through a page cache with a HARD resident cap.  The
// memory the checker holds is the cap, not the image: a 16.4 GB image costs
// the same resident bytes as a 48 MiB one.  Every page fault is counted, so
// "it is paged" is a measurement rather than a claim -- a window that
// thrashes shows up as refilled_bytes far above distinct_bytes.
// ---------------------------------------------------------------------------
namespace weightwindow {

struct Segment {
    std::uint64_t image_base = 0;   // byte offset within the addressed image
    std::uint64_t bytes = 0;
    std::uint64_t file_offset = 0;
    std::string path;
    int fd = -1;
};

struct Stats {
    std::uint64_t halfword_reads = 0;
    std::uint64_t page_hits = 0;
    std::uint64_t page_faults = 0;
    std::uint64_t bytes_faulted = 0;
    std::uint64_t pages_evicted = 0;
    std::uint64_t distinct_pages = 0;
    std::uint64_t peak_resident_bytes = 0;
};

class Window {
  public:
    ~Window() {
        for (auto& segment : segments_) {
            if (segment.fd >= 0) ::close(segment.fd);
        }
    }

    // Declared bytes is the image the RTL believes it is addressing.  The
    // window refuses to serve a different size, exactly as the old short-
    // $fread check did.
    std::uint64_t open(std::uint64_t declared_bytes) {
        if (opened_) return total_bytes_;
        page_bytes_ = env_u64("OT_A3_WEIGHT_PAGE_BYTES", 1ULL << 20);
        if (page_bytes_ < 4096 || (page_bytes_ & (page_bytes_ - 1)) != 0)
            fail("OT_A3_WEIGHT_PAGE_BYTES must be a power of two >= 4096");
        // The resident cap is a FRACTION of the image with a hard ceiling,
        // never the image: an eighth, clamped to [8 MiB, 64 MiB].  A
        // Qwen3-8B layer (386 MB) resides in 48 MiB, the LM head (1.24 GB)
        // and the whole 16.4 GB checkpoint both in 64 MiB.  This is what
        // makes the checker's footprint a function of the working set rather
        // than of the model.
        std::uint64_t cap = declared_bytes / 8;
        if (cap < (8ULL << 20)) cap = 8ULL << 20;
        if (cap > (64ULL << 20)) cap = 64ULL << 20;
        resident_cap_bytes_ = env_u64("OT_A3_WEIGHT_WINDOW_BYTES", cap);
        if (resident_cap_bytes_ < page_bytes_)
            resident_cap_bytes_ = page_bytes_;
        max_pages_ = resident_cap_bytes_ / page_bytes_;

        if (!load_manifest("p3_weight_window.txt")) load_blob();
        std::uint64_t next = 0;
        for (const auto& segment : segments_) {
            if (segment.image_base != next)
                fail("weight window image is not gap-free at byte " +
                     std::to_string(next));
            next += segment.bytes;
        }
        total_bytes_ = next;
        if (total_bytes_ != declared_bytes)
            fail("weight window holds " + std::to_string(total_bytes_) +
                 " bytes, the top declares " + std::to_string(declared_bytes));
        opened_ = true;
        return total_bytes_;
    }

    std::uint32_t halfword(std::uint64_t index) {
        ++stats_.halfword_reads;
        const std::uint64_t offset = index * 2ULL;
        // A halfword never straddles a page: offsets are even and the page
        // size is a power of two at least 4096.
        if (offset >= hot_lo_ && offset + 2 <= hot_hi_) {
            ++stats_.page_hits;
            const std::uint8_t* at = hot_ + (offset - hot_lo_);
            return static_cast<std::uint32_t>(at[0]) |
                   (static_cast<std::uint32_t>(at[1]) << 8);
        }
        const std::uint8_t* page = fetch(offset / page_bytes_);
        const std::uint8_t* at = page + (offset % page_bytes_);
        return static_cast<std::uint32_t>(at[0]) |
               (static_cast<std::uint32_t>(at[1]) << 8);
    }

    const Stats& stats() const { return stats_; }
    std::uint64_t total_bytes() const { return total_bytes_; }
    std::uint64_t page_bytes() const { return page_bytes_; }
    std::uint64_t resident_cap_bytes() const { return resident_cap_bytes_; }
    std::size_t segment_count() const { return segments_.size(); }
    const std::vector<Segment>& segments() const { return segments_; }

  private:
    [[noreturn]] static void fail(const std::string& why) {
        throw std::runtime_error("weight window: " + why);
    }

    static std::uint64_t env_u64(const char* name, std::uint64_t fallback) {
        const char* raw = std::getenv(name);
        if (raw == nullptr || *raw == '\0') return fallback;
        return std::strtoull(raw, nullptr, 0);
    }

    // p3_weight_window.txt: one segment per line,
    //   <image_base> <bytes> <file_offset> <path>
    // pointing straight at the checkpoint's own safetensors shards.  No
    // staged copy of the weights need exist on disk at all.
    bool load_manifest(const std::string& path) {
        std::ifstream input(path);
        if (!input) return false;
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
        return true;
    }

    void load_blob() {
        Segment segment;
        segment.path = "p3_matmul_weight.bin";
        segment.fd = ::open(segment.path.c_str(), O_RDONLY);
        if (segment.fd < 0)
            fail("neither p3_weight_window.txt nor p3_matmul_weight.bin");
        struct stat info {};
        if (::fstat(segment.fd, &info) != 0) fail("cannot stat the blob");
        segment.image_base = 0;
        segment.file_offset = 0;
        segment.bytes = static_cast<std::uint64_t>(info.st_size);
        segments_.push_back(segment);
    }

    const std::uint8_t* fetch(std::uint64_t page_index) {
        auto found = resident_.find(page_index);
        if (found != resident_.end()) {
            ++stats_.page_hits;
            order_.splice(order_.begin(), order_, found->second.position);
            arm_hot(page_index, found->second.bytes.data());
            return found->second.bytes.data();
        }
        ++stats_.page_faults;
        if (seen_.insert(page_index).second) ++stats_.distinct_pages;
        while (resident_.size() >= max_pages_) {
            const std::uint64_t victim = order_.back();
            order_.pop_back();
            resident_.erase(victim);
            ++stats_.pages_evicted;
        }
        Page page;
        page.bytes.assign(page_bytes_, 0);
        fill(page_index, page.bytes.data());
        stats_.bytes_faulted += page_bytes_;
        order_.push_front(page_index);
        page.position = order_.begin();
        auto inserted = resident_.emplace(page_index, std::move(page)).first;
        const std::uint64_t resident_bytes = resident_.size() * page_bytes_;
        if (resident_bytes > stats_.peak_resident_bytes)
            stats_.peak_resident_bytes = resident_bytes;
        arm_hot(page_index, inserted->second.bytes.data());
        return inserted->second.bytes.data();
    }

    void arm_hot(std::uint64_t page_index, const std::uint8_t* bytes) {
        hot_lo_ = page_index * page_bytes_;
        hot_hi_ = hot_lo_ + page_bytes_;
        hot_ = bytes;
    }

    // One page may span more than one shard: fill it segment by segment.
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

    struct Page {
        std::vector<std::uint8_t> bytes;
        std::list<std::uint64_t>::iterator position;
    };

    bool opened_ = false;
    std::uint64_t page_bytes_ = 1ULL << 20;
    std::uint64_t resident_cap_bytes_ = 64ULL << 20;
    std::size_t max_pages_ = 64;
    std::uint64_t total_bytes_ = 0;
    std::vector<Segment> segments_;
    std::unordered_map<std::uint64_t, Page> resident_;
    std::list<std::uint64_t> order_;
    std::unordered_set<std::uint64_t> seen_;
    Stats stats_;
    const std::uint8_t* hot_ = nullptr;
    std::uint64_t hot_lo_ = 1;   // empty range until the first fetch
    std::uint64_t hot_hi_ = 0;
};

Window& window() {
    static Window instance;
    return instance;
}

}  // namespace weightwindow

// The geometry the top was elaborated with.  The checker no longer hardcodes
// any of it: a ladder rung that instantiates the top with a 151,936-word
// result memory or a 1,400,832-word source memory is checked at that size.
struct Geometry {
    std::uint32_t program_words = 0;
    std::uint32_t desc_words = 0;
    std::uint32_t index_words = 0;
    std::uint32_t source_words = 0;
    std::uint32_t result_words = 0;
    std::uint64_t matmul_weight_bytes = 0;
    std::uint32_t result_injection = 0;
    std::uint32_t exact_multicast = 0;
    bool declared = false;
};

Geometry g_geometry;

// ---------------------------------------------------------------------------
// Rung G1e: the issue trace, and the engine-result injection boundary.
//
// The trace is what makes hybrid co-simulation evidence instead of a stub.
// The RTL control plane -- fetch, decode, view resolution, predicates, the
// loop stack, the wait set, queue acceptance -- runs exactly as it does when
// the engines compute; only the engine RESULT is supplied.  Every issue the
// RTL makes is recorded with its opcode, descriptor id, program counter,
// schedule (queue), issue serial and IRS slot, followed by every view the
// RTL resolver produced for it with its descriptor id and resolved address.
// The record is flattened to a fixed element vector and compared to the
// golden model's element for element, failing at the FIRST divergence with
// the element index recorded.
// ---------------------------------------------------------------------------
namespace trace {

// The fields the RTL emits for every engine issue and for every view its
// resolver produced.  Gate G1e names what must be there: the opcode, the
// descriptor ids, the resolved view ids and addresses, the schedule id and
// the issue serial.  All of them are emitted, always.
const std::vector<std::string>& issue_fields() {
    static const std::vector<std::string> fields = {
        "serial", "family", "sub", "descriptor_id", "pc", "queue", "irs_slot"};
    return fields;
}

const std::vector<std::string>& view_fields() {
    static const std::vector<std::string> fields = {
        "slot",  "descriptor_id", "extent", "extent_axis",
        "element_offset", "rank", "irs_slot"};
    return fields;
}

struct View {
    std::uint64_t slot = 0;
    std::uint64_t descriptor_id = 0;
    std::uint64_t extent = 0;
    std::uint64_t extent_axis = 0;
    std::uint64_t element_offset = 0;
    std::uint64_t rank = 0;
    std::uint64_t irs_slot = 0;

    std::uint64_t field(const std::string& name) const {
        if (name == "slot") return slot;
        if (name == "descriptor_id") return descriptor_id;
        if (name == "extent") return extent;
        if (name == "extent_axis") return extent_axis;
        if (name == "element_offset") return element_offset;
        if (name == "rank") return rank;
        if (name == "irs_slot") return irs_slot;
        throw std::runtime_error("unknown VIEW field '" + name + "'");
    }
    void set(const std::string& name, std::uint64_t value) {
        if (name == "slot") slot = value;
        else if (name == "descriptor_id") descriptor_id = value;
        else if (name == "extent") extent = value;
        else if (name == "extent_axis") extent_axis = value;
        else if (name == "element_offset") element_offset = value;
        else if (name == "rank") rank = value;
        else if (name == "irs_slot") irs_slot = value;
        else throw std::runtime_error("unknown VIEW field '" + name + "'");
    }
};

struct Issue {
    std::uint64_t serial = 0;
    std::uint64_t family = 0;
    std::uint64_t sub = 0;
    std::uint64_t descriptor_id = 0;
    std::uint64_t pc = 0;
    std::uint64_t queue = 0;
    std::uint64_t irs_slot = 0;
    std::vector<View> views;

    std::uint64_t field(const std::string& name) const {
        if (name == "serial") return serial;
        if (name == "family") return family;
        if (name == "sub") return sub;
        if (name == "descriptor_id") return descriptor_id;
        if (name == "pc") return pc;
        if (name == "queue") return queue;
        if (name == "irs_slot") return irs_slot;
        throw std::runtime_error("unknown ISSUE field '" + name + "'");
    }
    void set(const std::string& name, std::uint64_t value) {
        if (name == "serial") serial = value;
        else if (name == "family") family = value;
        else if (name == "sub") sub = value;
        else if (name == "descriptor_id") descriptor_id = value;
        else if (name == "pc") pc = value;
        else if (name == "queue") queue = value;
        else if (name == "irs_slot") irs_slot = value;
        else throw std::runtime_error("unknown ISSUE field '" + name + "'");
    }
};

struct Record {
    std::vector<Issue> issues;
    // The field lists this record's elements are made of.  A golden trace
    // MUST declare them; there is no default, so a golden that silently
    // omits a field cannot be mistaken for one that carries it.
    std::vector<std::string> compared_issue_fields;
    std::vector<std::string> compared_view_fields;

    std::size_t elements() const {
        std::size_t total = 0;
        for (const auto& issue : issues)
            total += compared_issue_fields.size() +
                     issue.views.size() * compared_view_fields.size();
        return total;
    }
};

// Flatten to the element vector the comparison walks, with a label per
// element so a divergence names the field it happened in.
void flatten(const Record& record, const std::vector<std::string>& issue_sel,
             const std::vector<std::string>& view_sel,
             std::vector<std::uint64_t>& values,
             std::vector<std::string>& labels) {
    for (std::size_t i = 0; i < record.issues.size(); ++i) {
        const auto& issue = record.issues[i];
        for (const auto& name : issue_sel) {
            values.push_back(issue.field(name));
            labels.push_back("issue[" + std::to_string(i) + "]." + name);
        }
        for (std::size_t v = 0; v < issue.views.size(); ++v) {
            for (const auto& name : view_sel) {
                values.push_back(issue.views[v].field(name));
                labels.push_back("issue[" + std::to_string(i) + "].view[" +
                                 std::to_string(v) + "]." + name);
            }
        }
    }
}

void write(const Record& record, const std::string& path) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write trace " + path);
    out << "FIELDS ISSUE";
    for (const auto& name : issue_fields()) out << ' ' << name;
    out << "\nFIELDS VIEW";
    for (const auto& name : view_fields()) out << ' ' << name;
    out << '\n';
    for (const auto& issue : record.issues) {
        out << "ISSUE";
        for (const auto& name : issue_fields()) out << ' ' << issue.field(name);
        out << '\n';
        for (const auto& view : issue.views) {
            out << "VIEW";
            for (const auto& name : view_fields()) out << ' ' << view.field(name);
            out << '\n';
        }
    }
}

Record read(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read trace " + path);
    Record record;
    bool issue_declared = false;
    bool view_declared = false;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string tag;
        fields >> tag;
        if (tag == "FIELDS") {
            std::string which;
            fields >> which;
            std::vector<std::string> names;
            std::string name;
            while (fields >> name) names.push_back(name);
            if (names.empty())
                throw std::runtime_error("empty FIELDS line in " + path);
            if (which == "ISSUE") {
                record.compared_issue_fields = names;
                issue_declared = true;
            } else if (which == "VIEW") {
                record.compared_view_fields = names;
                view_declared = true;
            } else {
                throw std::runtime_error("unknown FIELDS kind in " + path);
            }
            continue;
        }
        if (!issue_declared || !view_declared)
            throw std::runtime_error(
                "golden trace " + path +
                " has no FIELDS header: the compared field set must be "
                "declared, never assumed");
        std::vector<std::uint64_t> values;
        std::uint64_t value = 0;
        while (fields >> value) values.push_back(value);
        if (tag == "ISSUE") {
            if (values.size() != record.compared_issue_fields.size())
                throw std::runtime_error("ISSUE arity disagrees with FIELDS");
            Issue issue;
            for (std::size_t i = 0; i < values.size(); ++i)
                issue.set(record.compared_issue_fields[i], values[i]);
            record.issues.push_back(std::move(issue));
        } else if (tag == "VIEW") {
            if (record.issues.empty())
                throw std::runtime_error("VIEW before any ISSUE in " + path);
            if (values.size() != record.compared_view_fields.size())
                throw std::runtime_error("VIEW arity disagrees with FIELDS");
            View view;
            for (std::size_t i = 0; i < values.size(); ++i)
                view.set(record.compared_view_fields[i], values[i]);
            record.issues.back().views.push_back(view);
        } else {
            throw std::runtime_error("unknown trace tag '" + tag + "'");
        }
    }
    if (!issue_declared || !view_declared)
        throw std::runtime_error("golden trace " + path +
                                 " declares no FIELDS header");
    return record;
}

struct Comparison {
    bool ran = false;
    bool equal = true;
    long long divergence_index = -1;
    std::string label;
    std::uint64_t got = 0;
    std::uint64_t want = 0;
    std::size_t compared = 0;
    std::vector<std::string> uncompared_issue_fields;
    std::vector<std::string> uncompared_view_fields;
};

std::vector<std::string> missing(const std::vector<std::string>& all,
                                 const std::vector<std::string>& selected) {
    std::vector<std::string> out;
    for (const auto& name : all)
        if (std::find(selected.begin(), selected.end(), name) ==
            selected.end())
            out.push_back(name);
    return out;
}

// Element for element.  First divergence wins and its index is recorded.
Comparison compare(const Record& rtl, const Record& golden) {
    Comparison out;
    out.ran = true;
    out.uncompared_issue_fields =
        missing(issue_fields(), golden.compared_issue_fields);
    out.uncompared_view_fields =
        missing(view_fields(), golden.compared_view_fields);
    std::vector<std::uint64_t> rtl_values, golden_values;
    std::vector<std::string> rtl_labels, golden_labels;
    flatten(rtl, golden.compared_issue_fields, golden.compared_view_fields,
            rtl_values, rtl_labels);
    flatten(golden, golden.compared_issue_fields, golden.compared_view_fields,
            golden_values, golden_labels);
    const std::size_t common = rtl_values.size() < golden_values.size()
                                   ? rtl_values.size()
                                   : golden_values.size();
    for (std::size_t i = 0; i < common; ++i) {
        ++out.compared;
        if (rtl_values[i] != golden_values[i]) {
            out.equal = false;
            out.divergence_index = static_cast<long long>(i);
            out.label = rtl_labels[i] + " vs golden " + golden_labels[i];
            out.got = rtl_values[i];
            out.want = golden_values[i];
            return out;
        }
    }
    if (rtl_values.size() != golden_values.size()) {
        out.equal = false;
        out.divergence_index = static_cast<long long>(common);
        out.label = rtl_values.size() < golden_values.size()
                        ? "rtl trace ends early"
                        : "rtl trace runs long";
        out.got = rtl_values.size();
        out.want = golden_values.size();
    }
    return out;
}

}  // namespace trace

namespace inject {

// One golden engine result, consumed in issue order.  The opcode fields are
// checked against the RTL's issue before any word is supplied: an injection
// that does not match the issue it is answering is a divergence, not a fill.
struct Result {
    std::uint32_t family = 0;
    std::uint32_t sub = 0;
    std::uint32_t descriptor_id = 0;
    std::uint32_t pc = 0;
    std::uint32_t fault = 0;
    std::uint32_t trap_class = 0;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> words;
};

std::vector<Result> read(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read results " + path);
    std::vector<Result> out;
    std::string line;
    std::uint64_t remaining = 0;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string tag;
        fields >> tag;
        if (tag == "RESULT") {
            if (remaining != 0)
                throw std::runtime_error("truncated result body in " + path);
            Result record;
            std::uint64_t count = 0;
            if (!(fields >> record.family >> record.sub >>
                  record.descriptor_id >> record.pc >> record.fault >>
                  record.trap_class >> count))
                throw std::runtime_error("malformed RESULT line in " + path);
            remaining = count;
            out.push_back(std::move(record));
        } else if (tag == "WORD") {
            if (out.empty() || remaining == 0)
                throw std::runtime_error("stray WORD line in " + path);
            std::uint32_t address = 0;
            std::uint32_t data = 0;
            if (!(fields >> address >> data))
                throw std::runtime_error("malformed WORD line in " + path);
            out.back().words.emplace_back(address, data);
            --remaining;
        } else {
            throw std::runtime_error("unknown result tag '" + tag + "'");
        }
    }
    if (remaining != 0) throw std::runtime_error("truncated results " + path);
    return out;
}

}  // namespace inject

namespace headshard {

// Rung G1d, row-sharded.  The LM head is row-parallel: logit j is the dot
// product of the trunk vector with weight row j and nothing else, so
// partitioning the rows partitions the logits with no arithmetic crossing a
// shard boundary.  Four shards of 37,984 rows each is how the chip computes
// it, and it is what turns 4.33 h of RTL MAC time into 1.08 h wall.
struct Partition {
    std::uint64_t rows = 0;
    std::uint64_t shards = 0;
    std::vector<std::uint64_t> base;     // first row of each shard
    std::vector<std::uint64_t> extent;   // rows in each shard
};

Partition partition(std::uint64_t rows, std::uint64_t shards) {
    if (shards == 0 || rows % shards != 0)
        throw std::runtime_error("row count does not divide into shards");
    Partition out;
    out.rows = rows;
    out.shards = shards;
    const std::uint64_t each = rows / shards;
    for (std::uint64_t shard = 0; shard < shards; ++shard) {
        out.base.push_back(shard * each);
        out.extent.push_back(each);
    }
    return out;
}

// Exactness of the partition itself: contiguous, disjoint, covering.  Checked
// rather than asserted, because a silently overlapping shard would compose
// into a logit vector that still looks plausible.
bool partition_exact(const Partition& part) {
    std::uint64_t at = 0;
    for (std::uint64_t shard = 0; shard < part.shards; ++shard) {
        if (part.base[shard] != at) return false;
        at += part.extent[shard];
    }
    return at == part.rows;
}

// The composed argmax.  Two independent computations of the same answer: a
// flat scan of the composed vector, and the tournament the chip performs
// across shards.  They must agree, including the tie rule (lowest global
// index wins), or the composition is not exact.
struct Argmax {
    std::uint64_t index = 0;
    std::uint32_t code = 0;
};

Argmax flat_argmax(const std::vector<std::uint32_t>& logits) {
    Argmax out;
    bool first = true;
    for (std::size_t i = 0; i < logits.size(); ++i) {
        if (first || logits[i] > out.code) {
            out.index = i;
            out.code = logits[i];
            first = false;
        }
    }
    return out;
}

Argmax composed_argmax(const std::vector<std::vector<std::uint32_t>>& shards,
                       const Partition& part) {
    Argmax out;
    bool first = true;
    for (std::uint64_t shard = 0; shard < part.shards; ++shard) {
        const auto& logits = shards[shard];
        for (std::size_t i = 0; i < logits.size(); ++i) {
            const std::uint64_t global = part.base[shard] + i;
            if (first || logits[i] > out.code) {
                out.index = global;
                out.code = logits[i];
                first = false;
            }
        }
    }
    return out;
}

}  // namespace headshard



const char* env_or_null(const char* name) {
    const char* raw = std::getenv(name);
    if (raw == nullptr || *raw == '\0') return nullptr;
    return raw;
}

std::uint64_t env_u64(const char* name, std::uint64_t fallback) {
    const char* raw = env_or_null(name);
    return raw == nullptr ? fallback : std::strtoull(raw, nullptr, 0);
}

constexpr std::size_t kCases = 4;
// Two case-record generations, and the harness is told which by the vector
// set's own meta word rather than assuming one.  The legacy 80-word record
// carries no mapped placement, so the six families the issue bridge admits --
// DMA.SCATTER, ATTENTION.GQA, VECTOR.ADD, VECTOR.SILU_MUL, SELECTION.ARGMAX
// and SELECTION.TOKEN_APPEND -- have no bank bound to any object and the
// bridge refuses them with TRAP_CAPABILITY.  That refusal is measured here,
// not assumed: it is the pessimistic half of the two answers the programme's
// R13 rule says to publish.  The 112-word record carries the object->bank
// table, the request's context and generation policy, and the golden launch
// counts and selection outputs to compare against.
constexpr std::size_t kCaseStrideLegacy = 80;
constexpr std::size_t kCaseStridePlaced = 139;
// Case-record word offsets, valid only at kCaseStridePlaced.
constexpr std::size_t kPlaceSpanWord = 57;      // words the result region spans
constexpr std::size_t kPlaceValidWord = 58;     // object table supplied
constexpr std::size_t kMappedFamiliesWord = 59; // the six families admitted
constexpr std::size_t kPlaceTableWord = 60;     // 32 x (object id, base words)
constexpr std::size_t kPlaceTableEntries = 32;
constexpr std::size_t kMapContextWord = 124;   // request context length
constexpr std::size_t kMapPlaneRowsWord = 125; // KV K->V plane stride, rows
constexpr std::size_t kMapPolicyWord = 126;    // GENERATION_POLICY descriptor
constexpr std::size_t kMapMaxNewWord = 127;    // request max_new_tokens
constexpr std::size_t kMapGeneratedWord = 128; // tokens produced before this
constexpr std::size_t kMapLaunchWord = 129;    // 6 expected launch counts
constexpr std::size_t kMapTokenWord = 135;     // expected selected token
constexpr std::size_t kMapTieWord = 136;       // expected tie multiplicity
constexpr std::size_t kMapEosWord = 137;       // expected EOS reason
constexpr std::size_t kMapReservedWord = 138;  // reserved, must be zero
// What the vector set has to satisfy for the mapped words to be usable, all
// of it enforced inside rtl/abi3/ot_a3_engine_issue_bridge.sv rather than
// here, and none of it defaulted:
//   * every object a mapped operator's views name must appear in the table;
//     an object the table does not name is a DESCRIPTOR trap, not a guess.
//   * the scatter and attention INDEX view's object must be based in the
//     index bank (the bridge reads it with m0_reads_result low, so its base
//     plus resolved offset must be below INDEX_WORDS); every other mapped
//     object is a plane of the result bank the earlier operators produced.
//   * the KV cache object is one compact bank of 2 * kv_plane_rows * 1024
//     words: the K plane at the mapped base, the V plane a fixed
//     kv_plane_rows * 1024 words above it, so it does not move as the
//     context grows.  The declared view keeps the ABI's row stride 2048 and
//     plane offset 0 or 1024.
//   * context_length must equal the value the index view's own element holds
//     plus one, and must not exceed kv_plane_rows or the GQA datapath's
//     MAX_CONTEXT.
constexpr std::size_t kMappedFamilyCount = 6;
const char* const kMappedFamilyName[kMappedFamilyCount] = {
    "VECTOR.ADD", "VECTOR.SILU_MUL", "DMA.SCATTER",
    "ATTENTION.GQA", "SELECTION.ARGMAX", "SELECTION.TOKEN_APPEND"};
constexpr std::size_t kProgramWords = 4096;
constexpr std::size_t kDescWords = 8192;
constexpr std::size_t kSymbolsPerCase = 16;
constexpr std::size_t kIssueStride = 4;
// No hardcoded result-memory size: a ladder rung instantiating the top with
// a 151,936-word result memory (the LM head's logits) or a 1,400,832-word
// source memory (the KV cache) is checked at the size it was elaborated
// with, reported by the top itself through ot_a3_geometry_declare.
constexpr std::size_t kMulticastParticipants = 256;
constexpr std::uint32_t kMulticastWords = 16384;
constexpr std::uint32_t kMulticastWrites = 4194304;
constexpr std::uint32_t kUnwritten = 0xdeadbeefU;

std::uint32_t payload_word(std::uint32_t index) {
    return 0x9e3779b9U ^ (index * 0x045d9f3bU) ^
           ((index << 18) | (index << 4) | (index & 0xfU));
}

std::uint32_t expected_tree_source(std::uint32_t destination) {
    std::uint32_t power = 1;
    while ((power << 1) <= destination) power <<= 1;
    return destination - power;
}

std::vector<std::uint32_t> read_hex(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open " + path);
    std::vector<std::uint32_t> words;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::size_t used = 0;
        const auto value = std::stoull(line, &used, 16);
        if (used != line.size() || value > 0xffffffffULL)
            throw std::runtime_error("invalid 32-bit hex word in " + path);
        words.push_back(static_cast<std::uint32_t>(value));
    }
    return words;
}

// A wide device image: one row per line of `digits` hex digits, as 32-bit
// lanes in little-endian lane order (lane 0 is the last 8 digits), which is
// the lane order the design's host load path takes.
std::vector<std::vector<std::uint32_t>> read_rows(const std::string& path,
                                                  std::size_t digits,
                                                  std::size_t rows) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open " + path);
    std::vector<std::vector<std::uint32_t>> image;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        if (line.size() != digits)
            throw std::runtime_error("malformed image row in " + path);
        std::vector<std::uint32_t> lanes(digits / 8, 0);
        for (std::size_t lane = 0; lane < digits / 8; ++lane)
            lanes[lane] = static_cast<std::uint32_t>(
                std::stoul(line.substr(digits - 8 * (lane + 1), 8), nullptr, 16));
        image.push_back(lanes);
    }
    if (image.size() < rows)
        image.resize(rows, std::vector<std::uint32_t>(digits / 8, 0));
    return image;
}

struct Checker {
    std::uint64_t checks = 0;
    std::uint64_t failures = 0;

    void equal(std::string_view label, std::uint64_t got,
               std::uint64_t want) {
        ++checks;
        if (got != want) {
            ++failures;
            std::cerr << "FAIL: " << label << " got=" << got << " (0x"
                      << std::hex << got << ") want=" << std::dec << want
                      << " (0x" << std::hex << want << std::dec << ")\n";
        }
    }
};

struct Model {
    VerilatedContext context;
    Vot_a3_shipped_prefix_top dut{&context};

    Model() {
        dut.clk = 0;
        dut.rst_n = 0;
        dut.start = 0;
        dut.cfg_program_base = 0;
        dut.cfg_instruction_count = 0;
        dut.cfg_entry_pc = 0;
        dut.cfg_desc_base = 0;
        dut.cfg_desc_count = 0;
        dut.host_we = 0;
        dut.host_sel = 0;
        dut.host_row = 0;
        dut.host_lane = 0;
        dut.host_wdata = 0;
        dut.cfg_max_retired_work = 0;
        dut.cfg_state_count = 0;
        dut.cfg_index_base = 0;
        dut.cfg_source_base = 0;
        dut.cfg_source_launch_stride = 0;
        dut.cfg_embedding_source_base = 0;
        dut.cfg_transfer_index_base = 0;
        dut.cfg_transfer_source_base = 0;
        // No object is mapped until a case binds one.  UINT32_MAX is the
        // ABI's "no id", which the bridge's map lookup never matches, so an
        // unbound instance forms no operand address at all.
        dut.cfg_extended_placement_valid = 0;
        dut.cfg_place_object_0 = UINT32_MAX;
        dut.cfg_place_base_0 = 0;
        dut.cfg_place_object_1 = UINT32_MAX;
        dut.cfg_place_base_1 = 0;
        dut.cfg_place_object_2 = UINT32_MAX;
        dut.cfg_place_base_2 = 0;
        dut.cfg_place_object_3 = UINT32_MAX;
        dut.cfg_place_base_3 = 0;
        dut.cfg_place_object_4 = UINT32_MAX;
        dut.cfg_place_base_4 = 0;
        dut.cfg_place_object_5 = UINT32_MAX;
        dut.cfg_place_base_5 = 0;
        dut.cfg_place_object_6 = UINT32_MAX;
        dut.cfg_place_base_6 = 0;
        dut.cfg_place_object_7 = UINT32_MAX;
        dut.cfg_place_base_7 = 0;
        dut.cfg_place_object_8 = UINT32_MAX;
        dut.cfg_place_base_8 = 0;
        dut.cfg_place_object_9 = UINT32_MAX;
        dut.cfg_place_base_9 = 0;
        dut.cfg_place_object_10 = UINT32_MAX;
        dut.cfg_place_base_10 = 0;
        dut.cfg_place_object_11 = UINT32_MAX;
        dut.cfg_place_base_11 = 0;
        dut.cfg_place_object_12 = UINT32_MAX;
        dut.cfg_place_base_12 = 0;
        dut.cfg_place_object_13 = UINT32_MAX;
        dut.cfg_place_base_13 = 0;
        dut.cfg_place_object_14 = UINT32_MAX;
        dut.cfg_place_base_14 = 0;
        dut.cfg_place_object_15 = UINT32_MAX;
        dut.cfg_place_base_15 = 0;
        dut.cfg_place_object_16 = UINT32_MAX;
        dut.cfg_place_base_16 = 0;
        dut.cfg_place_object_17 = UINT32_MAX;
        dut.cfg_place_base_17 = 0;
        dut.cfg_place_object_18 = UINT32_MAX;
        dut.cfg_place_base_18 = 0;
        dut.cfg_place_object_19 = UINT32_MAX;
        dut.cfg_place_base_19 = 0;
        dut.cfg_place_object_20 = UINT32_MAX;
        dut.cfg_place_base_20 = 0;
        dut.cfg_place_object_21 = UINT32_MAX;
        dut.cfg_place_base_21 = 0;
        dut.cfg_place_object_22 = UINT32_MAX;
        dut.cfg_place_base_22 = 0;
        dut.cfg_place_object_23 = UINT32_MAX;
        dut.cfg_place_base_23 = 0;
        dut.cfg_place_object_24 = UINT32_MAX;
        dut.cfg_place_base_24 = 0;
        dut.cfg_place_object_25 = UINT32_MAX;
        dut.cfg_place_base_25 = 0;
        dut.cfg_place_object_26 = UINT32_MAX;
        dut.cfg_place_base_26 = 0;
        dut.cfg_place_object_27 = UINT32_MAX;
        dut.cfg_place_base_27 = 0;
        dut.cfg_place_object_28 = UINT32_MAX;
        dut.cfg_place_base_28 = 0;
        dut.cfg_place_object_29 = UINT32_MAX;
        dut.cfg_place_base_29 = 0;
        dut.cfg_place_object_30 = UINT32_MAX;
        dut.cfg_place_base_30 = 0;
        dut.cfg_place_object_31 = UINT32_MAX;
        dut.cfg_place_base_31 = 0;
        dut.cfg_context_length = 0;
        dut.cfg_kv_plane_rows = 0;
        dut.cfg_generation_policy_id = UINT32_MAX;
        dut.cfg_request_max_new_tokens = 0;
        dut.cfg_generated_before = 0;
        dut.cfg_matmul_weight_window_base = 0;
        dut.cfg_predicate_object = UINT32_MAX;
        dut.cfg_predicate_base = 0;
        dut.inj_result_valid = 0;
        dut.inj_result_fault = 0;
        dut.inj_result_trap_class = 0;
        dut.inj_write_en = 0;
        dut.inj_write_addr = 0;
        dut.inj_write_data = 0;
        dut.result_read_addr = 0;
        dut.eval();
    }

    template <class Observer>
    void cycle(Observer&& before_rising) {
        dut.clk = 0;
        dut.eval();
        before_rising();
        dut.clk = 1;
        dut.eval();
        context.timeInc(1);
        dut.clk = 0;
        dut.eval();
        context.timeInc(1);
    }

    void reset() {
        for (int i = 0; i < 4; ++i) cycle([] {});
        dut.rst_n = 1;
        for (int i = 0; i < 2; ++i) cycle([] {});
    }

    // One write through the design's host load path: one lane of one row.
    void host_write(unsigned sel, std::uint32_t row, unsigned lane,
                    std::uint32_t data) {
        dut.host_sel = sel;
        dut.host_row = row;
        dut.host_lane = lane;
        dut.host_wdata = data;
        dut.host_we = 1;
        cycle([] {});
        dut.host_we = 0;
    }
};


// ---------------------------------------------------------------------------
// Does the window actually hold the working set, and does it thrash?
//
// The sweep drives the SAME DPI path the RTL's weight port drives, over the
// whole declared image, and checks every halfword against an independent
// sequential reader with its own descriptors and its own buffer.  It then
// reports what it cost: wall time, throughput, the hard resident cap, the
// peak resident bytes, and -- the number that says whether the window is an
// improvement -- refilled_bytes over distinct_bytes.  A streaming operator
// refills each page once and the ratio is 1.0; a thrashing access pattern
// refills the same pages over and over and the ratio climbs, which is why it
// is reported rather than assumed.
// ---------------------------------------------------------------------------
namespace sweep {

struct Reader {
    const std::vector<weightwindow::Segment>* segments = nullptr;
    std::vector<int> fds;
    std::vector<std::uint8_t> buffer;
    std::uint64_t buffer_base = 1;   // empty
    std::uint64_t buffer_end = 0;

    explicit Reader(const std::vector<weightwindow::Segment>& from)
        : segments(&from), buffer(1u << 20) {
        for (const auto& segment : from) {
            const int fd = ::open(segment.path.c_str(), O_RDONLY);
            if (fd < 0)
                throw std::runtime_error("sweep cannot open " + segment.path);
            fds.push_back(fd);
        }
    }
    ~Reader() {
        for (int fd : fds)
            if (fd >= 0) ::close(fd);
    }

    std::uint32_t halfword(std::uint64_t index) {
        const std::uint64_t offset = index * 2ULL;
        if (offset < buffer_base || offset + 2 > buffer_end) refill(offset);
        const std::uint8_t* at = buffer.data() + (offset - buffer_base);
        return static_cast<std::uint32_t>(at[0]) |
               (static_cast<std::uint32_t>(at[1]) << 8);
    }

  private:
    void refill(std::uint64_t offset) {
        buffer_base = offset & ~static_cast<std::uint64_t>(buffer.size() - 1);
        buffer_end = buffer_base;
        std::fill(buffer.begin(), buffer.end(), 0);
        for (std::size_t i = 0; i < segments->size(); ++i) {
            const auto& segment = (*segments)[i];
            const std::uint64_t seg_lo = segment.image_base;
            const std::uint64_t seg_hi = seg_lo + segment.bytes;
            const std::uint64_t from =
                buffer_base > seg_lo ? buffer_base : seg_lo;
            const std::uint64_t to = (buffer_base + buffer.size()) < seg_hi
                                         ? (buffer_base + buffer.size())
                                         : seg_hi;
            if (from >= to) continue;
            std::uint64_t want = to - from;
            std::uint64_t at = segment.file_offset + (from - seg_lo);
            std::uint8_t* out = buffer.data() + (from - buffer_base);
            while (want != 0) {
                const ssize_t got = ::pread(fds[i], out,
                                            static_cast<std::size_t>(want),
                                            static_cast<off_t>(at));
                if (got <= 0)
                    throw std::runtime_error("sweep short read from " +
                                             segment.path);
                want -= static_cast<std::uint64_t>(got);
                at += static_cast<std::uint64_t>(got);
                out += got;
            }
        }
        buffer_end = buffer_base + buffer.size();
    }
};

int run(std::uint64_t image_bytes, Checker& check) {
    auto& win = weightwindow::window();
    Reader reader(win.segments());
    const std::uint64_t halfwords = image_bytes / 2;
    const auto start = std::chrono::steady_clock::now();
    std::uint64_t mismatches = 0;
    for (std::uint64_t index = 0; index < halfwords; ++index) {
        if (win.halfword(index) != reader.halfword(index)) {
            if (mismatches < 8)
                std::cerr << "FAIL: window halfword " << index
                          << " differs from an independent read\n";
            ++mismatches;
        }
    }
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count();
    check.equal("paged window equals an independent read", mismatches, 0);
    const auto& stats = win.stats();
    // Snapshot before the optional strided pass below, so the sequential
    // numbers the SWEEP line reports are the sequential ones.
    const std::uint64_t sequential_refilled = stats.bytes_faulted;
    const std::uint64_t sequential_faults = stats.page_faults;
    const std::uint64_t sequential_evictions = stats.pages_evicted;
    const std::uint64_t distinct = stats.distinct_pages * win.page_bytes();
    const double refill_ratio =
        distinct == 0 ? 0.0
                      : static_cast<double>(sequential_refilled) /
                            static_cast<double>(distinct);
    check.equal("every page of the image was reached",
                stats.distinct_pages,
                (image_bytes + win.page_bytes() - 1) / win.page_bytes());

    // The refill ratio is only worth reporting if it can rise.  Given a
    // stride, walk the image out of order and print what thrash looks like,
    // so the 1.0000 above is a measurement with a scale behind it rather
    // than a number that could not have come out otherwise.
    const std::uint64_t stride = env_u64("OT_A3_WINDOW_SWEEP_STRIDE", 0);
    if (stride != 0) {
        const weightwindow::Stats before = stats;
        const std::uint64_t probes =
            env_u64("OT_A3_WINDOW_SWEEP_PROBES", 200000);
        const auto strided_start = std::chrono::steady_clock::now();
        std::uint64_t at = 0;
        for (std::uint64_t probe = 0; probe < probes; ++probe) {
            (void)win.halfword(at);
            at += stride;
            if (at >= halfwords) at -= halfwords;
        }
        const double strided_seconds =
            std::chrono::duration<double>(
                std::chrono::steady_clock::now() - strided_start)
                .count();
        const std::uint64_t faulted = stats.bytes_faulted - before.bytes_faulted;
        const std::uint64_t touched =
            (stats.distinct_pages - before.distinct_pages) * win.page_bytes();
        std::cout << "SWEEPSTRIDE stride_halfwords=" << stride
                  << " probes=" << probes << " wall_s=" << std::fixed
                  << std::setprecision(3) << strided_seconds
                  << std::defaultfloat << " bytes_refilled=" << faulted
                  << " new_distinct_bytes=" << touched
                  << " bytes_refilled_per_probe="
                  << (probes ? faulted / probes : 0) << "\n";
    }
    std::cout << "SWEEP image_bytes=" << image_bytes
              << " halfwords=" << halfwords << " wall_s=" << std::fixed
              << std::setprecision(3) << seconds
              << " MB_per_s="
              << (seconds > 0 ? (static_cast<double>(image_bytes) /
                                 (1024.0 * 1024.0) / seconds)
                              : 0.0)
              << std::defaultfloat << " page_bytes=" << win.page_bytes()
              << " resident_cap_bytes=" << win.resident_cap_bytes()
              << " peak_resident_bytes=" << stats.peak_resident_bytes
              << " page_faults=" << sequential_faults
              << " pages_evicted=" << sequential_evictions
              << " distinct_bytes=" << distinct
              << " refilled_bytes=" << sequential_refilled
              << " refill_ratio=" << std::fixed << std::setprecision(4)
              << refill_ratio << std::defaultfloat
              << " mismatches=" << mismatches << "\n";
    return mismatches == 0 ? 0 : 1;
}

}  // namespace sweep


// ---------------------------------------------------------------------------
// Rung G1d in four row shards.
//
// The LM head is row-parallel: logit j is the dot product of the trunk vector
// with weight row j and with nothing else.  Partitioning the 151,936 rows
// therefore partitions the logits, and no arithmetic crosses a shard
// boundary -- which is why four shards of 37,984 rows are exact and not an
// approximation, and why the chip computes it that way.
//
// Two things have to be true and neither is assumed here:
//   1. the four windows tile the head exactly -- contiguous, disjoint,
//      covering -- and shard s's window is the flat head's rows
//      [s*37,984, (s+1)*37,984) and nothing else.  Checked halfword by
//      halfword against an independent read of the flat head.
//   2. the argmax over the composed logits is the argmax the shard
//      tournament produces, ties included.  Checked against a flat scan.
// ---------------------------------------------------------------------------
namespace headshard_mode {

int run(Checker& check) {
    const std::uint64_t rows = env_u64("OT_A3_HEAD_ROWS", 151936);
    const std::uint64_t columns = env_u64("OT_A3_HEAD_COLUMNS", 4096);
    const std::uint64_t shards = env_u64("OT_A3_HEAD_SHARDS", 4);
    const std::uint64_t index = env_u64("OT_A3_HEAD_SHARD", 0);

    const auto part = headshard::partition(rows, shards);
    check.equal("head row partition is exact",
                headshard::partition_exact(part) ? 1 : 0, 1);
    check.equal("head shard index in range", index < shards, 1);
    const std::uint64_t shard_rows = part.extent[index];
    const std::uint64_t shard_base_row = part.base[index];
    const std::uint64_t shard_bytes = shard_rows * columns * 2;
    check.equal("shard window byte count",
                g_geometry.matmul_weight_bytes, shard_bytes);

    // The flat head, read independently: its own descriptors, its own
    // buffer, none of the window's paging.
    std::vector<weightwindow::Segment> flat_segments;
    {
        std::ifstream input("p3_head_flat.txt");
        if (!input)
            throw std::runtime_error(
                "the head-shard mode needs p3_head_flat.txt: the flat LM head "
                "the four shards must compose back into");
        std::string line;
        while (std::getline(input, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream fields(line);
            weightwindow::Segment segment;
            fields >> segment.image_base >> segment.bytes >>
                segment.file_offset >> segment.path;
            flat_segments.push_back(segment);
        }
    }
    std::uint64_t flat_bytes = 0;
    for (const auto& segment : flat_segments) flat_bytes += segment.bytes;
    check.equal("flat head byte count", flat_bytes, rows * columns * 2);

    sweep::Reader reader(flat_segments);
    const std::uint64_t base_halfword = shard_base_row * columns;
    const std::uint64_t shard_halfwords = shard_rows * columns;
    const auto start = std::chrono::steady_clock::now();
    std::uint64_t mismatches = 0;
    for (std::uint64_t at = 0; at < shard_halfwords; ++at) {
        if (weightwindow::window().halfword(at) !=
            reader.halfword(base_halfword + at)) {
            if (mismatches < 8)
                std::cerr << "FAIL: shard " << index << " halfword " << at
                          << " is not the flat head's row-"
                          << (shard_base_row + at / columns) << " element\n";
            ++mismatches;
        }
    }
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count();
    check.equal("shard window is the flat head's own rows", mismatches, 0);

    const auto& stats = weightwindow::window().stats();
    std::cout << "HEADSHARD shard=" << index << " of " << shards
              << " base_row=" << shard_base_row << " rows=" << shard_rows
              << " columns=" << columns << " bytes=" << shard_bytes
              << " halfwords=" << shard_halfwords << " wall_s=" << std::fixed
              << std::setprecision(3) << seconds << std::defaultfloat
              << " peak_resident_bytes=" << stats.peak_resident_bytes
              << " refilled_bytes=" << stats.bytes_faulted
              << " mismatches=" << mismatches << "\n";
    return mismatches == 0 ? 0 : 1;
}

// The composition itself: the partition, and the argmax over it.  Run once,
// after the shards; it needs no weights, only the identity.
int compose(Checker& check) {
    const std::uint64_t rows = env_u64("OT_A3_HEAD_ROWS", 151936);
    const std::uint64_t shards = env_u64("OT_A3_HEAD_SHARDS", 4);
    const auto part = headshard::partition(rows, shards);
    check.equal("head row partition is exact",
                headshard::partition_exact(part) ? 1 : 0, 1);
    std::uint64_t covered = 0;
    for (std::uint64_t shard = 0; shard < shards; ++shard)
        covered += part.extent[shard];
    check.equal("shards cover every row", covered, rows);
    check.equal("shards are disjoint and contiguous", part.base[0], 0);

    // The argmax identity, on the composed vector and on the tournament.
    // Randomised with a fixed seed, then with deliberate ties: the tie rule
    // is what a naive per-shard reduction gets wrong, so it is the case that
    // is checked hardest.
    std::uint64_t state = 0x243f6a8885a308d3ULL;
    auto next = [&state]() {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        return static_cast<std::uint32_t>(state >> 32);
    };
    const std::uint64_t trials = env_u64("OT_A3_HEAD_ARGMAX_TRIALS", 2000);
    const auto small = headshard::partition(shards * 97, shards);
    std::uint64_t disagreements = 0;
    for (std::uint64_t trial = 0; trial < trials; ++trial) {
        std::vector<std::vector<std::uint32_t>> per_shard(shards);
        std::vector<std::uint32_t> composed;
        const bool tie_case = (trial % 3) == 0;
        const std::uint32_t tie_value = next() | 0x8000'0000u;
        for (std::uint64_t shard = 0; shard < shards; ++shard) {
            per_shard[shard].resize(small.extent[shard]);
            for (auto& value : per_shard[shard])
                value = tie_case ? (next() & 0x7fff'ffffu) : next();
            if (tie_case)
                // the same maximum in every shard: only the lowest global
                // index may win
                per_shard[shard][trial % small.extent[shard]] = tie_value;
            composed.insert(composed.end(), per_shard[shard].begin(),
                            per_shard[shard].end());
        }
        const auto flat = headshard::flat_argmax(composed);
        const auto tournament = headshard::composed_argmax(per_shard, small);
        if (flat.index != tournament.index || flat.code != tournament.code)
            ++disagreements;
    }
    check.equal("composed argmax equals the flat argmax", disagreements, 0);
    std::cout << "HEADCOMPOSE shards=" << shards << " rows=" << rows
              << " rows_per_shard=" << part.extent[0]
              << " argmax_trials=" << trials
              << " disagreements=" << disagreements << "\n";
    return disagreements == 0 ? 0 : 1;
}

}  // namespace headshard_mode

}  // namespace

// ---- DPI: the weight window and the elaborated geometry -------------------
// Signatures are Verilator's own, from Vot_a3_shipped_prefix_top__Dpi.h.
extern "C" unsigned long long ot_a3_weight_window_open(
    unsigned long long declared_bytes) {
    return weightwindow::window().open(declared_bytes);
}

extern "C" unsigned int ot_a3_weight_window_halfword(
    unsigned long long halfword_index) {
    return weightwindow::window().halfword(halfword_index);
}

extern "C" void ot_a3_geometry_declare(
    unsigned int program_words, unsigned int desc_words,
    unsigned int index_words, unsigned int source_words,
    unsigned int result_words, unsigned long long matmul_weight_bytes,
    unsigned int result_injection, unsigned int exact_multicast) {
    g_geometry.program_words = program_words;
    g_geometry.desc_words = desc_words;
    g_geometry.index_words = index_words;
    g_geometry.source_words = source_words;
    g_geometry.result_words = result_words;
    g_geometry.matmul_weight_bytes = matmul_weight_bytes;
    g_geometry.result_injection = result_injection;
    g_geometry.exact_multicast = exact_multicast;
    g_geometry.declared = true;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    try {
        const auto cases = read_hex("p3_case.hex");
        const auto issues = read_hex("p3_issue.hex");
        const auto expected = read_hex("p3_expect.hex");
        // The write STREAM the engines are required to produce: address then
        // value, one pair per word, in launch order.  Results are placed by
        // object, so a buffer the program rewrites is written twice at one
        // address and only the last value survives in the image above.
        // Comparing the image alone would stop checking every intermediate
        // that a later operator overwrote; this is what keeps that claim
        // true, and it also pins WHERE each word went, which an image compare
        // never did.
        const auto writes = read_hex("p3_writes.hex");
        const auto meta = read_hex("p3_meta.hex");
        const bool multicast_overlay = meta.size() == 27 && meta[1] == 29;
        const std::size_t expected_issue_words =
            multicast_overlay ? 132 : 128;
        // The vector set states its own case stride.  Only the two published
        // generations are accepted; anything else is a vector set this
        // checker has not been qualified against and is refused rather than
        // interpreted.
        const std::size_t case_stride = meta.size() > 4 ? meta[4] : 0;
        const bool mapped_placement_vectors =
            case_stride == kCaseStridePlaced;
        if ((case_stride != kCaseStrideLegacy &&
             case_stride != kCaseStridePlaced) ||
            cases.size() != kCases * case_stride ||
            issues.size() != expected_issue_words ||
            meta.size() != 27 || expected.size() != meta[26] ||
            writes.size() != 2 * meta[2] || meta[2] != 91136)
            throw std::runtime_error("shipped-prefix vector geometry mismatch");

        // The host's copies of the control images (docs/CHIP_ARCHITECTURE_
        // DESIGN.md section 13 item 12): written through the design's load
        // path, never preloaded into the wrapper.
        const auto image_program = read_rows("a3_program.hex", 64, kProgramWords);
        const auto image_desc = read_rows("a3_descriptor.hex", 384, kDescWords);
        const auto image_symbol = read_hex("a3_symbol.hex");

        // -- optional G1e modes.  Absent every one of these the checker
        // -- runs exactly as it did before, with the same checks.
        const char* trace_out_path = env_or_null("OT_A3_TRACE_OUT");
        const char* golden_trace_path = env_or_null("OT_A3_GOLDEN_TRACE");
        const char* inject_path = env_or_null("OT_A3_INJECT_RESULTS");
        const std::uint64_t cycle_guard_limit =
            env_u64("OT_A3_CYCLE_GUARD", 64000000000ULL);

        std::vector<inject::Result> injected;
        if (inject_path != nullptr) injected = inject::read(inject_path);

        Checker check;
        Model model;
        if (!g_geometry.declared)
            throw std::runtime_error("the top declared no geometry");

        // Sizing measurement: sweep the whole declared weight image through
        // the very DPI path the RTL's weight port uses, check it against an
        // independent reader, and report what it cost.  Nothing else runs.
        if (env_or_null("OT_A3_HEAD_COMPOSE") != nullptr) {
            const int status = headshard_mode::compose(check);
            if (check.failures != 0) {
                std::cerr << "FAILURES: " << check.failures
                          << " checks=" << check.checks << "\n";
                return 1;
            }
            std::cout << "PASS: ABI3 LM-head shard composition checks="
                      << check.checks << "\n";
            return status;
        }
        if (env_or_null("OT_A3_HEAD_SHARD") != nullptr) {
            const int status = headshard_mode::run(check);
            if (check.failures != 0) {
                std::cerr << "FAILURES: " << check.failures
                          << " checks=" << check.checks << "\n";
                return 1;
            }
            std::cout << "PASS: ABI3 LM-head row shard checks="
                      << check.checks << "\n";
            return status;
        }
        if (env_or_null("OT_A3_WINDOW_SWEEP") != nullptr) {
            const int status =
                sweep::run(g_geometry.matmul_weight_bytes, check);
            if (check.failures != 0) {
                std::cerr << "FAILURES: " << check.failures
                          << " checks=" << check.checks << "\n";
                return 1;
            }
            std::cout << "PASS: ABI3 weight-window sweep image_bytes="
                      << g_geometry.matmul_weight_bytes
                      << " checks=" << check.checks << "\n";
            return status;
        }
        if (inject_path != nullptr && g_geometry.result_injection == 0)
            throw std::runtime_error(
                "OT_A3_INJECT_RESULTS needs ENABLE_RESULT_INJECTION=1");
        if (inject_path == nullptr && g_geometry.result_injection != 0)
            throw std::runtime_error(
                "ENABLE_RESULT_INJECTION=1 needs OT_A3_INJECT_RESULTS");
        const bool injecting = inject_path != nullptr;
        const bool tracing =
            trace_out_path != nullptr || golden_trace_path != nullptr;
        trace::Record rtl_trace;
        std::vector<trace::View> pending_views;
        std::size_t injected_at = 0;
        std::size_t injected_word_at = 0;
        bool injected_serving = false;
        std::uint64_t last_issue_serial = 0;
        const auto wall_start = std::chrono::steady_clock::now();
        std::uint64_t total_cycles = 0;
        double sim_seconds = 0.0;

        model.reset();
        model.dut.eval();
        check.equal("host ready before load", model.dut.host_ready, 1);
        for (std::size_t row = 0; row < kProgramWords; ++row)
            for (unsigned lane = 0; lane < 8; ++lane)
                model.host_write(0, static_cast<std::uint32_t>(row), lane,
                                 image_program[row][lane]);
        for (std::size_t row = 0; row < kDescWords; ++row)
            for (unsigned lane = 0; lane < 48; ++lane)
                model.host_write(1, static_cast<std::uint32_t>(row), lane,
                                 image_desc[row][lane]);
        model.cycle([] {});
        check.equal("no write refused during load",
                    model.dut.host_write_refused, 0);

        // -- entry probe: what the control plane does at a given entry PC --
        // ABI 3.0 events are transaction-scoped, so an entry PC that skips a
        // family's wait-set producers cannot execute that family at all: the
        // event scoreboard refuses before dispatch.  This mode replays a plan
        // of (case, entry_pc, instruction_count) triples and reports the
        // sequencer's own verdict for each -- the trap class, the PC it
        // trapped at, and whether anything issued.  Nothing here is compared
        // against a vector set: it is a measurement of the control plane, and
        // the campaign that drives it compares it against a derivation made
        // independently from the deployed program.
        if (const char* probe_path = env_or_null("OT_A3_ENTRY_PROBE")) {
            std::ifstream plan(probe_path);
            if (!plan) throw std::runtime_error("cannot open the entry probe plan");
            std::size_t probes = 0;
            std::string line;
            while (std::getline(plan, line)) {
                if (line.empty() || line[0] == '#') continue;
                std::istringstream fields(line);
                std::size_t case_index = 0;
                std::uint32_t entry_pc = 0;
                std::uint32_t bound = 0;
                if (!(fields >> case_index >> entry_pc >> bound))
                    throw std::runtime_error("malformed entry probe line");
                if (case_index >= kCases)
                    throw std::runtime_error("entry probe names no such case");
                const auto* record = &cases[case_index * case_stride];
                model.dut.cfg_program_base = record[0];
                model.dut.cfg_instruction_count = bound;
                model.dut.cfg_desc_base = record[2];
                model.dut.cfg_desc_count = record[3];
                for (unsigned symbol = 0; symbol < kSymbolsPerCase; ++symbol) {
                    const std::size_t at = record[4] + symbol;
                    model.host_write(2, symbol, 0,
                                     at < image_symbol.size() ? image_symbol[at] : 0);
                    model.host_write(2, symbol, 1, 0);
                    model.host_write(2, symbol, 2, (record[5] >> symbol) & 1U);
                }
                model.dut.cfg_entry_pc = entry_pc;
                model.dut.cfg_max_retired_work =
                    (static_cast<std::uint64_t>(record[8]) << 32) | record[7];
                model.dut.cfg_state_count = record[9];
                model.dut.cfg_index_base = record[10];
                model.dut.cfg_source_base = record[11];
                model.dut.cfg_source_launch_stride = record[12];
                model.dut.cfg_embedding_source_base = record[32];
                model.dut.cfg_transfer_index_base = record[40];
                model.dut.cfg_transfer_source_base = record[41];
            {
                // The object placement table, driven for every family.  The
                // vector set states each object's base once; the bridge
                // refuses a table naming one object twice, and refuses any
                // operand or result whose object the table does not name.
                const bool placed = record[kPlaceValidWord] != 0;
                for (std::size_t entry = 0; entry < kPlaceTableEntries;
                     ++entry) {
                    const std::uint32_t object = placed
                        ? record[kPlaceTableWord + entry * 2] : UINT32_MAX;
                    const std::uint32_t base = placed
                        ? record[kPlaceTableWord + entry * 2 + 1] : 0U;
                    switch (entry) {
                    case 0:
                        model.dut.cfg_place_object_0 = object;
                        model.dut.cfg_place_base_0 = base;
                        break;
                    case 1:
                        model.dut.cfg_place_object_1 = object;
                        model.dut.cfg_place_base_1 = base;
                        break;
                    case 2:
                        model.dut.cfg_place_object_2 = object;
                        model.dut.cfg_place_base_2 = base;
                        break;
                    case 3:
                        model.dut.cfg_place_object_3 = object;
                        model.dut.cfg_place_base_3 = base;
                        break;
                    case 4:
                        model.dut.cfg_place_object_4 = object;
                        model.dut.cfg_place_base_4 = base;
                        break;
                    case 5:
                        model.dut.cfg_place_object_5 = object;
                        model.dut.cfg_place_base_5 = base;
                        break;
                    case 6:
                        model.dut.cfg_place_object_6 = object;
                        model.dut.cfg_place_base_6 = base;
                        break;
                    case 7:
                        model.dut.cfg_place_object_7 = object;
                        model.dut.cfg_place_base_7 = base;
                        break;
                    case 8:
                        model.dut.cfg_place_object_8 = object;
                        model.dut.cfg_place_base_8 = base;
                        break;
                    case 9:
                        model.dut.cfg_place_object_9 = object;
                        model.dut.cfg_place_base_9 = base;
                        break;
                    case 10:
                        model.dut.cfg_place_object_10 = object;
                        model.dut.cfg_place_base_10 = base;
                        break;
                    case 11:
                        model.dut.cfg_place_object_11 = object;
                        model.dut.cfg_place_base_11 = base;
                        break;
                    case 12:
                        model.dut.cfg_place_object_12 = object;
                        model.dut.cfg_place_base_12 = base;
                        break;
                    case 13:
                        model.dut.cfg_place_object_13 = object;
                        model.dut.cfg_place_base_13 = base;
                        break;
                    case 14:
                        model.dut.cfg_place_object_14 = object;
                        model.dut.cfg_place_base_14 = base;
                        break;
                    case 15:
                        model.dut.cfg_place_object_15 = object;
                        model.dut.cfg_place_base_15 = base;
                        break;
                    case 16:
                        model.dut.cfg_place_object_16 = object;
                        model.dut.cfg_place_base_16 = base;
                        break;
                    case 17:
                        model.dut.cfg_place_object_17 = object;
                        model.dut.cfg_place_base_17 = base;
                        break;
                    case 18:
                        model.dut.cfg_place_object_18 = object;
                        model.dut.cfg_place_base_18 = base;
                        break;
                    case 19:
                        model.dut.cfg_place_object_19 = object;
                        model.dut.cfg_place_base_19 = base;
                        break;
                    case 20:
                        model.dut.cfg_place_object_20 = object;
                        model.dut.cfg_place_base_20 = base;
                        break;
                    case 21:
                        model.dut.cfg_place_object_21 = object;
                        model.dut.cfg_place_base_21 = base;
                        break;
                    case 22:
                        model.dut.cfg_place_object_22 = object;
                        model.dut.cfg_place_base_22 = base;
                        break;
                    case 23:
                        model.dut.cfg_place_object_23 = object;
                        model.dut.cfg_place_base_23 = base;
                        break;
                    case 24:
                        model.dut.cfg_place_object_24 = object;
                        model.dut.cfg_place_base_24 = base;
                        break;
                    case 25:
                        model.dut.cfg_place_object_25 = object;
                        model.dut.cfg_place_base_25 = base;
                        break;
                    case 26:
                        model.dut.cfg_place_object_26 = object;
                        model.dut.cfg_place_base_26 = base;
                        break;
                    case 27:
                        model.dut.cfg_place_object_27 = object;
                        model.dut.cfg_place_base_27 = base;
                        break;
                    case 28:
                        model.dut.cfg_place_object_28 = object;
                        model.dut.cfg_place_base_28 = base;
                        break;
                    case 29:
                        model.dut.cfg_place_object_29 = object;
                        model.dut.cfg_place_base_29 = base;
                        break;
                    case 30:
                        model.dut.cfg_place_object_30 = object;
                        model.dut.cfg_place_base_30 = base;
                        break;
                    case 31:
                        model.dut.cfg_place_object_31 = object;
                        model.dut.cfg_place_base_31 = base;
                        break;
                    default: break;
                    }
                }
            }
            // -- the six mapped families, under an entry probe too ---------
            // This path used to leave ``cfg_extended_placement_valid`` at its
            // reset value while the main path drove it from the case record,
            // so every probe measured a machine configured DIFFERENTLY from
            // the one the campaign measures: the six mapped families were
            // gated off no matter what the record said, and a probe span that
            // ends in SELECTION.ARGMAX could not have reached an admission
            // decision about it even with every object placed and every
            // geometry admitted.  A probe that cannot reach the question it
            // is asked is not a measurement of the design.  The record's own
            // word decides it here exactly as it does there -- same field,
            // same guard, same UINT32_MAX for an unbound policy id -- so a
            // vector set that carries no golden past its fail-stop boundary
            // still gets TRAP_CAPABILITY, and one that opts in gets the
            // admission walk.
            {
                const bool mapped = mapped_placement_vectors &&
                                    record[kMappedFamiliesWord] != 0;
                model.dut.cfg_extended_placement_valid = mapped ? 1 : 0;
                model.dut.cfg_context_length =
                    mapped ? record[kMapContextWord] : 0U;
                model.dut.cfg_kv_plane_rows =
                    mapped ? record[kMapPlaneRowsWord] : 0U;
                model.dut.cfg_generation_policy_id =
                    mapped ? record[kMapPolicyWord] : UINT32_MAX;
                model.dut.cfg_request_max_new_tokens =
                    mapped ? record[kMapMaxNewWord] : 0U;
                model.dut.cfg_generated_before =
                    mapped ? record[kMapGeneratedWord] : 0U;
            }
                model.dut.start = 1;
                model.cycle([] {});
                model.dut.start = 0;
                std::uint64_t guard = 0;
                while (!model.dut.done && guard < cycle_guard_limit) {
                    model.cycle([] {});
                    ++guard;
                }
                if (!model.dut.done)
                    throw std::runtime_error("entry probe did not terminate");
                std::cout << "PROBE case=" << case_index
                          << " entry=" << entry_pc << " ic=" << bound
                          << " trap=" << model.dut.trap_class
                          << " fault=" << model.dut.first_fault_instruction
                          << " launches=" << model.dut.real_launch_count
                          << " issued=" << model.dut.count_issued
                          << " fetched=" << model.dut.count_fetched
                          << " retired=" << model.dut.count_retired
                          << " capability=" << model.dut.capability_fault_count
                          << " cycles=" << guard << "\n";
                // A SECOND line, never a wider PROBE line: the existing
                // campaign's parser is anchored on the end of that one and a
                // new field there would silently stop matching.  This carries
                // what the six mapped families did, which the PROBE line has
                // never been able to say.
                std::cout << "PROBEMAPPED case=" << case_index
                          << " admitted="
                          << static_cast<unsigned>(
                                 model.dut.cfg_extended_placement_valid)
                          << " vector_add="
                          << model.dut.vector_add_launch_count
                          << " vector_silu_mul="
                          << model.dut.vector_silu_mul_launch_count
                          << " dma_scatter="
                          << model.dut.dma_scatter_launch_count
                          << " attention_gqa="
                          << model.dut.attention_gqa_launch_count
                          << " selection_argmax="
                          << model.dut.selection_argmax_launch_count
                          << " selection_token_append="
                          << model.dut.selection_token_append_launch_count
                          << " matmul=" << model.dut.matmul_launch_count
                          << " rms_norm=" << model.dut.rms_norm_launch_count
                          << " dma_gather="
                          << model.dut.dma_gather_launch_count
                          << " token=" << model.dut.selected_token
                          << " tie=" << model.dut.selected_tie_multiplicity
                          << " eos="
                          << static_cast<unsigned>(
                                 model.dut.selected_eos_reason)
                          << "\n";
                ++probes;
                model.cycle([] {});
            }
            // The image load's own checks still bind: a probe run that
            // loaded the stores badly measures the wrong machine, and must
            // not print a marker that says otherwise.
            if (check.failures != 0) {
                std::cerr << "FAILURES: " << check.failures
                          << " checks=" << check.checks << "\n";
                return 1;
            }
            std::cout << "PASS: ABI3 vehicle entry probe probes=" << probes
                      << " checks=" << check.checks << "\n";
            return 0;
        }

        check.equal("meta case count", meta[0], kCases);
        check.equal("meta case stride", meta[4], case_stride);
        check.equal("meta result memory", meta[7], g_geometry.result_words);
        check.equal("meta DMA gathers", meta[8], 6);
        check.equal("meta embedding launches", meta[9], 4);
        check.equal("meta RoPE coefficient gather words", meta[10], 1024);
        check.equal("meta selected checkpoint bytes", meta[11], 100713472);
        check.equal("meta RMSNorm launches", meta[12], 2);
        check.equal("meta transfer launches", meta[13], 2);
        check.equal("meta RMSNorm words", meta[14], 8192);
        check.equal("meta transfer words", meta[15], 32768);
        check.equal("meta MATMUL launches", meta[16], 6);
        check.equal("meta MATMUL words", meta[17], 12288);
        check.equal("meta MATMUL MACs", meta[18], 50331648);
        check.equal("meta MATMUL checkpoint bytes", meta[19], 100663296);
        check.equal("meta head RMSNorm launches", meta[20], 4);
        check.equal("meta head RMSNorm words", meta[21], 10240);
        check.equal("meta head RMSNorm checkpoint bytes", meta[22], 1024);
        check.equal("meta all RMSNorm launches", meta[23], 6);
        check.equal("meta RoPE launches", meta[24], 4);
        check.equal("meta RoPE output words", meta[25], 10240);

        std::uint64_t total_responses = 0;
        std::uint64_t total_launches = 0;
        std::uint64_t total_gathers = 0;
        std::uint64_t total_embeddings = 0;
        std::uint64_t total_rms_norms = 0;
        std::uint64_t total_head_rms_norms = 0;
        std::uint64_t total_ropes = 0;
        std::uint64_t total_transfers = 0;
        std::uint64_t total_matmuls = 0;
        std::uint64_t total_multicasts = 0;
        std::uint64_t total_words = 0;
        // Where the golden write stream has got to.  It runs across the whole
        // campaign in launch order, so a case that writes one word too few is
        // caught by the next case's very first address rather than only at
        // the end.
        std::size_t write_cursor = 0;
        std::uint64_t total_views = 0;
        // Reached, per family, in THIS vehicle: the bridge launched it at
        // least once and the case it launched in compared its result words
        // against golden without a failure.  Nothing is inferred from the
        // bridge's own qualification campaign; a family this top never
        // launched is trapped here whatever another vehicle measured.
        std::uint64_t mapped_launches[kMappedFamilyCount] = {0, 0, 0, 0, 0, 0};
        std::uint64_t mapped_cases_with_placement = 0;

        for (std::size_t case_index = 0; case_index < kCases; ++case_index) {
            const auto* record = &cases[case_index * case_stride];
            model.dut.cfg_program_base = record[0];
            model.dut.cfg_instruction_count = record[1];
            model.dut.cfg_desc_base = record[2];
            model.dut.cfg_desc_count = record[3];
            // the request's sixteen symbols, through the host path
            for (unsigned symbol = 0; symbol < kSymbolsPerCase; ++symbol) {
                const std::size_t at = record[4] + symbol;
                model.host_write(2, symbol, 0,
                                 at < image_symbol.size() ? image_symbol[at] : 0);
                model.host_write(2, symbol, 1, 0);
                model.host_write(2, symbol, 2, (record[5] >> symbol) & 1U);
            }
            check.equal("no symbol write refused",
                        model.dut.host_write_refused, 0);
            model.dut.cfg_entry_pc = record[6];
            model.dut.cfg_max_retired_work =
                (static_cast<std::uint64_t>(record[8]) << 32) | record[7];
            model.dut.cfg_state_count = record[9];
            model.dut.cfg_index_base = record[10];
            model.dut.cfg_source_base = record[11];
            model.dut.cfg_source_launch_stride = record[12];
            model.dut.cfg_embedding_source_base = record[32];
            model.dut.cfg_transfer_index_base = record[40];
            model.dut.cfg_transfer_source_base = record[41];
            {
                // The object placement table, driven for every family.  The
                // vector set states each object's base once; the bridge
                // refuses a table naming one object twice, and refuses any
                // operand or result whose object the table does not name.
                const bool placed = record[kPlaceValidWord] != 0;
                for (std::size_t entry = 0; entry < kPlaceTableEntries;
                     ++entry) {
                    const std::uint32_t object = placed
                        ? record[kPlaceTableWord + entry * 2] : UINT32_MAX;
                    const std::uint32_t base = placed
                        ? record[kPlaceTableWord + entry * 2 + 1] : 0U;
                    switch (entry) {
                    case 0:
                        model.dut.cfg_place_object_0 = object;
                        model.dut.cfg_place_base_0 = base;
                        break;
                    case 1:
                        model.dut.cfg_place_object_1 = object;
                        model.dut.cfg_place_base_1 = base;
                        break;
                    case 2:
                        model.dut.cfg_place_object_2 = object;
                        model.dut.cfg_place_base_2 = base;
                        break;
                    case 3:
                        model.dut.cfg_place_object_3 = object;
                        model.dut.cfg_place_base_3 = base;
                        break;
                    case 4:
                        model.dut.cfg_place_object_4 = object;
                        model.dut.cfg_place_base_4 = base;
                        break;
                    case 5:
                        model.dut.cfg_place_object_5 = object;
                        model.dut.cfg_place_base_5 = base;
                        break;
                    case 6:
                        model.dut.cfg_place_object_6 = object;
                        model.dut.cfg_place_base_6 = base;
                        break;
                    case 7:
                        model.dut.cfg_place_object_7 = object;
                        model.dut.cfg_place_base_7 = base;
                        break;
                    case 8:
                        model.dut.cfg_place_object_8 = object;
                        model.dut.cfg_place_base_8 = base;
                        break;
                    case 9:
                        model.dut.cfg_place_object_9 = object;
                        model.dut.cfg_place_base_9 = base;
                        break;
                    case 10:
                        model.dut.cfg_place_object_10 = object;
                        model.dut.cfg_place_base_10 = base;
                        break;
                    case 11:
                        model.dut.cfg_place_object_11 = object;
                        model.dut.cfg_place_base_11 = base;
                        break;
                    case 12:
                        model.dut.cfg_place_object_12 = object;
                        model.dut.cfg_place_base_12 = base;
                        break;
                    case 13:
                        model.dut.cfg_place_object_13 = object;
                        model.dut.cfg_place_base_13 = base;
                        break;
                    case 14:
                        model.dut.cfg_place_object_14 = object;
                        model.dut.cfg_place_base_14 = base;
                        break;
                    case 15:
                        model.dut.cfg_place_object_15 = object;
                        model.dut.cfg_place_base_15 = base;
                        break;
                    case 16:
                        model.dut.cfg_place_object_16 = object;
                        model.dut.cfg_place_base_16 = base;
                        break;
                    case 17:
                        model.dut.cfg_place_object_17 = object;
                        model.dut.cfg_place_base_17 = base;
                        break;
                    case 18:
                        model.dut.cfg_place_object_18 = object;
                        model.dut.cfg_place_base_18 = base;
                        break;
                    case 19:
                        model.dut.cfg_place_object_19 = object;
                        model.dut.cfg_place_base_19 = base;
                        break;
                    case 20:
                        model.dut.cfg_place_object_20 = object;
                        model.dut.cfg_place_base_20 = base;
                        break;
                    case 21:
                        model.dut.cfg_place_object_21 = object;
                        model.dut.cfg_place_base_21 = base;
                        break;
                    case 22:
                        model.dut.cfg_place_object_22 = object;
                        model.dut.cfg_place_base_22 = base;
                        break;
                    case 23:
                        model.dut.cfg_place_object_23 = object;
                        model.dut.cfg_place_base_23 = base;
                        break;
                    case 24:
                        model.dut.cfg_place_object_24 = object;
                        model.dut.cfg_place_base_24 = base;
                        break;
                    case 25:
                        model.dut.cfg_place_object_25 = object;
                        model.dut.cfg_place_base_25 = base;
                        break;
                    case 26:
                        model.dut.cfg_place_object_26 = object;
                        model.dut.cfg_place_base_26 = base;
                        break;
                    case 27:
                        model.dut.cfg_place_object_27 = object;
                        model.dut.cfg_place_base_27 = base;
                        break;
                    case 28:
                        model.dut.cfg_place_object_28 = object;
                        model.dut.cfg_place_base_28 = base;
                        break;
                    case 29:
                        model.dut.cfg_place_object_29 = object;
                        model.dut.cfg_place_base_29 = base;
                        break;
                    case 30:
                        model.dut.cfg_place_object_30 = object;
                        model.dut.cfg_place_base_30 = base;
                        break;
                    case 31:
                        model.dut.cfg_place_object_31 = object;
                        model.dut.cfg_place_base_31 = base;
                        break;
                    default: break;
                    }
                }
            }
            // -- the six mapped families, admitted or refused --------------
            // Whether the six families may run at all is a different
            // question from where objects live, and the record answers it in
            // its own word.  A vector set that stops at its fail-stop
            // boundary carries no golden past it and says so here; the bridge
            // then answers TRAP_CAPABILITY, which is a measurement rather
            // than an unconnected pin.
            {
                const bool mapped = mapped_placement_vectors &&
                                    record[kMappedFamiliesWord] != 0;
                model.dut.cfg_extended_placement_valid = mapped ? 1 : 0;
                model.dut.cfg_context_length =
                    mapped ? record[kMapContextWord] : 0U;
                model.dut.cfg_kv_plane_rows =
                    mapped ? record[kMapPlaneRowsWord] : 0U;
                model.dut.cfg_generation_policy_id =
                    mapped ? record[kMapPolicyWord] : UINT32_MAX;
                model.dut.cfg_request_max_new_tokens =
                    mapped ? record[kMapMaxNewWord] : 0U;
                model.dut.cfg_generated_before =
                    mapped ? record[kMapGeneratedWord] : 0U;
                if (mapped) {
                    ++mapped_cases_with_placement;
                    check.equal("mapped record reserved word",
                                record[kMapReservedWord], 0);
                }
            }

            last_issue_serial = 0;
            std::uint64_t case_writes_seen = 0;
            model.dut.result_read_addr = record[13];
            model.dut.eval();
            check.equal("result initially unwritten",
                        model.dut.result_read_data, kUnwritten);

            std::uint32_t response_seen = 0;
            const std::uint32_t response_expected = record[21];
            const std::uint32_t response_base = record[31];
            std::uint64_t observed_multicast_writes = 0;
            std::vector<std::uint32_t> next_multicast_word(
                kMulticastParticipants, 0);
            std::vector<std::uint32_t> participant_writes(
                kMulticastParticipants, 0);
            // The G1e engine-result boundary and the issue trace.  Ordered
            // deliberately: drive the injected completion, settle, and only
            // then observe -- so the handshake is seen in the cycle it
            // happens, exactly as the real engine's is.  Nothing here is an
            // input to fetch, decode, view resolution, predicates, the loop
            // stack, the wait set or queue acceptance.
            auto drive_injection = [&]() {
                if (!injecting) return;
                model.dut.inj_write_en = 0;
                model.dut.inj_result_valid = 0;
                model.dut.inj_result_fault = 0;
                model.dut.inj_result_trap_class = 0;
                if (!model.dut.rst_n || !model.dut.inj_issue_valid) {
                    model.dut.eval();
                    return;
                }
                if (injected_at >= injected.size()) {
                    ++check.failures;
                    std::cerr << "FAIL: RTL issued past the golden result "
                                 "stream at issue "
                              << injected_at << "\n";
                    model.dut.eval();
                    return;
                }
                const auto& record = injected[injected_at];
                if (!injected_serving) {
                    injected_serving = true;
                    injected_word_at = 0;
                    // The injected result must answer the issue the RTL
                    // actually made.  A mismatch is a divergence, not a fill.
                    check.equal("injected result opcode",
                                (static_cast<std::uint32_t>(
                                     model.dut.inj_issue_family)
                                 << 8) |
                                    model.dut.inj_issue_sub,
                                (record.family << 8) | record.sub);
                    check.equal("injected result descriptor",
                                model.dut.inj_issue_descriptor_id,
                                record.descriptor_id);
                    check.equal("injected result pc",
                                model.dut.inj_issue_index, record.pc);
                }
                if (injected_word_at < record.words.size()) {
                    model.dut.inj_write_en = 1;
                    model.dut.inj_write_addr =
                        record.words[injected_word_at].first;
                    model.dut.inj_write_data =
                        record.words[injected_word_at].second;
                    ++injected_word_at;
                } else {
                    model.dut.inj_result_valid = 1;
                    model.dut.inj_result_fault = record.fault;
                    model.dut.inj_result_trap_class = record.trap_class;
                    injected_serving = false;
                    ++injected_at;
                }
                model.dut.eval();
            };

            auto capture_trace = [&]() {
                if (!tracing || !model.dut.rst_n) return;
                if (model.dut.trace_view_valid) {
                    trace::View view;
                    view.slot = model.dut.trace_view_slot;
                    view.descriptor_id = model.dut.trace_view_descriptor_id;
                    view.extent = model.dut.trace_view_extent;
                    view.extent_axis = model.dut.trace_view_extent_axis;
                    view.element_offset = model.dut.trace_view_element_offset;
                    view.rank = model.dut.trace_view_rank;
                    view.irs_slot = model.dut.trace_view_irs_slot;
                    pending_views.push_back(view);
                }
                if (!model.dut.trace_issue_valid) return;
                trace::Issue issue;
                issue.serial = model.dut.trace_issue_serial;
                issue.family = model.dut.trace_issue_family;
                issue.sub = model.dut.trace_issue_sub;
                issue.descriptor_id = model.dut.trace_issue_descriptor_id;
                issue.pc = model.dut.trace_issue_index;
                issue.queue = model.dut.trace_issue_queue;
                issue.irs_slot = model.dut.trace_issue_slot;
                // Views are attached to the issue they were resolved for and
                // ordered by slot, so the record is a function of the data
                // and not of RTL timing.
                std::sort(pending_views.begin(), pending_views.end(),
                          [](const trace::View& a, const trace::View& b) {
                              return a.slot < b.slot;
                          });
                issue.views = pending_views;
                pending_views.clear();
                // The serial must advance, and the schedule must be a real
                // queue: fields a golden trace may not carry are still not
                // left unexamined.
                // The sequencer restarts its program-order serial at every
                // transaction, so monotonicity is a within-case property.
                check.equal("issue serial advances",
                            issue.serial > last_issue_serial, 1);
                last_issue_serial = issue.serial;
                check.equal("issue queue in range", issue.queue < 32, 1);
                rtl_trace.issues.push_back(std::move(issue));
            };

            auto observe = [&]() {
                drive_injection();
                capture_trace();
                // -- every result word, compared where and when it is written
                // The bridge's write is stable for the whole cycle whose
                // rising edge commits it, so sampling here sees each write
                // exactly once and in order.  Both halves are checked: the
                // ADDRESS, which is the whole object-placement claim, and the
                // VALUE.  Under injection the words come from the model, so
                // there is nothing of the engines' to compare.
                if (model.dut.rst_n && !injecting &&
                    model.dut.obs_write_valid) {
                    if (write_cursor + 2 > writes.size()) {
                        ++check.failures;
                        std::cerr << "FAIL: case " << case_index
                                  << " wrote more result words than the "
                                     "golden write stream holds\n";
                    } else {
                        check.equal("result write address",
                                    model.dut.obs_write_addr,
                                    writes[write_cursor]);
                        check.equal("result write value",
                                    model.dut.obs_write_data,
                                    writes[write_cursor + 1]);
                        write_cursor += 2;
                        ++case_writes_seen;
                    }
                }
                if (model.dut.rst_n &&
                    model.dut.multicast_remote_write_valid &&
                    model.dut.multicast_remote_write_ready) {
                    const std::uint32_t participant =
                        model.dut.multicast_remote_write_participant;
                    const std::uint64_t offset =
                        model.dut.multicast_remote_write_offset;
                    const std::uint32_t word =
                        static_cast<std::uint32_t>((offset & 0xffffU) >> 2);
                    check.equal(
                        "multicast write address/data",
                        model.dut.multicast_remote_write_object_id == 366 &&
                            (offset & 3U) == 0 &&
                            offset < 16777216ULL && participant < 256 &&
                            participant == ((offset >> 16) & 0xffU) &&
                            model.dut.multicast_remote_write_data ==
                                payload_word(word),
                        1);
                    if (participant < kMulticastParticipants) {
                        check.equal("multicast ascending participant word",
                                    word,
                                    next_multicast_word[participant]);
                        ++next_multicast_word[participant];
                        ++participant_writes[participant];
                        if (participant != 0)
                            check.equal(
                                "multicast binomial-tree source",
                                model.dut.multicast_tree_source,
                                expected_tree_source(participant));
                    }
                    ++observed_multicast_writes;
                }
                if (!model.dut.rst_n || !model.dut.response_valid) return;
                if (response_seen >= response_expected) {
                    ++check.failures;
                    std::cerr << "FAIL: response overflow in case "
                              << case_index << "\n";
                } else {
                    const auto offset =
                        (response_base + response_seen) * kIssueStride;
                    check.equal(
                        "response opcode",
                        (static_cast<std::uint32_t>(model.dut.response_family)
                         << 8) |
                            model.dut.response_sub,
                        issues[offset]);
                    check.equal("response descriptor",
                                model.dut.response_descriptor_id,
                                issues[offset + 1]);
                    check.equal("response PC", model.dut.response_index,
                                issues[offset + 2]);
                    check.equal("response trap",
                                model.dut.response_trap_class,
                                issues[offset + 3]);
                    check.equal("response fault bit", model.dut.response_fault,
                                issues[offset + 3] != 0);
                }
                ++response_seen;
                ++total_responses;
            };

            model.dut.start = 1;
            model.cycle(observe);
            model.dut.start = 0;
            // 64-bit.  The old guard was a std::uint32_t bounded at
            // 150,000,000; one full-dimension layer is about 1e9 cycles and
            // the LM head about 3e9, so the guard tripped before the work
            // did.  It still trips -- it is a watchdog, not a formality --
            // and the bound it tripped at is reported.
            std::uint64_t guard = 0;
            const auto sim_start = std::chrono::steady_clock::now();
            while (!model.dut.done && guard < cycle_guard_limit) {
                model.cycle(observe);
                ++guard;
            }
            sim_seconds += std::chrono::duration<double>(
                               std::chrono::steady_clock::now() - sim_start)
                               .count();
            total_cycles += guard;
            if (!model.dut.done) {
                ++check.failures;
                std::cerr << "FAIL: case " << case_index
                          << " timed out after " << guard << " cycles\n";
            }
            if (!pending_views.empty()) {
                ++check.failures;
                std::cerr << "FAIL: case " << case_index << " left "
                          << pending_views.size()
                          << " resolved views attached to no issue\n";
                pending_views.clear();
            }
            if (injecting) {
                // No engine was issued to.  This is the evidence that the
                // control plane, not the datapath, is what ran.
                check.equal("no engine launch under injection",
                            model.dut.real_launch_count, 0);
                check.equal("no engine work under injection",
                            model.dut.engine_work_count, 0);
                check.equal("injected completions",
                            model.dut.inj_completion_count, response_seen);
                check.equal("predicate reads refused",
                            model.dut.predicate_read_refused_count, 0);
            }

            // Engine-side observables. Under G1e injection no engine is
            // issued to at all, so every one of them must read zero; the
            // CONTROL counters below are compared against the very same
            // expectations as the real-engine run, which is what makes
            // "the control path was not stubbed" a measurement.
            auto engine_expect = [&](std::uint64_t value) -> std::uint64_t {
                return injecting ? 0 : value;
            };
            check.equal("response count", response_seen, response_expected);
            check.equal("busy at completion", model.dut.busy, 0);
            check.equal("complete must remain false", model.dut.complete, 0);
            check.equal("transaction trapped", model.dut.trapped, 1);
            check.equal("trap class", model.dut.trap_class, 4);
            check.equal("first fault PC", model.dut.first_fault_instruction,
                        record[16]);
            check.equal("fetched", model.dut.count_fetched, record[19]);
            check.equal("retired", model.dut.count_retired, record[20]);
            check.equal("issued", model.dut.count_issued, record[21]);
            check.equal("loop iterations", model.dut.count_loop_iterations,
                        record[22]);
            check.equal("signals", model.dut.count_signals, record[23]);
            check.equal("views resolved", model.dut.count_views_resolved,
                        record[24]);
            check.equal("predicated off", model.dut.count_predicated_off, 0);
            check.equal("branches", model.dut.count_branches, 0);
            check.equal("wait events", model.dut.count_wait_events,
                        record[35]);
            check.equal("real engine launches", model.dut.real_launch_count,
                        engine_expect(record[14]));
            check.equal("DMA gather launches",
                        model.dut.dma_gather_launch_count,
                        engine_expect(record[33]));
            check.equal("embedding launches",
                        model.dut.embedding_launch_count,
                        engine_expect(record[34]));
            check.equal("RMSNorm launches", model.dut.rms_norm_launch_count,
                        engine_expect(record[42]));
            check.equal("head RMSNorm launches",
                        model.dut.head_rms_norm_launch_count,
                        engine_expect(record[49]));
            check.equal("RoPE launches", model.dut.rope_launch_count,
                        engine_expect(record[54]));
            check.equal("DMA transfer launches",
                        model.dut.dma_transfer_launch_count,
                        engine_expect(record[43]));
            check.equal("MATMUL launches", model.dut.matmul_launch_count,
                        engine_expect(record[46]));
            if (multicast_overlay) {
                check.equal("multicast launches",
                            model.dut.multicast_launch_count, record[56]);
                check.equal("multicast faults",
                            model.dut.multicast_fault_count, 0);
            }
            check.equal("capability responses",
                        model.dut.capability_fault_count,
                        engine_expect(record[29]));
            check.equal("descriptor faults", model.dut.descriptor_fault_count,
                        0);
            check.equal("engine faults", model.dut.engine_fault_count, 0);
            check.equal("last response PC", model.dut.last_response_index,
                        record[16]);
            check.equal(
                "last response opcode",
                (static_cast<std::uint32_t>(model.dut.last_response_family)
                 << 8) |
                    model.dut.last_response_sub,
                record[17]);
            check.equal("last response descriptor",
                        model.dut.last_response_descriptor_id, record[18]);
            check.equal("engine error", model.dut.engine_error_code, 0);
            check.equal("last engine result count",
                        model.dut.engine_result_count,
                        engine_expect(record[50]));
            check.equal("last engine work count", model.dut.engine_work_count,
                        engine_expect(record[51]));
            check.equal("result write count", model.dut.output_write_count,
                        record[15]);
            check.equal("writes after capability fault",
                        model.dut.writes_after_fault, 0);
            check.equal("operand read in bounds", model.dut.operand_read_oob,
                        0);
            check.equal("result write in bounds", model.dut.result_write_oob,
                        0);
            check.equal("event scoreboard error",
                        model.dut.event_signal_error, 0);
            check.equal("state apply overflow", model.dut.state_apply_overflow,
                        0);
            check.equal("state prepares", model.dut.count_state_prepares, 0);
            check.equal("state commits", model.dut.count_state_commits, 0);
            check.equal("state discards", model.dut.count_state_discards, 0);
            check.equal("state reads", model.dut.count_state_reads, 0);
            check.equal("state generation advances",
                        model.dut.count_state_generation_advances, 0);
            check.equal("state commits applied",
                        model.dut.count_state_commits_applied, 0);
            check.equal("state rows committed",
                        model.dut.count_state_rows_committed, 0);
            check.equal("state bytes written",
                        model.dut.count_state_bytes_written, 0);
            if (multicast_overlay) {
                check.equal("multicast protocol error",
                            model.dut.multicast_protocol_error, 0);
                check.equal("multicast writes after completion",
                            model.dut.multicast_writes_after_completion, 0);
            }

            if (multicast_overlay && record[56] != 0) {
                check.equal("multicast source reads",
                            model.dut.multicast_source_read_count,
                            kMulticastWords);
                check.equal("multicast source stalls exercised",
                            model.dut.multicast_source_stall_cycles != 0, 1);
                check.equal("multicast destination stalls exercised",
                            model.dut.multicast_destination_stall_cycles != 0,
                            1);
                check.equal("multicast messages sent",
                            model.dut.multicast_messages_sent, 255);
                check.equal("multicast messages received",
                            model.dut.multicast_messages_received, 255);
                check.equal("multicast bytes sent",
                            model.dut.multicast_bytes_sent, 16711680);
                check.equal("multicast bytes received",
                            model.dut.multicast_bytes_received, 16711680);
                check.equal("multicast payload flits",
                            model.dut.multicast_payload_flits, 4177920);
                check.equal("multicast adapter writes",
                            model.dut.multicast_remote_write_count,
                            kMulticastWrites);
                check.equal("multicast observed writes",
                            observed_multicast_writes, kMulticastWrites);
                check.equal("multicast CRC errors",
                            model.dut.multicast_crc_errors, 1);
                check.equal("multicast retry exercised",
                            model.dut.multicast_retry_events != 0, 1);
                check.equal("multicast replay exercised",
                            model.dut.multicast_replayed_flits != 0, 1);
                check.equal("multicast sequence errors",
                            model.dut.multicast_sequence_errors, 4);
                check.equal(
                    "multicast wire delivery relation",
                    model.dut.multicast_wire_flits,
                    static_cast<std::uint64_t>(
                        model.dut.multicast_payload_flits) +
                        model.dut.multicast_crc_errors +
                        model.dut.multicast_sequence_errors);
                for (std::size_t participant = 0;
                     participant < kMulticastParticipants; ++participant)
                    check.equal("multicast participant writes",
                                participant_writes[participant],
                                kMulticastWords);
            } else if (multicast_overlay) {
                check.equal("no multicast source reads",
                            model.dut.multicast_source_read_count, 0);
                check.equal("no multicast destination writes",
                            observed_multicast_writes, 0);
                check.equal("no multicast adapter writes",
                            model.dut.multicast_remote_write_count, 0);
                check.equal("no multicast CRC activity",
                            model.dut.multicast_crc_errors, 0);
            }

            // Every word this case wrote was compared as it was written,
            // address and value both, against the golden write stream.  What
            // is left to check about the RETAINED image is that the case
            // wrote the number of words the vector set declares and that the
            // region it allocated holds what survives -- which is a smaller
            // span than the write count exactly where the program rewrites a
            // buffer.
            if (!injecting)
                check.equal("case write-stream words consumed",
                            case_writes_seen, record[15]);
            for (std::uint32_t word = 0; word < record[kPlaceSpanWord];
                 ++word) {
                model.dut.result_read_addr = record[13] + word;
                model.dut.eval();
                check.equal("retained case result word",
                            model.dut.result_read_data,
                            expected[record[13] + word]);
            }
            total_launches += model.dut.real_launch_count;
            total_gathers += model.dut.dma_gather_launch_count;
            total_embeddings += model.dut.embedding_launch_count;
            total_rms_norms += model.dut.rms_norm_launch_count;
            total_head_rms_norms += model.dut.head_rms_norm_launch_count;
            total_ropes += model.dut.rope_launch_count;
            total_transfers += model.dut.dma_transfer_launch_count;
            total_matmuls += model.dut.matmul_launch_count;
            total_multicasts += model.dut.multicast_launch_count;
            total_words += model.dut.output_write_count;
            total_views += model.dut.count_views_resolved;

            // -- the six mapped families, observed one at a time ----------
            // The result words above were already compared against golden
            // for this case, so a launch counted here is a launch whose
            // output matched.  Each family is compared against the count the
            // vector set declares, so a family that ran when it should not
            // have is as much a failure as one that did not run.
            {
                const std::uint32_t observed[kMappedFamilyCount] = {
                    model.dut.vector_add_launch_count,
                    model.dut.vector_silu_mul_launch_count,
                    model.dut.dma_scatter_launch_count,
                    model.dut.attention_gqa_launch_count,
                    model.dut.selection_argmax_launch_count,
                    model.dut.selection_token_append_launch_count};
                for (unsigned family = 0; family < kMappedFamilyCount;
                     ++family) {
                    const std::uint64_t want =
                        (mapped_placement_vectors && !injecting)
                            ? record[kMapLaunchWord + family] : 0U;
                    check.equal(kMappedFamilyName[family], observed[family],
                                want);
                    mapped_launches[family] += observed[family];
                }
                const std::uint64_t want_token =
                    (mapped_placement_vectors && !injecting)
                        ? record[kMapTokenWord] : 0U;
                const std::uint64_t want_tie =
                    (mapped_placement_vectors && !injecting)
                        ? record[kMapTieWord] : 0U;
                const std::uint64_t want_eos =
                    (mapped_placement_vectors && !injecting)
                        ? record[kMapEosWord] : 0U;
                check.equal("selected token", model.dut.selected_token,
                            want_token);
                check.equal("selected tie multiplicity",
                            model.dut.selected_tie_multiplicity, want_tie);
                check.equal("selected EOS reason",
                            model.dut.selected_eos_reason, want_eos);
                std::cout << "MAPPED " << case_index << " placement="
                          << static_cast<unsigned>(
                                 model.dut.cfg_extended_placement_valid)
                          << " add=" << observed[0]
                          << " silu=" << observed[1]
                          << " scatter=" << observed[2]
                          << " gqa=" << observed[3]
                          << " argmax=" << observed[4]
                          << " append=" << observed[5]
                          << " token=" << model.dut.selected_token
                          << " tie=" << model.dut.selected_tie_multiplicity
                          << " eos="
                          << static_cast<unsigned>(
                                 model.dut.selected_eos_reason)
                          << " capability_faults="
                          << model.dut.capability_fault_count << "\n";
            }
            std::cout << "CASE " << case_index << " OK launches="
                      << model.dut.real_launch_count << " words="
                      << model.dut.output_write_count << " responses="
                      << response_seen << " trap=" << model.dut.trap_class
                      << " fault=" << model.dut.first_fault_instruction
                      << " fetched=" << model.dut.count_fetched
                      << " retired=" << model.dut.count_retired
                      << " issued=" << model.dut.count_issued << " views="
                      << model.dut.count_views_resolved;
            if (multicast_overlay)
                std::cout << " multicasts="
                          << model.dut.multicast_launch_count;
            std::cout << "\n";
            model.cycle(observe);
        }

        check.equal("total responses", total_responses, meta[0] + meta[1]);
        check.equal("total launches", total_launches,
                    injecting ? 0 : meta[1]);
        check.equal("total DMA gathers", total_gathers,
                    injecting ? 0 : meta[8]);
        check.equal("total embedding launches", total_embeddings,
                    injecting ? 0 : meta[9]);
        check.equal("total RMSNorm launches", total_rms_norms,
                    injecting ? 0 : meta[12]);
        check.equal("total head RMSNorm launches", total_head_rms_norms,
                    injecting ? 0 : meta[20]);
        check.equal("total RoPE launches", total_ropes,
                    injecting ? 0 : meta[24]);
        check.equal("total transfer launches", total_transfers,
                    injecting ? 0 : meta[13]);
        check.equal("total MATMUL launches", total_matmuls,
                    injecting ? 0 : meta[16]);
        if (multicast_overlay)
            check.equal("total multicast launches", total_multicasts, 1);
        check.equal("total result words", total_words, meta[2]);
        if (!injecting)
            check.equal("golden write stream fully consumed",
                        write_cursor, writes.size());
        check.equal("total resolved views", total_views, meta[3]);
        // meta[26], not meta[2]: the image spans what the placement
        // ALLOCATED, and the write count is larger by the words a rewritten
        // buffer gave up.
        for (std::uint32_t word = 0; word < meta[26]; ++word) {
            model.dut.result_read_addr = word;
            model.dut.eval();
            check.equal("final retained result", model.dut.result_read_data,
                        expected[word]);
        }
        for (std::uint32_t word = meta[26]; word < g_geometry.result_words;
             ++word) {
            model.dut.result_read_addr = word;
            model.dut.eval();
            check.equal("unwritten result tail", model.dut.result_read_data,
                        kUnwritten);
        }

        // -- rung G1e: the issue trace, element for element ---------------
        if (trace_out_path != nullptr) trace::write(rtl_trace, trace_out_path);
        trace::Comparison comparison;
        std::string uncompared;
        if (golden_trace_path != nullptr) {
            const auto golden = trace::read(golden_trace_path);
            comparison = trace::compare(rtl_trace, golden);
            check.equal("issue trace equals golden", comparison.equal ? 1 : 0,
                        1);
            if (!comparison.equal) {
                std::cerr << "FAIL: issue trace diverges at element "
                          << comparison.divergence_index << " ("
                          << comparison.label << ") got=" << comparison.got
                          << " want=" << comparison.want << "\n";
            }
            check.equal("issue trace compared elements", comparison.compared,
                        golden.elements());
            check.equal("issue trace issue count", rtl_trace.issues.size(),
                        golden.issues.size());
            // A field the golden does not carry was NOT compared.  Say so in
            // the run's own output rather than letting a partial trace read
            // as a complete one.
            for (const auto& name : comparison.uncompared_issue_fields)
                uncompared += (uncompared.empty() ? "" : ",") + ("issue." + name);
            for (const auto& name : comparison.uncompared_view_fields)
                uncompared += (uncompared.empty() ? "" : ",") + ("view." + name);
            if (!uncompared.empty())
                std::cerr << "NOTE: golden trace carries no "
                          << uncompared
                          << "; those elements were NOT compared\n";
        }
        if (injecting)
            check.equal("golden result stream fully consumed", injected_at,
                        injected.size());

        // -- what the run cost, measured, not estimated -------------------
        const auto wall_end = std::chrono::steady_clock::now();
        const double wall_seconds =
            std::chrono::duration<double>(wall_end - wall_start).count();
        const auto& window_stats = weightwindow::window().stats();
        const std::uint64_t distinct_bytes =
            window_stats.distinct_pages * weightwindow::window().page_bytes();
        // -- rung G1a, the integrated half: which of the six the vehicle
        // -- that runs the real compiled program actually reached.
        // A family is reached only if this top launched it; the source of
        // the number is this run, never another vehicle's campaign and never
        // the presence of a port connection.  Absence of a launch is a trap,
        // which is a FAIL, not a "not evaluable".
        {
            unsigned reached = 0;
            std::cout << "ADMISSION vectors="
                      << (mapped_placement_vectors ? "mapped" : "legacy")
                      << " cases_with_placement=" << mapped_cases_with_placement
                      << " injecting=" << (injecting ? 1 : 0);
            for (unsigned family = 0; family < kMappedFamilyCount; ++family) {
                if (mapped_launches[family] != 0) ++reached;
                std::cout << " " << kMappedFamilyName[family] << "="
                          << mapped_launches[family];
            }
            std::cout << " reached=" << reached << " trapped="
                      << (kMappedFamilyCount - reached) << "\n";
        }
        std::cout << "MEASURE"
                  << " cycles=" << total_cycles
                  << " wall_s=" << std::fixed << std::setprecision(3)
                  << wall_seconds << std::defaultfloat
                  << " sim_wall_s=" << std::fixed
                  << std::setprecision(3) << sim_seconds << std::defaultfloat
                  << " cycle_guard=" << cycle_guard_limit
                  << " result_words=" << g_geometry.result_words
                  << " source_words=" << g_geometry.source_words
                  << " weight_image_bytes=" << g_geometry.matmul_weight_bytes
                  << " window_page_bytes="
                  << weightwindow::window().page_bytes()
                  << " window_cap_bytes="
                  << weightwindow::window().resident_cap_bytes()
                  << " window_peak_resident_bytes="
                  << window_stats.peak_resident_bytes
                  << " window_segments="
                  << weightwindow::window().segment_count()
                  << " halfword_reads=" << window_stats.halfword_reads
                  << " page_hits=" << window_stats.page_hits
                  << " page_faults=" << window_stats.page_faults
                  << " pages_evicted=" << window_stats.pages_evicted
                  << " distinct_bytes=" << distinct_bytes
                  << " refilled_bytes=" << window_stats.bytes_faulted
                  << " trace_last_case_issues=" << model.dut.trace_issue_count
                  << " trace_issues=" << rtl_trace.issues.size()
                  << " injected_results=" << injected_at
                  << " trace_compared_elements=" << comparison.compared
                  << " trace_divergence_index=" << comparison.divergence_index
                  << " trace_uncompared_fields="
                  << (uncompared.empty() ? "none" : uncompared) << "\n";

        model.dut.final();
        if (check.failures != 0) {
            std::cerr << "FAILURES: " << check.failures
                      << " checks=" << check.checks << "\n";
            return 1;
        }
        if (injecting)
            // A different claim, and it says so: the control plane ran, the
            // engines did not, and the issue trace equalled golden's.
            std::cout
                << "PASS: ABI3 shipped-prefix G1e control-plane injection "
                   "cases=4 engine_launches=0 words=91136 injected_results="
                << injected_at << " trace_issues=" << rtl_trace.issues.size()
                << " checks=" << check.checks << "\n";
        else if (multicast_overlay)
            std::cout
                << "PASS: ABI3 shipped-prefix multicast integration cases=4 "
                   "launches=29 words=91136 capability_faults=4 multicasts=1 "
                   "checks="
                << check.checks << "\n";
        else
            std::cout
                << "PASS: ABI3 shipped-prefix engine integration cases=4 "
                   "launches=28 words=91136 capability_faults=4 checks="
                << check.checks << "\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "FAIL: " << exc.what() << "\n";
        return 2;
    }
}
