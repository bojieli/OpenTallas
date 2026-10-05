#include "Vot_ta_dma_rope_sequencer.h"
#include "verilated.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kCommands = 2U;
constexpr uint32_t kHeadWidth = 128U;
constexpr uint32_t kQElements = 32U * kHeadWidth;
constexpr uint32_t kKElements = 8U * kHeadWidth;
constexpr uint32_t kElements = kQElements + kKElements;
constexpr uint32_t kCoefficientElements = 2U * kHeadWidth;
constexpr uint32_t kHbmRequests = 8U;
constexpr uint32_t kDmaWrites = 32U;
constexpr uint32_t kSramReads = 2U + kCoefficientElements + kElements;
constexpr uint32_t kSramWrites = kDmaWrites + kElements;
constexpr uint64_t kTableBase = 16384425984ULL;
constexpr uint64_t kRow7999Base = 16388521472ULL;
constexpr uint64_t kIndexBase = 4ULL;
constexpr uint64_t kCoefficientBase = 13631488ULL;
constexpr uint64_t kQInputBase = 11534336ULL;
constexpr uint64_t kKInputBase = 12591104ULL;
constexpr uint64_t kQOutputBase = 14680064ULL;
constexpr uint64_t kKOutputBase = 15728640ULL;
constexpr uint64_t kTimeout = 1000000ULL;

using Record = std::array<uint32_t, 16>;

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(1);
}

void require(bool condition, const std::string& message) {
    if (!condition) fail(message);
}

std::vector<uint16_t> load_codes16(const char* path, size_t count) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint16_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {
        require(value <= 0xffffU, std::string("wide code in ") + path);
        result.push_back(static_cast<uint16_t>(value));
    }
    require(result.size() == count, std::string(path) + " count differs");
    return result;
}

std::vector<Record> load_records(const char* path, size_t count) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<Record> result;
    std::string hex;
    while (stream >> hex) {
        require(hex.size() == 128U, "command record width differs");
        Record record{};
        for (unsigned word = 0; word < record.size(); ++word) {
            const size_t offset = hex.size() - (word + 1U) * 8U;
            record[word] = static_cast<uint32_t>(
                std::stoul(hex.substr(offset, 8U), nullptr, 16));
        }
        result.push_back(record);
    }
    require(result.size() == count, std::string(path) + " count differs");
    return result;
}

uint16_t lane16(const std::array<uint32_t, 4>& words, unsigned lane) {
    return static_cast<uint16_t>(
        words[lane / 2U] >> ((lane & 1U) * 16U));
}

void eval_low(Vot_ta_dma_rope_sequencer& dut) {
    dut.clk = 0;
    dut.eval();
}

struct Model {
    const std::vector<uint16_t>& q_inputs;
    const std::vector<uint16_t>& k_inputs;
    const std::vector<uint16_t>& coefficient0;
    const std::vector<uint16_t>& coefficient7999;
    const std::vector<uint16_t>& q_expected0;
    const std::vector<uint16_t>& k_expected0;
    const std::vector<uint16_t>& q_expected7999;
    const std::vector<uint16_t>& k_expected7999;
    std::vector<uint16_t> staged_coefficient;

    uint32_t position = 0;
    bool inject_hbm_error = false;
    bool pending_hbm = false;
    bool stall_next_hbm_request = true;
    uint32_t pending_hbm_delay = 0;
    bool pending_hbm_error = false;
    std::array<uint32_t, 16> pending_hbm_data{};
    bool hbm_response_valid = false;
    uint8_t hbm_response_error = 0;
    std::array<uint32_t, 16> hbm_response_data{};
    bool pending_read = false;
    uint32_t pending_read_delay = 0;
    uint16_t pending_read_data = 0;
    bool sram_response_valid = false;
    uint16_t sram_response_data = 0;

    uint64_t cycles = 0;
    uint32_t hbm_requests = 0;
    uint32_t hbm_responses = 0;
    uint32_t index_reads = 0;
    uint32_t coefficient_reads = 0;
    uint32_t q_reads = 0;
    uint32_t k_reads = 0;
    uint32_t read_responses = 0;
    uint32_t dma_writes = 0;
    uint32_t q_writes = 0;
    uint32_t k_writes = 0;
    uint32_t request_stalls = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;

    Model(const std::vector<uint16_t>& q_input_value,
          const std::vector<uint16_t>& k_input_value,
          const std::vector<uint16_t>& coefficient0_value,
          const std::vector<uint16_t>& coefficient7999_value,
          const std::vector<uint16_t>& q_output0_value,
          const std::vector<uint16_t>& k_output0_value,
          const std::vector<uint16_t>& q_output7999_value,
          const std::vector<uint16_t>& k_output7999_value)
        : q_inputs(q_input_value),
          k_inputs(k_input_value),
          coefficient0(coefficient0_value),
          coefficient7999(coefficient7999_value),
          q_expected0(q_output0_value),
          k_expected0(k_output0_value),
          q_expected7999(q_output7999_value),
          k_expected7999(k_output7999_value),
          staged_coefficient(kCoefficientElements, 0xdeadU) {}

    const std::vector<uint16_t>& selected_coefficient() const {
        require(position == 0U || position == 7999U,
                "no retained coefficient row for position");
        return position == 0U ? coefficient0 : coefficient7999;
    }

    const std::vector<uint16_t>& selected_q_expected() const {
        require(position == 0U || position == 7999U,
                "no retained Q output for position");
        return position == 0U ? q_expected0 : q_expected7999;
    }

    const std::vector<uint16_t>& selected_k_expected() const {
        require(position == 0U || position == 7999U,
                "no retained K output for position");
        return position == 0U ? k_expected0 : k_expected7999;
    }

    void reset(uint32_t position_value, bool inject_error) {
        position = position_value;
        inject_hbm_error = inject_error;
        std::fill(staged_coefficient.begin(), staged_coefficient.end(), 0xdeadU);
        pending_hbm = false;
        stall_next_hbm_request = true;
        pending_hbm_delay = 0;
        pending_hbm_error = false;
        pending_hbm_data.fill(0);
        hbm_response_valid = false;
        hbm_response_error = 0;
        hbm_response_data.fill(0);
        pending_read = false;
        pending_read_delay = 0;
        pending_read_data = 0;
        sram_response_valid = false;
        sram_response_data = 0;
        cycles = 0;
        hbm_requests = hbm_responses = 0;
        index_reads = coefficient_reads = q_reads = k_reads = 0;
        read_responses = 0;
        dma_writes = q_writes = k_writes = 0;
        request_stalls = read_stalls = write_stalls = 0;
    }

    void drive(Vot_ta_dma_rope_sequencer& dut) const {
        dut.hbm_request_ready = !pending_hbm && !hbm_response_valid &&
                                !stall_next_hbm_request;
        dut.sram_read_ready = !pending_read && !sram_response_valid &&
                              (cycles % 7U) != 4U;
        dut.sram_write_ready = (cycles % 13U) != 5U;
        dut.hbm_response_valid = hbm_response_valid;
        dut.hbm_response_error = hbm_response_error;
        for (unsigned word = 0; word < hbm_response_data.size(); ++word)
            dut.hbm_response_data[word] = hbm_response_data[word];
        dut.sram_response_valid = sram_response_valid;
        dut.sram_response_data = sram_response_data;
    }

    void raw_reset_tick(Vot_ta_dma_rope_sequencer& dut) {
        dut.hbm_request_ready = 0;
        dut.hbm_response_valid = 0;
        dut.hbm_response_error = 0;
        dut.sram_read_ready = 0;
        dut.sram_response_valid = 0;
        dut.sram_write_ready = 0;
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }

    uint16_t read_value(uint64_t address) {
        if (address == kIndexBase) {
            require(index_reads == 0U, "low index read order differs");
            ++index_reads;
            return static_cast<uint16_t>(position);
        }
        if (address == kIndexBase + 2U) {
            require(index_reads == 1U, "high index read order differs");
            ++index_reads;
            return static_cast<uint16_t>(position >> 16U);
        }
        if (address >= kCoefficientBase &&
            address < kCoefficientBase + kCoefficientElements * 2ULL) {
            const auto index = static_cast<uint32_t>(
                (address - kCoefficientBase) >> 1U);
            require(index == coefficient_reads,
                    "coefficient read order differs");
            ++coefficient_reads;
            return staged_coefficient[index];
        }
        if (address >= kQInputBase &&
            address < kQInputBase + kQElements * 2ULL) {
            const auto index = static_cast<uint32_t>(
                (address - kQInputBase) >> 1U);
            require(index == q_reads, "Q input read order differs");
            ++q_reads;
            return q_inputs[index];
        }
        if (address >= kKInputBase &&
            address < kKInputBase + kKElements * 2ULL) {
            const auto index = static_cast<uint32_t>(
                (address - kKInputBase) >> 1U);
            require(index == k_reads, "K input read order differs");
            ++k_reads;
            return k_inputs[index];
        }
        fail("SRAM read outside indexed RoPE regions");
    }

    void cycle(Vot_ta_dma_rope_sequencer& dut) {
        drive(dut);
        eval_low(dut);
        const bool request_stalled =
            dut.hbm_request_valid && !dut.hbm_request_ready;
        const bool read_stalled = dut.sram_read_valid && !dut.sram_read_ready;
        const bool write_stalled =
            dut.sram_write_valid && !dut.sram_write_ready;
        const bool hbm_request_fire =
            dut.hbm_request_valid && dut.hbm_request_ready;
        const bool hbm_response_fire =
            dut.hbm_response_valid && dut.hbm_response_ready;
        const bool read_fire = dut.sram_read_valid && dut.sram_read_ready;
        const bool read_response_fire =
            dut.sram_response_valid && dut.sram_response_ready;
        const bool write_fire = dut.sram_write_valid && dut.sram_write_ready;
        const uint64_t hbm_address = dut.hbm_request_address;
        const uint16_t hbm_bytes = dut.hbm_request_bytes;
        const uint64_t read_address = dut.sram_read_address;
        const uint64_t write_address = dut.sram_write_address;
        const uint16_t write_enable = dut.sram_write_byte_enable;
        std::array<uint32_t, 4> write_words{};
        for (unsigned word = 0; word < write_words.size(); ++word)
            write_words[word] = dut.sram_write_data[word];
        const bool had_pending_hbm = pending_hbm;
        const bool had_pending_read = pending_read;

        dut.clk = 1;
        dut.eval();
        request_stalls += request_stalled ? 1U : 0U;
        read_stalls += read_stalled ? 1U : 0U;
        write_stalls += write_stalled ? 1U : 0U;

        if (request_stalled && !pending_hbm && !hbm_response_valid)
            stall_next_hbm_request = false;

        if (hbm_response_fire) {
            require(hbm_response_valid, "HBM response fire without valid");
            hbm_response_valid = false;
            hbm_response_error = 0;
            ++hbm_responses;
        }
        if (hbm_request_fire) {
            require(!pending_hbm && !hbm_response_valid,
                    "more than one HBM request outstanding");
            require(hbm_bytes == 64U, "HBM request byte count differs");
            const uint64_t selected_base =
                position == 0U ? kTableBase : kRow7999Base;
            require(hbm_address >= selected_base &&
                        hbm_address < selected_base + 512U,
                    "HBM request outside selected coefficient row");
            const auto start = static_cast<uint32_t>(
                (hbm_address - selected_base) >> 1U);
            const auto& source = selected_coefficient();
            for (unsigned word = 0; word < 16; ++word) {
                const uint16_t low = source[start + word * 2U];
                const uint16_t high = source[start + word * 2U + 1U];
                pending_hbm_data[word] =
                    static_cast<uint32_t>(low) |
                    (static_cast<uint32_t>(high) << 16U);
            }
            pending_hbm_error = inject_hbm_error && hbm_requests == 3U;
            pending_hbm = true;
            stall_next_hbm_request = true;
            pending_hbm_delay = (hbm_requests % 4U) + 2U;
            ++hbm_requests;
        }
        if (had_pending_hbm) {
            if (pending_hbm_delay == 0U && !hbm_response_valid) {
                hbm_response_data = pending_hbm_data;
                hbm_response_error = pending_hbm_error ? 1U : 0U;
                hbm_response_valid = true;
                pending_hbm = false;
            } else {
                --pending_hbm_delay;
            }
        }

        if (read_response_fire) {
            require(sram_response_valid, "SRAM response fire without valid");
            sram_response_valid = false;
            ++read_responses;
        }
        if (read_fire) {
            require(!pending_read && !sram_response_valid,
                    "more than one SRAM read outstanding");
            pending_read_data = read_value(read_address);
            pending_read = true;
            pending_read_delay =
                ((index_reads + coefficient_reads + q_reads + k_reads) % 5U) +
                1U;
        }
        if (had_pending_read) {
            if (pending_read_delay == 0U && !sram_response_valid) {
                sram_response_data = pending_read_data;
                sram_response_valid = true;
                pending_read = false;
            } else {
                --pending_read_delay;
            }
        }

        if (write_fire) {
            if (write_enable == 0xffffU &&
                write_address >= kCoefficientBase &&
                write_address < kCoefficientBase + 512U) {
                const auto start = static_cast<uint32_t>(
                    (write_address - kCoefficientBase) >> 1U);
                require(start == dma_writes * 8U,
                        "coefficient DMA write order differs");
                const auto& expected = selected_coefficient();
                for (unsigned lane = 0; lane < 8; ++lane) {
                    require(lane16(write_words, lane) == expected[start + lane],
                            "coefficient DMA write data differs");
                    staged_coefficient[start + lane] = lane16(write_words, lane);
                }
                ++dma_writes;
            } else if (write_enable == 0x0003U &&
                       write_address >= kQOutputBase &&
                       write_address < kQOutputBase + kQElements * 2ULL) {
                const auto index = static_cast<uint32_t>(
                    (write_address - kQOutputBase) >> 1U);
                require(index == q_writes, "Q output write order differs");
                require(lane16(write_words, 0) == selected_q_expected()[index],
                        "Q output write data differs");
                ++q_writes;
            } else if (write_enable == 0x0003U &&
                       write_address >= kKOutputBase &&
                       write_address < kKOutputBase + kKElements * 2ULL) {
                const auto index = static_cast<uint32_t>(
                    (write_address - kKOutputBase) >> 1U);
                require(index == k_writes, "K output write order differs");
                require(lane16(write_words, 0) == selected_k_expected()[index],
                        "K output write data differs");
                ++k_writes;
            } else {
                fail("SRAM write outside indexed RoPE regions");
            }
        }
        ++cycles;
        require(cycles <= kTimeout, "campaign case timed out");
        dut.clk = 0;
        dut.eval();
    }
};

void set_record(Vot_ta_dma_rope_sequencer& dut, const Record& record) {
    for (unsigned word = 0; word < record.size(); ++word)
        dut.command_record[word] = record[word];
}

void reset_case(Vot_ta_dma_rope_sequencer& dut, Model& model,
                uint32_t position, bool inject_hbm_error) {
    model.reset(position, inject_hbm_error);
    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.cmd_last = 0;
    dut.program_done_ready = 0;
    dut.abi_major = 2;
    dut.abi_minor = 5;
    for (unsigned cycle = 0; cycle < 4; ++cycle) model.raw_reset_tick(dut);
    dut.rst_n = 1;
    model.drive(dut);
    eval_low(dut);
}

void submit(Vot_ta_dma_rope_sequencer& dut, Model& model,
            const Record& record, uint32_t expected_index, bool last) {
    for (uint64_t wait = 0; !dut.cmd_ready; ++wait) {
        require(wait < kTimeout, "command ready timeout");
        model.cycle(dut);
    }
    set_record(dut, record);
    dut.expected_command_index = expected_index;
    dut.cmd_last = last;
    dut.cmd_valid = 1;
    model.cycle(dut);
    dut.cmd_valid = 0;
    dut.cmd_last = 0;
}

void await_done(Vot_ta_dma_rope_sequencer& dut, Model& model) {
    for (uint64_t wait = 0; !dut.program_done_valid; ++wait) {
        require(wait < kTimeout, "program completion timeout");
        model.cycle(dut);
    }
}

void acknowledge(Vot_ta_dma_rope_sequencer& dut, Model& model) {
    for (unsigned cycle = 0; cycle < 3; ++cycle) {
        require(dut.program_done_valid, "program completion was not stable");
        model.cycle(dut);
    }
    dut.program_done_ready = 1;
    model.cycle(dut);
    dut.program_done_ready = 0;
}

void prove_early_terminal(Vot_ta_dma_rope_sequencer& dut, Model& model,
                          const std::vector<Record>& records) {
    reset_case(dut, model, 0U, false);
    submit(dut, model, records[0], 3079U, true);
    await_done(dut, model);
    require(dut.program_done_error == 12U &&
                dut.program_done_failing_command_index == 3079U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                model.index_reads == 0U && model.hbm_requests == 0U &&
                model.dma_writes == 0U,
            "early-terminal fail-stop behavior differs");
    acknowledge(dut, model);
}

void prove_range_fault(Vot_ta_dma_rope_sequencer& dut, Model& model,
                       const std::vector<Record>& records) {
    reset_case(dut, model, 8000U, false);
    submit(dut, model, records[0], 3079U, false);
    await_done(dut, model);
    require(dut.program_done_error == 9U &&
                dut.program_done_failing_command_index == 3079U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                dut.program_done_logical_index == 8000U &&
                dut.program_done_sram_read_count == 2U &&
                model.index_reads == 2U && model.hbm_requests == 0U &&
                model.dma_writes == 0U,
            "indexed-DMA range fail-stop behavior differs");
    acknowledge(dut, model);
}

void prove_hbm_fault(Vot_ta_dma_rope_sequencer& dut, Model& model,
                     const std::vector<Record>& records) {
    reset_case(dut, model, 7999U, true);
    submit(dut, model, records[0], 3079U, false);
    await_done(dut, model);
    require(dut.program_done_error == 11U &&
                dut.program_done_failing_command_index == 3079U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                dut.program_done_logical_index == 7999U &&
                dut.program_done_selected_hbm_address == kRow7999Base &&
                dut.program_done_hbm_request_count == 4U &&
                dut.program_done_hbm_response_count == 4U &&
                dut.program_done_hbm_bytes_read == 192U &&
                dut.program_done_sram_write_count == 0U &&
                model.index_reads == 2U && model.hbm_requests == 4U &&
                model.hbm_responses == 4U && model.dma_writes == 0U,
            "indexed-DMA HBM atomic fail-stop behavior differs");
    acknowledge(dut, model);
}

void prove_success(Vot_ta_dma_rope_sequencer& dut, Model& model,
                   const std::vector<Record>& records, uint32_t position) {
    reset_case(dut, model, position, false);
    submit(dut, model, records[0], 3079U, false);
    submit(dut, model, records[1], 3080U, true);
    await_done(dut, model);
    require(dut.program_done_error == 0U &&
                dut.program_done_failing_command_index == 0xffffffffU &&
                dut.program_done_last_command_index == 3080U &&
                dut.program_done_commands_accepted == kCommands &&
                dut.program_done_commands_completed == kCommands &&
                dut.program_done_logical_index == position &&
                dut.program_done_selected_hbm_address ==
                    kTableBase + static_cast<uint64_t>(position) * 512ULL &&
                dut.program_done_hbm_request_count == kHbmRequests &&
                dut.program_done_hbm_response_count == kHbmRequests &&
                dut.program_done_hbm_bytes_read == 512U &&
                dut.program_done_sram_read_count == kSramReads &&
                dut.program_done_sram_bytes_read == kSramReads * 2U &&
                dut.program_done_sram_write_count == kSramWrites &&
                dut.program_done_sram_bytes_written == 10752U &&
                dut.program_done_element_count == kElements &&
                dut.program_done_multiplication_count == 2U * kElements &&
                dut.program_done_addition_count == kElements &&
                dut.program_done_multiplication_saturation_count == 0U &&
                dut.program_done_addition_saturation_count == 0U &&
                model.hbm_requests == kHbmRequests &&
                model.hbm_responses == kHbmRequests &&
                model.index_reads == 2U &&
                model.coefficient_reads == kCoefficientElements &&
                model.q_reads == kQElements && model.k_reads == kKElements &&
                model.read_responses == kSramReads &&
                model.dma_writes == kDmaWrites &&
                model.q_writes == kQElements && model.k_writes == kKElements &&
                model.request_stalls != 0U && model.read_stalls != 0U &&
                model.write_stalls != 0U && !model.pending_hbm &&
                !model.pending_read && !model.hbm_response_valid &&
                !model.sram_response_valid,
            "indexed RoPE accounting differs");
    require(model.staged_coefficient == model.selected_coefficient(),
            "staged RoPE coefficient row differs");
    acknowledge(dut, model);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const auto records = load_records("rope_commands.hex", kCommands);
    const auto q_inputs = load_codes16("rope_q_input.hex", kQElements);
    const auto k_inputs = load_codes16("rope_k_input.hex", kKElements);
    const auto coefficient0 =
        load_codes16("rope_coefficient_0.hex", kCoefficientElements);
    const auto coefficient7999 =
        load_codes16("rope_coefficient_7999.hex", kCoefficientElements);
    const auto q_output0 =
        load_codes16("rope_q_output_0.hex", kQElements);
    const auto k_output0 =
        load_codes16("rope_k_output_0.hex", kKElements);
    const auto q_output7999 =
        load_codes16("rope_q_output_7999.hex", kQElements);
    const auto k_output7999 =
        load_codes16("rope_k_output_7999.hex", kKElements);
    Vot_ta_dma_rope_sequencer dut;
    Model model(q_inputs, k_inputs, coefficient0, coefficient7999, q_output0,
                k_output0, q_output7999, k_output7999);
    prove_early_terminal(dut, model, records);
    prove_range_fault(dut, model, records);
    prove_hbm_fault(dut, model, records);
    prove_success(dut, model, records, 0U);
    prove_success(dut, model, records, 7999U);
    dut.final();
    std::cout
        << "PASS: Qwen indexed RoPE RTL commands=2 positions=2 elements=10240 "
        << "multiplications=20480 additions=10240 outputs=10240 faults=3 cycles="
        << model.cycles << " request_stalls=" << model.request_stalls
        << " read_stalls=" << model.read_stalls
        << " write_stalls=" << model.write_stalls << " vector_set="
        << "3a792b0dec8dd7277540841409accca66521f2f05f977c1cd6b6d9e5361f4f76"
        << "\n";
    return 0;
}
