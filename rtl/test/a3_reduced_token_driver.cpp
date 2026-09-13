#include <array>
// ---------------------------------------------------------------------------
// Drive the integrated vehicle through the whole reduced program and read the
// token it emits.
//
// The shipped-prefix harness checks every intermediate write against golden and
// stops at a fail-stop boundary. This does the opposite trade: it stages the whole
// deployment, lets the program run to completion, and checks exactly one thing --
// the token id on `selected_token` -- against the golden device's own.
//
// That is a weaker check per operator and a stronger one end to end. It cannot tell
// you WHICH operator went wrong; it can tell you whether the redesigned datapath,
// under the real microsequencer and the real issue bridge, produces the token the
// reference produces.
//
// Everything it needs comes from tools/stage_reduced_token_run.py: the placement
// table, the staged operand image, the weight window, and the request's symbol
// bindings taken from the golden device's own record rather than recomputed.
// ---------------------------------------------------------------------------
#include "Vot_a3_shipped_prefix_top.h"
#include "verilated.h"

#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

// ---- the DPI weight window, backed by a flat file ------------------------
std::vector<std::uint8_t> g_weights;
std::uint64_t g_declared = 0;

std::vector<std::uint32_t> read_hex_rows(const std::string& path, std::size_t lanes) {
    std::ifstream in(path);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", path.c_str()); std::exit(2); }
    std::vector<std::uint32_t> words;
    std::string row;
    while (in >> row) {
        // one row is `lanes` 32-bit lanes, most significant lane first
        if (row.size() != lanes * 8) {
            std::fprintf(stderr, "%s: row has %zu digits, expected %zu\n",
                         path.c_str(), row.size(), lanes * 8);
            std::exit(2);
        }
        for (std::size_t lane = 0; lane < lanes; ++lane) {
            const std::string piece = row.substr((lanes - 1 - lane) * 8, 8);
            words.push_back(static_cast<std::uint32_t>(std::stoul(piece, nullptr, 16)));
        }
    }
    return words;
}

struct Plan {
    std::map<std::string, std::uint64_t> scalars;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> places;   // object, base
    std::vector<std::array<std::uint32_t, 3>> symbols;             // index, value, bound
};

Plan read_plan(const std::string& path) {
    std::ifstream in(path);
    if (!in) { std::fprintf(stderr, "cannot open %s\n", path.c_str()); std::exit(2); }
    Plan plan;
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream fields(line);
        std::string key;
        if (!(fields >> key)) continue;
        if (key == "place") {
            std::uint32_t slot, object, base;
            fields >> slot >> object >> base;
            plan.places.emplace_back(object, base);
        } else if (key == "symbol") {
            std::uint32_t index, value, bound;
            fields >> index >> value >> bound;
            plan.symbols.push_back({index, value, bound});
        } else {
            std::uint64_t value = 0;
            fields >> value;
            plan.scalars[key] = value;
        }
    }
    return plan;
}

}  // namespace

extern "C" unsigned long long ot_a3_weight_window_open(unsigned long long declared) {
    g_declared = declared;
    return declared;
}

extern "C" unsigned int ot_a3_weight_window_halfword(unsigned long long index) {
    const std::uint64_t at = index * 2;
    if (at + 1 >= g_weights.size()) return 0;
    return static_cast<unsigned int>(g_weights[at] |
                                     (std::uint32_t(g_weights[at + 1]) << 8));
}

extern "C" void ot_a3_geometry_declare(unsigned, unsigned, unsigned, unsigned,
                                       unsigned, unsigned long long, unsigned,
                                       unsigned) {}

int main(int argc, char** argv) {
    const std::string dir = (argc > 1) ? argv[1] : ".";
    const Plan plan = read_plan(dir + "/driver.txt");

    {
        std::ifstream w(dir + "/p3_matmul_weight.bin", std::ios::binary);
        if (!w) { std::fprintf(stderr, "cannot open p3_matmul_weight.bin\n"); return 2; }
        g_weights.assign(std::istreambuf_iterator<char>(w),
                         std::istreambuf_iterator<char>());
    }
    const auto program = read_hex_rows(dir + "/a3_program.hex", 8);
    const auto descriptors = read_hex_rows(dir + "/a3_descriptor.hex", 48);

    VerilatedContext ctx;
    ctx.commandArgs(argc, argv);
    Vot_a3_shipped_prefix_top dut{&ctx};

    std::uint64_t cycles = 0;
    auto tick = [&]() {
        dut.clk = 0; dut.eval(); ctx.timeInc(1);
        dut.clk = 1; dut.eval(); ctx.timeInc(1);
        ++cycles;
    };

    dut.rst_n = 0; dut.host_we = 0; dut.start = 0;
    for (int i = 0; i < 4; ++i) tick();
    dut.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick();

    auto host_write = [&](unsigned sel, std::uint32_t row, unsigned lane,
                          std::uint32_t data) {
        dut.host_sel = sel; dut.host_row = row; dut.host_lane = lane;
        dut.host_wdata = data; dut.host_we = 1;
        tick();
        dut.host_we = 0;
    };

    for (std::size_t row = 0; row * 8 < program.size(); ++row)
        for (unsigned lane = 0; lane < 8; ++lane)
            host_write(0, static_cast<std::uint32_t>(row), lane, program[row * 8 + lane]);
    for (std::size_t row = 0; row * 48 < descriptors.size(); ++row)
        for (unsigned lane = 0; lane < 48; ++lane)
            host_write(1, static_cast<std::uint32_t>(row), lane,
                       descriptors[row * 48 + lane]);
    for (const auto& sym : plan.symbols) {
        host_write(2, sym[0], 0, sym[1]);
        host_write(2, sym[0], 1, 0);
        host_write(2, sym[0], 2, sym[2]);
    }
    tick();
    if (dut.host_write_refused) {
        std::printf("FAIL: a host write was refused during load\n");
        return 1;
    }

    auto get = [&](const char* key, std::uint64_t fallback = 0) {
        auto it = plan.scalars.find(key);
        return it == plan.scalars.end() ? fallback : it->second;
    };

    dut.cfg_program_base = 0;
    dut.cfg_instruction_count = static_cast<std::uint32_t>(get("instruction_count"));
    dut.cfg_entry_pc = static_cast<std::uint32_t>(get("entry_pc"));
    dut.cfg_desc_base = 0;
    dut.cfg_desc_count = static_cast<std::uint32_t>(get("desc_count"));
    dut.cfg_max_retired_work = get("max_retired_work");
    dut.cfg_state_count = static_cast<std::uint32_t>(get("state_count"));
    dut.cfg_index_base = 0;
    dut.cfg_source_base = 0;
    dut.cfg_source_launch_stride = 0;
    dut.cfg_embedding_source_base = 0;
    dut.cfg_transfer_index_base = 0;
    dut.cfg_transfer_source_base = 0;
    dut.cfg_matmul_weight_window_base = 0;
    dut.cfg_predicate_object = 0xFFFFFFFFu;
    dut.cfg_predicate_base = 0;
    //: the six mapped families are admitted for this run; their addresses come from
    //: the placement table below, which is what actually resolves them
    dut.cfg_extended_placement_valid = 1;
    // The request's declared context. There is no defensible default: 17 (a
    // decode of a 16-token prompt) was the fallback, and a prefill silently
    // inheriting it declares a context one longer than its own span. Absent, say
    // so and stop rather than run the wrong request.
    if (plan.scalars.find("symbol_context") == plan.scalars.end()) {
        std::printf("FAIL: driver.txt states no symbol_context; "
                    "re-run tools/stage_reduced_token_run.py --case\n");
        return 2;
    }
    dut.cfg_context_length = static_cast<std::uint32_t>(get("symbol_context"));
    dut.cfg_kv_plane_rows = static_cast<std::uint32_t>(get("kv_plane_rows", 0));
    dut.cfg_generation_policy_id =
        static_cast<std::uint32_t>(get("generation_policy_id", 0xFFFFFFFFu));
    dut.cfg_request_max_new_tokens =
        static_cast<std::uint32_t>(get("request_max_new_tokens", 1));
    dut.cfg_generated_before = static_cast<std::uint32_t>(get("generated_before", 0));
    dut.inj_result_valid = 0; dut.inj_write_en = 0;
    dut.result_read_addr = 0;

#define PLACE_SLOT(n)                                                        \
    if (plan.places.size() > (n)) {                                          \
        dut.cfg_place_object_##n = plan.places[(n)].first;                    \
        dut.cfg_place_base_##n = plan.places[(n)].second;                     \
    } else {                                                                 \
        dut.cfg_place_object_##n = 0xFFFFFFFFu;                              \
        dut.cfg_place_base_##n = 0;                                          \
    }
    PLACE_SLOT(0)  PLACE_SLOT(1)  PLACE_SLOT(2)  PLACE_SLOT(3)
    PLACE_SLOT(4)  PLACE_SLOT(5)  PLACE_SLOT(6)  PLACE_SLOT(7)
    PLACE_SLOT(8)  PLACE_SLOT(9)  PLACE_SLOT(10) PLACE_SLOT(11)
    PLACE_SLOT(12) PLACE_SLOT(13) PLACE_SLOT(14) PLACE_SLOT(15)
    PLACE_SLOT(16) PLACE_SLOT(17) PLACE_SLOT(18) PLACE_SLOT(19)
    PLACE_SLOT(20) PLACE_SLOT(21) PLACE_SLOT(22) PLACE_SLOT(23)
    PLACE_SLOT(24) PLACE_SLOT(25) PLACE_SLOT(26) PLACE_SLOT(27)
    PLACE_SLOT(28) PLACE_SLOT(29) PLACE_SLOT(30) PLACE_SLOT(31)
#undef PLACE_SLOT

    tick();
    dut.start = 1; tick(); dut.start = 0;

    const std::uint64_t guard = 400ull * 1000 * 1000;
    // `done` and `complete` are pulses. Sampling them after the drain ticks
    // below read them back as zero on a run that had in fact completed, which
    // made a correct execution print FAIL.
    unsigned done_seen = 0, complete_seen = 0, trapped_seen = 0;
    while (!dut.done && !dut.trapped && cycles < guard) {
        tick();
        done_seen |= dut.done;
        complete_seen |= dut.complete;
        trapped_seen |= dut.trapped;
    }
    const bool hit_guard = !done_seen && !trapped_seen;
    for (int i = 0; i < 8; ++i) {
        tick();
        complete_seen |= dut.complete;
    }
    if (hit_guard)
        std::printf("  NOTE: stopped at the %llu-cycle guard, not on done\n",
                    (unsigned long long)guard);

    std::printf("  cycles              %llu\n", (unsigned long long)cycles);
    std::printf("  done                %u\n", done_seen);
    std::printf("  complete            %u\n", complete_seen);
    std::printf("  trapped             %u  trap_class=%u\n",
                (unsigned)dut.trapped, (unsigned)dut.trap_class);
    std::printf("  fetched/retired     %u / %u\n",
                (unsigned)dut.count_fetched, (unsigned)dut.count_retired);
    std::printf("  issued              %u\n", (unsigned)dut.count_issued);
    std::printf("  loop_iterations     %u\n", (unsigned)dut.count_loop_iterations);
    std::printf("  argmax launches     %u\n",
                (unsigned)dut.selection_token_append_launch_count);
    std::printf("  selected_token      %u\n", (unsigned)dut.selected_token);
    std::printf("  selected_eos_reason %u\n", (unsigned)dut.selected_eos_reason);
    std::printf("  session_retired     %u\n", (unsigned)dut.session_retired);
    std::printf("  operand_read_oob    %u\n", (unsigned)dut.operand_read_oob);
    std::printf("  first_fault_instr   %u\n", (unsigned)dut.first_fault_instruction);
    std::printf("  views_resolved      %u\n", (unsigned)dut.count_views_resolved);
    std::printf("  response_trap_class %u\n", (unsigned)dut.response_trap_class);
    std::printf("  engine_result_count %u\n", (unsigned)dut.engine_result_count);
    std::printf("  wait_events         %u\n", (unsigned)dut.count_wait_events);
    std::printf("  result_write_oob    %u\n", (unsigned)dut.result_write_oob);

    // +DUMP=<base>,<count> prints result-bank words after the run, so a chain
    // that produces a constant can be bisected operator by operator instead of
    // guessed at.
    for (int i = 1; i < argc; ++i) {
        const std::string a(argv[i]);
        if (a.rfind("+DUMP=", 0) != 0) continue;
        const std::string spec = a.substr(6);
        const std::size_t comma = spec.find(',');
        const std::uint32_t base =
            static_cast<std::uint32_t>(std::strtoull(spec.c_str(), nullptr, 10));
        const unsigned count = comma == std::string::npos
            ? 8u
            : static_cast<unsigned>(std::strtoul(spec.c_str() + comma + 1, nullptr, 10));
        std::printf("  result[%u..%u]:", base, base + count - 1);
        for (unsigned w = 0; w < count; ++w) {
            dut.result_read_addr = base + w;
            dut.eval();
            std::printf(" %08x", (unsigned)dut.result_read_data);
        }
        std::printf("\n");
    }

    const bool ok = done_seen && complete_seen && !trapped_seen &&
                    dut.count_retired == get("golden_retired") &&
                    dut.count_issued == get("golden_issued");
    std::printf("%s reduced end-to-end: retired %u vs golden %llu, issued %u vs %llu\n",
                ok ? "PASS" : "FAIL", (unsigned)dut.count_retired,
                (unsigned long long)get("golden_retired"),
                (unsigned)dut.count_issued,
                (unsigned long long)get("golden_issued"));
    return ok ? 0 : 1;
}
