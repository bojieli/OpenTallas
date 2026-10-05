#include "Vot_ta_dma_head_rmsnorm_sequencer.h"
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

constexpr uint32_t kCommands = 4U;
constexpr uint32_t kWidth = 128U;
constexpr uint32_t kQRows = 32U;
constexpr uint32_t kKRows = 8U;
constexpr uint32_t kQElements = kQRows * kWidth;
constexpr uint32_t kKElements = kKRows * kWidth;
constexpr uint32_t kElements = kQElements + kKElements;
constexpr uint32_t kRows = kQRows + kKRows;
constexpr uint32_t kHbmRequests = 8U;
constexpr uint32_t kDmaWrites = 32U;
constexpr uint32_t kSramReads = kElements * 2U;
constexpr uint32_t kSramWrites = kDmaWrites + kElements;
constexpr uint64_t kQInputBase = 6291456ULL;
constexpr uint64_t kKInputBase = 7340032ULL;
constexpr uint64_t kQWeightHbm = 1295024128ULL;
constexpr uint64_t kKWeightHbm = 1295024384ULL;
constexpr uint64_t kQWeightSram = 9437184ULL;
constexpr uint64_t kKWeightSram = 10485760ULL;
constexpr uint64_t kQOutputBase = 11534336ULL;
constexpr uint64_t kKOutputBase = 12591104ULL;
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

std::vector<uint32_t> load_codes32(const char* path, size_t count) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint32_t> result;
    uint64_t value = 0;
    while (stream >> std::hex >> value) {
        require(value <= 0xffffffffULL, std::string("wide code in ") + path);
        result.push_back(static_cast<uint32_t>(value));
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

void eval_low(Vot_ta_dma_head_rmsnorm_sequencer& dut) {
    dut.clk = 0;
    dut.eval();
}

struct Model {
    const std::vector<uint16_t>& q_inputs;
    const std::vector<uint16_t>& k_inputs;
    const std::vector<uint16_t>& q_weights;
    const std::vector<uint16_t>& k_weights;
    const std::vector<uint16_t>& q_expected;
    const std::vector<uint16_t>& k_expected;
    std::vector<uint16_t> q_staged;
    std::vector<uint16_t> k_staged;

    bool pending_hbm = false;
    bool stall_next_hbm_request = true;
    uint32_t pending_hbm_delay = 0;
    std::array<uint32_t, 16> pending_hbm_data{};
    bool hbm_response_valid = false;
    std::array<uint32_t, 16> hbm_response_data{};
    bool pending_read = false;
    uint32_t pending_read_delay = 0;
    uint16_t pending_read_data = 0;
    bool sram_response_valid = false;
    uint16_t sram_response_data = 0;

    uint64_t cycles = 0;
    uint32_t hbm_requests = 0;
    uint32_t hbm_responses = 0;
    uint32_t dma_writes = 0;
    uint32_t q_input_reads = 0;
    uint32_t k_input_reads = 0;
    uint32_t q_weight_reads = 0;
    uint32_t k_weight_reads = 0;
    uint32_t read_responses = 0;
    uint32_t q_writes = 0;
    uint32_t k_writes = 0;
    uint32_t request_stalls = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;

    Model(const std::vector<uint16_t>& q_input_value,
          const std::vector<uint16_t>& k_input_value,
          const std::vector<uint16_t>& q_weight_value,
          const std::vector<uint16_t>& k_weight_value,
          const std::vector<uint16_t>& q_output_value,
          const std::vector<uint16_t>& k_output_value)
        : q_inputs(q_input_value),
          k_inputs(k_input_value),
          q_weights(q_weight_value),
          k_weights(k_weight_value),
          q_expected(q_output_value),
          k_expected(k_output_value),
          q_staged(kWidth),
          k_staged(kWidth) {}

    void reset() {
        std::fill(q_staged.begin(), q_staged.end(), 0);
        std::fill(k_staged.begin(), k_staged.end(), 0);
        pending_hbm = false;
        stall_next_hbm_request = true;
        pending_hbm_delay = 0;
        pending_hbm_data.fill(0);
        hbm_response_valid = false;
        hbm_response_data.fill(0);
        pending_read = false;
        pending_read_delay = 0;
        pending_read_data = 0;
        sram_response_valid = false;
        sram_response_data = 0;
        cycles = 0;
        hbm_requests = hbm_responses = dma_writes = 0;
        q_input_reads = k_input_reads = 0;
        q_weight_reads = k_weight_reads = read_responses = 0;
        q_writes = k_writes = 0;
        request_stalls = read_stalls = write_stalls = 0;
    }

    void drive(Vot_ta_dma_head_rmsnorm_sequencer& dut) const {
        dut.hbm_request_ready = !pending_hbm && !hbm_response_valid &&
                                !stall_next_hbm_request;
        dut.sram_read_ready = !pending_read && !sram_response_valid &&
                              (cycles % 5U) != 1U;
        dut.sram_write_ready = (cycles % 11U) != 3U;
        dut.hbm_response_valid = hbm_response_valid;
        dut.hbm_response_error = 0;
        for (unsigned word = 0; word < hbm_response_data.size(); ++word)
            dut.hbm_response_data[word] = hbm_response_data[word];
        dut.sram_response_valid = sram_response_valid;
        dut.sram_response_data = sram_response_data;
    }

    void raw_reset_tick(Vot_ta_dma_head_rmsnorm_sequencer& dut) {
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
        if (address >= kQInputBase && address < kQInputBase + kQElements * 2ULL) {
            const auto index = static_cast<uint32_t>((address - kQInputBase) >> 1U);
            require(index == q_input_reads, "Q input read order differs");
            ++q_input_reads;
            return q_inputs[index];
        }
        if (address >= kKInputBase && address < kKInputBase + kKElements * 2ULL) {
            const auto index = static_cast<uint32_t>((address - kKInputBase) >> 1U);
            require(index == k_input_reads, "K input read order differs");
            ++k_input_reads;
            return k_inputs[index];
        }
        if (address >= kQWeightSram && address < kQWeightSram + kWidth * 2ULL) {
            const auto index = static_cast<uint32_t>((address - kQWeightSram) >> 1U);
            require(index == q_weight_reads % kWidth,
                    "Q weight read order differs");
            ++q_weight_reads;
            return q_staged[index];
        }
        if (address >= kKWeightSram && address < kKWeightSram + kWidth * 2ULL) {
            const auto index = static_cast<uint32_t>((address - kKWeightSram) >> 1U);
            require(index == k_weight_reads % kWidth,
                    "K weight read order differs");
            ++k_weight_reads;
            return k_staged[index];
        }
        fail("SRAM read outside head RMSNorm regions");
    }

    void cycle(Vot_ta_dma_head_rmsnorm_sequencer& dut) {
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
            ++hbm_responses;
        }
        if (hbm_request_fire) {
            require(!pending_hbm && !hbm_response_valid,
                    "more than one HBM request outstanding");
            require(hbm_bytes == 64U, "HBM request byte count differs");
            const std::vector<uint16_t>* source = nullptr;
            uint32_t start = 0;
            if (hbm_address >= kQWeightHbm && hbm_address < kQWeightHbm + 256U) {
                source = &q_weights;
                start = static_cast<uint32_t>((hbm_address - kQWeightHbm) >> 1U);
            } else if (hbm_address >= kKWeightHbm &&
                       hbm_address < kKWeightHbm + 256U) {
                source = &k_weights;
                start = static_cast<uint32_t>((hbm_address - kKWeightHbm) >> 1U);
            } else {
                fail("HBM request outside head RMSNorm weights");
            }
            for (unsigned word = 0; word < 16; ++word) {
                const uint16_t low = (*source)[start + word * 2U];
                const uint16_t high = (*source)[start + word * 2U + 1U];
                pending_hbm_data[word] =
                    static_cast<uint32_t>(low) |
                    (static_cast<uint32_t>(high) << 16U);
            }
            pending_hbm = true;
            stall_next_hbm_request = true;
            pending_hbm_delay = (hbm_requests % 3U) + 1U;
            ++hbm_requests;
        }
        if (had_pending_hbm) {
            if (pending_hbm_delay == 0 && !hbm_response_valid) {
                hbm_response_data = pending_hbm_data;
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
                ((q_input_reads + k_input_reads + q_weight_reads +
                  k_weight_reads) % 4U) + 1U;
        }
        if (had_pending_read) {
            if (pending_read_delay == 0 && !sram_response_valid) {
                sram_response_data = pending_read_data;
                sram_response_valid = true;
                pending_read = false;
            } else {
                --pending_read_delay;
            }
        }

        if (write_fire) {
            if (write_enable == 0xffffU &&
                write_address >= kQWeightSram &&
                write_address < kQWeightSram + 256U) {
                const auto start = static_cast<uint32_t>(
                    (write_address - kQWeightSram) >> 1U);
                for (unsigned lane = 0; lane < 8; ++lane) {
                    require(lane16(write_words, lane) == q_weights[start + lane],
                            "Q DMA write data differs");
                    q_staged[start + lane] = lane16(write_words, lane);
                }
                ++dma_writes;
            } else if (write_enable == 0xffffU &&
                       write_address >= kKWeightSram &&
                       write_address < kKWeightSram + 256U) {
                const auto start = static_cast<uint32_t>(
                    (write_address - kKWeightSram) >> 1U);
                for (unsigned lane = 0; lane < 8; ++lane) {
                    require(lane16(write_words, lane) == k_weights[start + lane],
                            "K DMA write data differs");
                    k_staged[start + lane] = lane16(write_words, lane);
                }
                ++dma_writes;
            } else if (write_enable == 0x0003U &&
                       write_address >= kQOutputBase &&
                       write_address < kQOutputBase + kQElements * 2ULL) {
                const auto index = static_cast<uint32_t>(
                    (write_address - kQOutputBase) >> 1U);
                require(index == q_writes, "Q output write order differs");
                require(lane16(write_words, 0) == q_expected[index],
                        "Q output write data differs");
                ++q_writes;
            } else if (write_enable == 0x0003U &&
                       write_address >= kKOutputBase &&
                       write_address < kKOutputBase + kKElements * 2ULL) {
                const auto index = static_cast<uint32_t>(
                    (write_address - kKOutputBase) >> 1U);
                require(index == k_writes, "K output write order differs");
                require(lane16(write_words, 0) == k_expected[index],
                        "K output write data differs");
                ++k_writes;
            } else {
                fail("SRAM write outside head RMSNorm regions");
            }
        }
        ++cycles;
        require(cycles <= kTimeout, "campaign case timed out");
        dut.clk = 0;
        dut.eval();
    }
};

void set_record(Vot_ta_dma_head_rmsnorm_sequencer& dut,
                const Record& record) {
    for (unsigned word = 0; word < record.size(); ++word)
        dut.command_record[word] = record[word];
}

void reset_case(Vot_ta_dma_head_rmsnorm_sequencer& dut, Model& model) {
    model.reset();
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

void submit(Vot_ta_dma_head_rmsnorm_sequencer& dut, Model& model,
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
}

void await_done(Vot_ta_dma_head_rmsnorm_sequencer& dut, Model& model) {
    for (uint64_t wait = 0; !dut.program_done_valid; ++wait) {
        require(wait < kTimeout, "program completion timeout");
        model.cycle(dut);
    }
}

void acknowledge(Vot_ta_dma_head_rmsnorm_sequencer& dut, Model& model) {
    for (unsigned cycle = 0; cycle < 3; ++cycle) {
        require(dut.program_done_valid, "program completion was not stable");
        model.cycle(dut);
    }
    dut.program_done_ready = 1;
    model.cycle(dut);
    dut.program_done_ready = 0;
}

void prove_early_terminal(Vot_ta_dma_head_rmsnorm_sequencer& dut,
                          Model& model, const std::vector<Record>& records) {
    reset_case(dut, model);
    submit(dut, model, records[0], 3075U, true);
    await_done(dut, model);
    require(dut.program_done_error == 12U &&
                dut.program_done_failing_command_index == 3075U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                model.hbm_requests == 0U && model.dma_writes == 0U,
            "early-terminal fail-stop behavior differs");
    acknowledge(dut, model);
}

void prove_success(Vot_ta_dma_head_rmsnorm_sequencer& dut, Model& model,
                   const std::vector<Record>& records,
                   const std::vector<uint32_t>& k_mean,
                   const std::vector<uint32_t>& k_inverse) {
    reset_case(dut, model);
    for (uint32_t offset = 0; offset < kCommands; ++offset)
        submit(dut, model, records[offset], 3075U + offset,
               offset == kCommands - 1U);
    await_done(dut, model);
    require(dut.program_done_error == 0U &&
                dut.program_done_failing_command_index == 0xffffffffU &&
                dut.program_done_last_command_index == 3078U &&
                dut.program_done_commands_accepted == kCommands &&
                dut.program_done_commands_completed == kCommands &&
                dut.program_done_hbm_request_count == kHbmRequests &&
                dut.program_done_hbm_response_count == kHbmRequests &&
                dut.program_done_hbm_bytes_read == 512U &&
                dut.program_done_sram_read_count == kSramReads &&
                dut.program_done_sram_bytes_read == kSramReads * 2U &&
                dut.program_done_sram_write_count == kSramWrites &&
                dut.program_done_sram_bytes_written == 10752U &&
                dut.program_done_row_count == kRows &&
                dut.program_done_element_count == kElements &&
                dut.program_done_normalized_saturation_count == 0U &&
                dut.program_done_output_saturation_count == 0U &&
                dut.program_done_mean_square_code == k_mean.back() &&
                dut.program_done_inverse_rms_code == k_inverse.back() &&
                model.hbm_requests == kHbmRequests &&
                model.hbm_responses == kHbmRequests &&
                model.dma_writes == kDmaWrites &&
                model.q_input_reads == kQElements &&
                model.k_input_reads == kKElements &&
                model.q_weight_reads == kQElements &&
                model.k_weight_reads == kKElements &&
                model.read_responses == kSramReads &&
                model.q_writes == kQElements &&
                model.k_writes == kKElements &&
                model.request_stalls != 0U && model.read_stalls != 0U &&
                model.write_stalls != 0U && !model.pending_hbm &&
                !model.pending_read && !model.hbm_response_valid &&
                !model.sram_response_valid,
            "Q/K head RMSNorm accounting differs");
    require(model.q_staged == model.q_weights &&
                model.k_staged == model.k_weights,
            "staged head RMSNorm weights differ");
    acknowledge(dut, model);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const auto records = load_records("head_rmsnorm_commands.hex", kCommands);
    const auto q_inputs =
        load_codes16("head_rmsnorm_q_input.hex", kQElements);
    const auto k_inputs =
        load_codes16("head_rmsnorm_k_input.hex", kKElements);
    const auto q_weights =
        load_codes16("head_rmsnorm_q_weight.hex", kWidth);
    const auto k_weights =
        load_codes16("head_rmsnorm_k_weight.hex", kWidth);
    const auto q_outputs =
        load_codes16("head_rmsnorm_q_output.hex", kQElements);
    const auto k_outputs =
        load_codes16("head_rmsnorm_k_output.hex", kKElements);
    const auto k_mean = load_codes32("head_rmsnorm_k_mean.hex", kKRows);
    const auto k_inverse =
        load_codes32("head_rmsnorm_k_inverse.hex", kKRows);
    Vot_ta_dma_head_rmsnorm_sequencer dut;
    Model model(q_inputs, k_inputs, q_weights, k_weights, q_outputs, k_outputs);
    prove_early_terminal(dut, model, records);
    prove_success(dut, model, records, k_mean, k_inverse);
    dut.final();
    std::cout
        << "PASS: Qwen Q/K head RMSNorm RTL commands=4 rows=40 elements=5120 "
        << "reductions=5080 rsqrt=40 outputs=5120 faults=1 cycles="
        << model.cycles << " request_stalls=" << model.request_stalls
        << " read_stalls=" << model.read_stalls
        << " write_stalls=" << model.write_stalls << " vector_set="
        << "9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791"
        << "\n";
    return 0;
}
