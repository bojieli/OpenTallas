#include "Vot_ta_dma_matmul_sequencer.h"
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

constexpr uint32_t kTiles = 16U;
constexpr uint32_t kCommands = 32U;
constexpr uint32_t kInputsPerTile = 256U;
constexpr uint32_t kInputs = 4096U;
constexpr uint32_t kOutputs = 64U;
constexpr uint32_t kWeightsPerTile = 16384U;
constexpr uint32_t kWeights = 262144U;
constexpr uint32_t kDmaBytesPerTile = 32768U;
constexpr uint32_t kDmaBytes = 524288U;
constexpr uint32_t kDmaWritesPerTile = 2048U;
constexpr uint32_t kDmaWrites = 32768U;
constexpr uint32_t kAccumulatorReads = 1920U;
constexpr uint32_t kAccumulatorWrites = 1024U;
constexpr uint64_t kHbmBase = 1244692480ULL;
constexpr uint64_t kInputBase = 3145728ULL;
constexpr uint64_t kWeightBase = 4194304ULL;
constexpr uint64_t kAccumulatorBase = 5242880ULL;
constexpr uint64_t kAuxiliaryBase = 6291456ULL;

using Record = std::array<uint32_t, 16>;

enum class Fault {
    kNone,
    kHbm,
    kInputNonfinite,
    kWeightNonfinite,
    kMultiplyOverflow,
    kAddOverflow,
    kAccumulatorNonfinite,
};

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(1);
}

void require(bool condition, const std::string& message) {
    if (!condition) fail(message);
}

std::vector<uint8_t> load_bytes(const char* path, size_t count) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint8_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {
        if (value > 0xffU) fail(std::string("wide byte in ") + path);
        result.push_back(static_cast<uint8_t>(value));
    }
    require(result.size() == count, std::string(path) + " count differs");
    return result;
}

std::vector<uint16_t> load_codes16(const char* path, size_t count) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint16_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {
        if (value > 0xffffU) fail(std::string("wide code in ") + path);
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
        if (value > 0xffffffffULL)
            fail(std::string("wide code in ") + path);
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

void eval_low(Vot_ta_dma_matmul_sequencer& dut) {
    dut.clk = 0;
    dut.eval();
}

uint16_t lane16(const std::array<uint32_t, 4>& words, unsigned lane) {
    const unsigned word = lane / 2U;
    const unsigned shift = (lane & 1U) * 16U;
    return static_cast<uint16_t>(words[word] >> shift);
}

struct Model {
    const std::vector<uint8_t>& payload;
    const std::vector<uint16_t>& inputs;
    const std::vector<uint32_t>& expected_accumulators;
    const std::vector<uint16_t>& expected_outputs;
    std::vector<uint16_t> weights;
    std::vector<uint32_t> accumulators;
    std::vector<uint16_t> outputs;
    Fault fault = Fault::kNone;

    bool pending_hbm = false;
    uint32_t pending_hbm_burst = 0;
    uint32_t pending_hbm_delay = 0;
    bool hbm_response_valid = false;
    std::array<uint32_t, 16> hbm_response_data{};
    uint8_t hbm_response_error = 0;

    bool pending_read = false;
    uint16_t pending_read_data = 0;
    uint32_t pending_read_delay = 0;
    bool sram_response_valid = false;
    uint16_t sram_response_data = 0;

    uint32_t cycles = 0;
    uint32_t hbm_requests = 0;
    uint32_t hbm_responses = 0;
    uint32_t dma_writes = 0;
    uint32_t accumulator_reads = 0;
    uint32_t input_reads = 0;
    uint32_t weight_reads = 0;
    uint32_t sram_read_responses = 0;
    uint32_t accumulator_writes = 0;
    uint32_t auxiliary_writes = 0;
    uint32_t request_stalls = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;

    Model(const std::vector<uint8_t>& payload_value,
          const std::vector<uint16_t>& input_value,
          const std::vector<uint32_t>& expected_accumulator_value,
          const std::vector<uint16_t>& expected_output_value)
        : payload(payload_value),
          inputs(input_value),
          expected_accumulators(expected_accumulator_value),
          expected_outputs(expected_output_value),
          weights(kWeightsPerTile),
          accumulators(kOutputs),
          outputs(kOutputs) {}

    void reset(Fault selected_fault) {
        fault = selected_fault;
        std::fill(weights.begin(), weights.end(), 0);
        std::fill(accumulators.begin(), accumulators.end(), 0);
        std::fill(outputs.begin(), outputs.end(), 0);
        pending_hbm = false;
        pending_hbm_burst = 0;
        pending_hbm_delay = 0;
        hbm_response_valid = false;
        hbm_response_data.fill(0);
        hbm_response_error = 0;
        pending_read = false;
        pending_read_data = 0;
        pending_read_delay = 0;
        sram_response_valid = false;
        sram_response_data = 0;
        cycles = 0;
        hbm_requests = 0;
        hbm_responses = 0;
        dma_writes = 0;
        accumulator_reads = 0;
        input_reads = 0;
        weight_reads = 0;
        sram_read_responses = 0;
        accumulator_writes = 0;
        auxiliary_writes = 0;
        request_stalls = 0;
        read_stalls = 0;
        write_stalls = 0;
    }

    void drive(Vot_ta_dma_matmul_sequencer& dut) const {
        dut.hbm_request_ready = (cycles % 5U) != 1U;
        dut.sram_read_ready = (cycles & 1U) != 0U;
        dut.sram_write_ready = (cycles % 7U) != 3U;
        dut.hbm_response_valid = hbm_response_valid;
        dut.hbm_response_error = hbm_response_error;
        for (unsigned word = 0; word < hbm_response_data.size(); ++word)
            dut.hbm_response_data[word] = hbm_response_data[word];
        dut.sram_response_valid = sram_response_valid;
        dut.sram_response_data = sram_response_data;
    }

    void raw_reset_tick(Vot_ta_dma_matmul_sequencer& dut) {
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

    void cycle(Vot_ta_dma_matmul_sequencer& dut) {
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

        if (hbm_response_fire) {
            require(hbm_response_valid, "HBM response fire without valid");
            hbm_response_valid = false;
            hbm_response_error = 0;
            ++hbm_responses;
        }
        if (hbm_request_fire) {
            require(!pending_hbm && !hbm_response_valid,
                    "more than one HBM request outstanding");
            require(hbm_address == kHbmBase + hbm_requests * 64ULL,
                    "HBM request address differs");
            require(hbm_bytes == 64U, "HBM request byte count differs");
            pending_hbm = true;
            pending_hbm_burst = hbm_requests;
            pending_hbm_delay = (hbm_requests % 4U) + 1U;
            ++hbm_requests;
        }
        if (had_pending_hbm) {
            if (pending_hbm_delay == 0 && !hbm_response_valid) {
                for (unsigned word = 0; word < 16; ++word) {
                    uint32_t value = 0;
                    for (unsigned byte = 0; byte < 4; ++byte) {
                        const size_t offset =
                            pending_hbm_burst * 64U + word * 4U + byte;
                        value |= static_cast<uint32_t>(payload[offset])
                                 << (byte * 8U);
                    }
                    hbm_response_data[word] = value;
                }
                hbm_response_error = fault == Fault::kHbm ? 1U : 0U;
                hbm_response_valid = true;
                pending_hbm = false;
            } else {
                --pending_hbm_delay;
            }
        }

        if (read_response_fire) {
            require(sram_response_valid, "SRAM response fire without valid");
            sram_response_valid = false;
            ++sram_read_responses;
        }
        if (read_fire) {
            require(!pending_read && !sram_response_valid,
                    "more than one SRAM read outstanding");
            if (read_address >= kInputBase &&
                read_address < kInputBase + kInputs * 2ULL) {
                const uint32_t index = static_cast<uint32_t>(
                    (read_address - kInputBase) >> 1U);
                require(index == input_reads, "input read order differs");
                require(dma_writes ==
                            ((index / kInputsPerTile) + 1U) *
                                kDmaWritesPerTile,
                        "input read bypassed current DMA");
                if (index == 0U && fault == Fault::kInputNonfinite)
                    pending_read_data = 0x7f80U;
                else if (index == 0U &&
                         (fault == Fault::kMultiplyOverflow ||
                          fault == Fault::kAddOverflow))
                    pending_read_data = 0x7f7fU;
                else if (index == 1U && fault == Fault::kAddOverflow)
                    pending_read_data = 0x7f7fU;
                else
                    pending_read_data = inputs[index];
                ++input_reads;
            } else if (read_address >= kWeightBase &&
                       read_address < kWeightBase + kDmaBytesPerTile) {
                const uint32_t index = static_cast<uint32_t>(
                    (read_address - kWeightBase) >> 1U);
                require(index == weight_reads % kWeightsPerTile,
                        "weight read order differs");
                if (weight_reads == 0U && fault == Fault::kWeightNonfinite)
                    pending_read_data = 0x7f80U;
                else if (weight_reads == 0U &&
                         fault == Fault::kMultiplyOverflow)
                    pending_read_data = 0x7f7fU;
                else if (weight_reads < 2U && fault == Fault::kAddOverflow)
                    pending_read_data = 0x3f80U;
                else
                    pending_read_data = weights[index];
                ++weight_reads;
            } else if (read_address >= kAccumulatorBase &&
                       read_address < kAccumulatorBase + kOutputs * 4ULL) {
                const uint32_t index = static_cast<uint32_t>(
                    (read_address - kAccumulatorBase) >> 1U);
                require(index == accumulator_reads % 128U,
                        "accumulator reload order differs");
                if (index == 1U && fault == Fault::kAccumulatorNonfinite)
                    pending_read_data = 0x7f80U;
                else if ((index & 1U) == 0U)
                    pending_read_data = accumulators[index >> 1U] & 0xffffU;
                else
                    pending_read_data = accumulators[index >> 1U] >> 16U;
                ++accumulator_reads;
            } else {
                fail("SRAM read outside MATMUL operands");
            }
            pending_read = true;
            pending_read_delay =
                ((input_reads + weight_reads + accumulator_reads) % 3U) + 1U;
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
            if (write_address >= kWeightBase &&
                write_address < kWeightBase + kDmaBytesPerTile) {
                const uint32_t transaction =
                    dma_writes % kDmaWritesPerTile;
                require(write_enable == 0xffffU,
                        "DMA SRAM byte enable differs");
                require(write_address == kWeightBase + transaction * 16ULL,
                        "DMA SRAM write address differs");
                for (unsigned lane = 0; lane < 8; ++lane) {
                    const uint32_t index = dma_writes * 8U + lane;
                    const uint16_t code =
                        static_cast<uint16_t>(payload[index * 2U]) |
                        static_cast<uint16_t>(payload[index * 2U + 1U] << 8U);
                    require(lane16(write_words, lane) == code,
                            "DMA SRAM write data differs");
                    weights[transaction * 8U + lane] = code;
                }
                ++dma_writes;
            } else if (write_address >= kAccumulatorBase &&
                       write_address < kAccumulatorBase + kOutputs * 4ULL) {
                const uint32_t index = static_cast<uint32_t>(
                    (write_address - kAccumulatorBase) >> 2U);
                require(write_enable == 0x000fU,
                        "accumulator SRAM byte enable differs");
                require(index == accumulator_writes % kOutputs,
                        "accumulator write order differs");
                require(write_words[0] ==
                            expected_accumulators[accumulator_writes],
                        "accumulator write data differs");
                accumulators[index] = write_words[0];
                ++accumulator_writes;
            } else if (write_address >= kAuxiliaryBase &&
                       write_address < kAuxiliaryBase + kOutputs * 2ULL) {
                const uint32_t index = static_cast<uint32_t>(
                    (write_address - kAuxiliaryBase) >> 1U);
                require(accumulator_writes == kAccumulatorWrites,
                        "auxiliary write preceded final accumulator tile");
                require(write_enable == 0x0003U,
                        "auxiliary SRAM byte enable differs");
                require(index == auxiliary_writes,
                        "auxiliary write order differs");
                require(lane16(write_words, 0) == expected_outputs[index],
                        "auxiliary write data differs");
                outputs[index] = lane16(write_words, 0);
                ++auxiliary_writes;
            } else {
                fail("SRAM write outside composed regions");
            }
        }

        ++cycles;
        require(cycles <= 3000000U, "campaign case timed out");
        dut.clk = 0;
        dut.eval();
    }
};

void set_record(Vot_ta_dma_matmul_sequencer& dut, const Record& record) {
    for (unsigned word = 0; word < record.size(); ++word)
        dut.command_record[word] = record[word];
}

void reset_case(Vot_ta_dma_matmul_sequencer& dut, Model& model, Fault fault) {
    model.reset(fault);
    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.cmd_last = 0;
    dut.program_done_ready = 0;
    dut.abi_major = 2;
    dut.abi_minor = 5;
    for (unsigned cycle = 0; cycle < 3; ++cycle) model.raw_reset_tick(dut);
    dut.rst_n = 1;
    model.drive(dut);
    eval_low(dut);
}

void submit(Vot_ta_dma_matmul_sequencer& dut, Model& model,
            const Record& record, uint32_t expected_index, bool last) {
    for (unsigned wait = 0; !dut.cmd_ready; ++wait) {
        require(wait < 3000000U, "command ready timeout");
        model.cycle(dut);
    }
    set_record(dut, record);
    dut.expected_command_index = expected_index;
    dut.cmd_last = last;
    dut.cmd_valid = 1;
    model.cycle(dut);
    dut.cmd_valid = 0;
}

void await_done(Vot_ta_dma_matmul_sequencer& dut, Model& model) {
    for (unsigned wait = 0; !dut.program_done_valid; ++wait) {
        require(wait < 3000000U, "program completion timeout");
        model.cycle(dut);
    }
    require(!dut.cmd_ready && dut.program_active,
            "completion/program-active protocol differs");
}

void acknowledge(Vot_ta_dma_matmul_sequencer& dut, Model& model) {
    for (unsigned cycle = 0; cycle < 3; ++cycle) {
        require(dut.program_done_valid, "program completion was not stable");
        model.cycle(dut);
    }
    dut.program_done_ready = 1;
    model.cycle(dut);
    dut.program_done_ready = 0;
}

void require_no_destination(const Vot_ta_dma_matmul_sequencer& dut,
                            const Model& model) {
    require(dut.program_done_matmul_accumulator_write_count == 0U &&
                dut.program_done_matmul_auxiliary_write_count == 0U &&
                model.accumulator_writes == 0U &&
                model.auxiliary_writes == 0U &&
                std::all_of(model.accumulators.begin(),
                            model.accumulators.end(),
                            [](uint32_t code) { return code == 0U; }) &&
                std::all_of(model.outputs.begin(), model.outputs.end(),
                            [](uint16_t code) { return code == 0U; }),
            "fault exposed a MATMUL destination write");
}

void prove_success(Vot_ta_dma_matmul_sequencer& dut, Model& model,
                   const std::vector<Record>& records) {
    reset_case(dut, model, Fault::kNone);
    for (uint32_t offset = 0; offset < kCommands; ++offset)
        submit(dut, model, records[offset], 3U + offset,
               offset == kCommands - 1U);
    await_done(dut, model);
    require(dut.program_done_error == 0U &&
                dut.program_done_failing_command_index == 0xffffffffU &&
                dut.program_done_last_command_index == 34U &&
                dut.program_done_commands_accepted == kCommands &&
                dut.program_done_commands_completed == kCommands &&
                dut.program_done_hbm_request_count == 8192U &&
                dut.program_done_hbm_response_count == 8192U &&
                dut.program_done_hbm_bytes_read == kDmaBytes &&
                dut.program_done_sram_read_count == 268160U &&
                dut.program_done_sram_bytes_read == 536320U &&
                dut.program_done_sram_write_count == 33856U &&
                dut.program_done_sram_bytes_written == 528512U &&
                dut.program_done_matmul_accumulator_read_count ==
                    kAccumulatorReads &&
                dut.program_done_matmul_input_read_count == kInputs &&
                dut.program_done_matmul_weight_read_count == kWeights &&
                dut.program_done_matmul_multiply_count == kWeights &&
                dut.program_done_matmul_add_count == kWeights &&
                dut.program_done_matmul_output_count == kAccumulatorWrites &&
                dut.program_done_matmul_accumulator_write_count ==
                    kAccumulatorWrites &&
                dut.program_done_matmul_auxiliary_write_count == kOutputs &&
                dut.program_done_matmul_output_saturation_count == 0U &&
                model.hbm_requests == 8192U &&
                model.hbm_responses == 8192U &&
                model.dma_writes == kDmaWrites &&
                model.accumulator_reads == kAccumulatorReads &&
                model.input_reads == kInputs &&
                model.weight_reads == kWeights &&
                model.sram_read_responses == 268160U &&
                model.accumulator_writes == kAccumulatorWrites &&
                model.auxiliary_writes == kOutputs &&
                model.request_stalls != 0U && model.read_stalls != 0U &&
                model.write_stalls != 0U && !model.pending_hbm &&
                !model.pending_read && !model.hbm_response_valid &&
                !model.sram_response_valid,
            "successful program accounting differs");
    for (uint32_t index = 0; index < kOutputs; ++index) {
        require(model.accumulators[index] ==
                    model.expected_accumulators[
                        (kTiles - 1U) * kOutputs + index],
                "final accumulator payload differs");
        require(model.outputs[index] == model.expected_outputs[index],
                "final BF16 payload differs");
    }
    acknowledge(dut, model);
}

void prove_hbm(Vot_ta_dma_matmul_sequencer& dut, Model& model,
               const std::vector<Record>& records) {
    reset_case(dut, model, Fault::kHbm);
    submit(dut, model, records[0], 3U, false);
    await_done(dut, model);
    require(dut.program_done_error == 11U &&
                dut.program_done_failing_command_index == 3U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                dut.program_done_hbm_request_count == 1U &&
                dut.program_done_hbm_response_count == 1U &&
                dut.program_done_hbm_bytes_read == 0U &&
                dut.program_done_sram_write_count == 0U &&
                model.hbm_requests == 1U && model.hbm_responses == 1U &&
                model.dma_writes == 0U,
            "HBM fail-stop accounting differs");
    require_no_destination(dut, model);
    acknowledge(dut, model);
}

void prove_crc(Vot_ta_dma_matmul_sequencer& dut, Model& model,
              const std::vector<Record>& records) {
    reset_case(dut, model, Fault::kNone);
    Record bad = records[1];
    bad[15] ^= 0x80000000U;
    submit(dut, model, records[0], 3U, false);
    submit(dut, model, bad, 4U, false);
    await_done(dut, model);
    require(dut.program_done_error == 1U &&
                dut.program_done_failing_command_index == 4U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_hbm_request_count == 512U &&
                dut.program_done_sram_read_count == 0U,
            "CRC fail-stop accounting differs");
    require_no_destination(dut, model);
    acknowledge(dut, model);
}

void prove_order(Vot_ta_dma_matmul_sequencer& dut, Model& model,
                const std::vector<Record>& records) {
    reset_case(dut, model, Fault::kNone);
    submit(dut, model, records[0], 3U, false);
    submit(dut, model, records[1], 3U, false);
    await_done(dut, model);
    require(dut.program_done_error == 12U &&
                dut.program_done_failing_command_index == 3U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_sram_read_count == 0U,
            "program-order fail-stop accounting differs");
    require_no_destination(dut, model);
    acknowledge(dut, model);
}

void prove_numeric(Vot_ta_dma_matmul_sequencer& dut, Model& model,
                   const std::vector<Record>& records, Fault fault,
                   uint8_t error, uint32_t reads,
                   uint32_t successful_arithmetic) {
    reset_case(dut, model, fault);
    submit(dut, model, records[0], 3U, false);
    submit(dut, model, records[1], 4U, false);
    await_done(dut, model);
    require(dut.program_done_error == error &&
                dut.program_done_failing_command_index == 4U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_sram_read_count == reads &&
                dut.program_done_sram_bytes_read == reads * 2U &&
                dut.program_done_sram_write_count == kDmaWritesPerTile &&
                dut.program_done_sram_bytes_written == kDmaBytesPerTile &&
                dut.program_done_matmul_multiply_count ==
                    successful_arithmetic &&
                dut.program_done_matmul_add_count == successful_arithmetic &&
                dut.program_done_matmul_output_count == 0U &&
                model.input_reads + model.weight_reads == reads &&
                model.sram_read_responses == reads,
            "numeric fail-stop accounting differs");
    require_no_destination(dut, model);
    acknowledge(dut, model);
}

void prove_accumulator_fault(Vot_ta_dma_matmul_sequencer& dut, Model& model,
                             const std::vector<Record>& records) {
    reset_case(dut, model, Fault::kAccumulatorNonfinite);
    for (uint32_t offset = 0; offset < 4U; ++offset)
        submit(dut, model, records[offset], 3U + offset, false);
    await_done(dut, model);
    require(dut.program_done_error == 9U &&
                dut.program_done_failing_command_index == 6U &&
                dut.program_done_commands_accepted == 4U &&
                dut.program_done_commands_completed == 3U &&
                dut.program_done_hbm_request_count == 1024U &&
                dut.program_done_hbm_bytes_read == 65536U &&
                dut.program_done_sram_read_count == 16642U &&
                dut.program_done_sram_bytes_read == 33284U &&
                dut.program_done_sram_write_count == 4160U &&
                dut.program_done_sram_bytes_written == 65792U &&
                dut.program_done_matmul_accumulator_read_count == 2U &&
                dut.program_done_matmul_input_read_count == 256U &&
                dut.program_done_matmul_weight_read_count == 16384U &&
                dut.program_done_matmul_multiply_count == 16384U &&
                dut.program_done_matmul_add_count == 16384U &&
                dut.program_done_matmul_accumulator_write_count == 64U &&
                dut.program_done_matmul_auxiliary_write_count == 0U &&
                model.accumulator_reads == 2U &&
                model.accumulator_writes == 64U &&
                model.auxiliary_writes == 0U,
            "accumulator reload fail-stop accounting differs");
    for (uint32_t index = 0; index < kOutputs; ++index) {
        require(model.accumulators[index] ==
                    model.expected_accumulators[index],
                "reload fault modified prior accumulator tile");
        require(model.outputs[index] == 0U,
                "reload fault exposed auxiliary output");
    }
    acknowledge(dut, model);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const auto records = load_records("matmul_commands.hex", kCommands);
    const auto payload = load_bytes("matmul_payload.hex", kDmaBytes);
    const auto inputs = load_codes16("matmul_input.hex", kInputs);
    const auto accumulators =
        load_codes32("matmul_accumulators.hex", kAccumulatorWrites);
    const auto outputs = load_codes16("matmul_output.hex", kOutputs);
    Vot_ta_dma_matmul_sequencer dut;
    Model model(payload, inputs, accumulators, outputs);

    prove_success(dut, model, records);
    prove_crc(dut, model, records);
    prove_hbm(dut, model, records);
    prove_order(dut, model, records);
    prove_numeric(dut, model, records, Fault::kInputNonfinite, 9U, 1U, 0U);
    prove_numeric(dut, model, records, Fault::kWeightNonfinite, 9U, 257U, 0U);
    prove_numeric(dut, model, records, Fault::kMultiplyOverflow, 10U, 257U, 0U);
    prove_numeric(dut, model, records, Fault::kAddOverflow, 10U, 258U, 1U);
    prove_accumulator_fault(dut, model, records);
    dut.final();
    std::cout
        << "PASS: Qwen DMA+MATMUL RTL slice commands=32 k_tiles=16 "
        << "inputs=4096 weights=262144 accumulators=1024 bf16=64 faults=8 "
        << "vector_set="
        << "4fe481b232112fe5b494cab1ca4445159b91a512a524471bee18267fe5525129"
        << "\n";
    return 0;
}
