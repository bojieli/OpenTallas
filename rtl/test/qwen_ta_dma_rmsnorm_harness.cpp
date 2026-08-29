#include "Vot_ta_dma_rmsnorm_sequencer.h"
#include "verilated.h"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kElements = 4096U;
constexpr uint32_t kDmaBytes = 8192U;
constexpr uint32_t kDmaWrites = 512U;
constexpr uint64_t kHbmBase = 1244659712ULL;
constexpr uint64_t kInputBase = 1048576ULL;
constexpr uint64_t kWeightBase = 2097152ULL;
constexpr uint64_t kDestinationBase = 3145728ULL;

constexpr std::array<uint32_t, 16> kDmaRecord = {{
    0x00000101U, 0x00000001U, 0x00000001U, 0x4a300000U,
    0x00000000U, 0x00000000U, 0x00000000U, 0x00200000U,
    0x00000000U, 0x00000000U, 0x00000000U, 0x00002000U,
    0x00000000U, 0x00000000U, 0x00000000U, 0xb5d7c76dU,
}};
constexpr std::array<uint32_t, 16> kRmsRecord = {{
    0x00000320U, 0x00000002U, 0x00000001U, 0x00100000U,
    0x00000000U, 0x00200000U, 0x00000000U, 0x00300000U,
    0x00000000U, 0x00000000U, 0x00000000U, 0x00000001U,
    0x00001000U, 0x358637bdU, 0x00000000U, 0xea9b35a4U,
}};
constexpr std::array<uint32_t, 16> kBadCrcRecord = {{
    0x00000320U, 0x00000002U, 0x00000001U, 0x00100000U,
    0x00000000U, 0x00200000U, 0x00000000U, 0x00300000U,
    0x00000000U, 0x00000000U, 0x00000000U, 0x00000001U,
    0x00001000U, 0x358637bdU, 0x00000000U, 0x6a9b35a4U,
}};

enum class Fault {
    kNone,
    kHbm,
    kInputNonfinite,
    kInputOverflow,
    kWeightNonfinite,
    kWeightOverflow,
};

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(1);
}

void require(bool condition, const std::string& message) {
    if (!condition) fail(message);
}

std::vector<uint8_t> load_bytes(const char* path) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint8_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {
        if (value > 0xffU) fail(std::string("wide byte in ") + path);
        result.push_back(static_cast<uint8_t>(value));
    }
    require(result.size() == kDmaBytes,
            std::string(path) + " byte count differs");
    return result;
}

std::vector<uint16_t> load_codes(const char* path) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint16_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {
        if (value > 0xffffU) fail(std::string("wide code in ") + path);
        result.push_back(static_cast<uint16_t>(value));
    }
    require(result.size() == kElements,
            std::string(path) + " element count differs");
    return result;
}

void eval_low(Vot_ta_dma_rmsnorm_sequencer& dut) {
    dut.clk = 0;
    dut.eval();
}

uint16_t lane16(const Vot_ta_dma_rmsnorm_sequencer& dut, unsigned lane) {
    const unsigned word = lane / 2U;
    const unsigned shift = (lane & 1U) * 16U;
    return static_cast<uint16_t>(dut.sram_write_data[word] >> shift);
}

struct Model {
    const std::vector<uint8_t>& payload;
    const std::vector<uint16_t>& inputs;
    const std::vector<uint16_t>& expected;
    std::vector<uint16_t> weights;
    std::vector<uint16_t> destination;
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
    uint32_t input_reads = 0;
    uint32_t weight_reads = 0;
    uint32_t sram_read_responses = 0;
    uint32_t rms_writes = 0;
    uint32_t request_stalls = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;

    Model(const std::vector<uint8_t>& payload_value,
          const std::vector<uint16_t>& input_value,
          const std::vector<uint16_t>& expected_value)
        : payload(payload_value),
          inputs(input_value),
          expected(expected_value),
          weights(kElements),
          destination(kElements) {}

    void reset(Fault selected_fault) {
        fault = selected_fault;
        std::fill(weights.begin(), weights.end(), 0);
        std::fill(destination.begin(), destination.end(), 0);
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
        input_reads = 0;
        weight_reads = 0;
        sram_read_responses = 0;
        rms_writes = 0;
        request_stalls = 0;
        read_stalls = 0;
        write_stalls = 0;
    }

    void drive(Vot_ta_dma_rmsnorm_sequencer& dut) const {
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

    void raw_reset_tick(Vot_ta_dma_rmsnorm_sequencer& dut) {
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

    void cycle(Vot_ta_dma_rmsnorm_sequencer& dut) {
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
        std::array<uint16_t, 8> write_lanes{};
        for (unsigned lane = 0; lane < write_lanes.size(); ++lane)
            write_lanes[lane] = lane16(dut, lane);

        const bool had_pending_hbm = pending_hbm;
        const bool had_pending_read = pending_read;

        dut.clk = 1;
        dut.eval();

        request_stalls += request_stalled ? 1U : 0U;
        read_stalls += read_stalled ? 1U : 0U;
        write_stalls += write_stalled ? 1U : 0U;

        if (hbm_response_fire) {
            require(hbm_response_valid, "HBM response fire without model valid");
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
            require(sram_response_valid,
                    "SRAM response fire without model valid");
            sram_response_valid = false;
            ++sram_read_responses;
        }
        if (read_fire) {
            require(!pending_read && !sram_response_valid,
                    "more than one SRAM read outstanding");
            require(dma_writes == kDmaWrites,
                    "RMSNorm read bypassed incomplete DMA");
            if (read_address >= kInputBase &&
                read_address < kInputBase + kDmaBytes) {
                const uint32_t index =
                    static_cast<uint32_t>((read_address - kInputBase) >> 1U);
                require(index == input_reads, "input read order differs");
                if (index == 0 && fault == Fault::kInputNonfinite)
                    pending_read_data = 0x7f80U;
                else if (index == 0 && fault == Fault::kInputOverflow)
                    pending_read_data = 0x7f7fU;
                else
                    pending_read_data = inputs[index];
                ++input_reads;
            } else if (read_address >= kWeightBase &&
                       read_address < kWeightBase + kDmaBytes) {
                const uint32_t index =
                    static_cast<uint32_t>((read_address - kWeightBase) >> 1U);
                require(index == weight_reads, "weight read order differs");
                if (index == 0 && fault == Fault::kWeightNonfinite)
                    pending_read_data = 0x7f80U;
                else if (index == 0 && fault == Fault::kWeightOverflow)
                    pending_read_data = 0x7f7fU;
                else
                    pending_read_data = weights[index];
                ++weight_reads;
            } else {
                fail("SRAM read outside RMSNorm operands");
            }
            pending_read = true;
            pending_read_delay = ((input_reads + weight_reads) % 3U) + 1U;
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
                write_address < kWeightBase + kDmaBytes) {
                require(write_enable == 0xffffU,
                        "DMA SRAM byte enable differs");
                require(write_address == kWeightBase + dma_writes * 16ULL,
                        "DMA SRAM write address differs");
                for (unsigned lane = 0; lane < 8; ++lane) {
                    const uint32_t index = dma_writes * 8U + lane;
                    const uint16_t expected_code =
                        static_cast<uint16_t>(payload[index * 2U]) |
                        static_cast<uint16_t>(payload[index * 2U + 1U] << 8U);
                    require(write_lanes[lane] == expected_code,
                            "DMA SRAM write data differs");
                    weights[index] = write_lanes[lane];
                }
                ++dma_writes;
            } else if (write_address >= kDestinationBase &&
                       write_address < kDestinationBase + kDmaBytes) {
                const uint32_t index = static_cast<uint32_t>(
                    (write_address - kDestinationBase) >> 1U);
                require(input_reads == kElements && weight_reads == kElements,
                        "write preceded complete numeric pass");
                require(write_enable == 0x0003U,
                        "RMSNorm SRAM byte enable differs");
                require(index == rms_writes, "RMSNorm write order differs");
                require(write_lanes[0] == expected[index],
                        "RMSNorm write data differs");
                destination[index] = write_lanes[0];
                ++rms_writes;
            } else {
                fail("SRAM write outside composed regions");
            }
        }

        ++cycles;
        require(cycles <= 300000U, "campaign case timed out");
        dut.clk = 0;
        dut.eval();
    }
};

void set_record(Vot_ta_dma_rmsnorm_sequencer& dut,
                const std::array<uint32_t, 16>& record) {
    for (unsigned word = 0; word < record.size(); ++word)
        dut.command_record[word] = record[word];
}

void reset_case(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model,
                Fault fault) {
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

void submit(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model,
            const std::array<uint32_t, 16>& record, uint32_t expected_index,
            bool last) {
    for (unsigned wait = 0; !dut.cmd_ready; ++wait) {
        require(wait < 300000U, "command ready timeout");
        model.cycle(dut);
    }
    set_record(dut, record);
    dut.expected_command_index = expected_index;
    dut.cmd_last = last;
    dut.cmd_valid = 1;
    model.cycle(dut);
    dut.cmd_valid = 0;
}

void await_done(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    for (unsigned wait = 0; !dut.program_done_valid; ++wait) {
        require(wait < 300000U, "program completion timeout");
        model.cycle(dut);
    }
    require(!dut.cmd_ready && dut.program_active,
            "completion/program-active protocol differs");
}

void acknowledge(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    for (unsigned cycle = 0; cycle < 3; ++cycle) {
        require(dut.program_done_valid,
                "program completion was not stable");
        model.cycle(dut);
    }
    dut.program_done_ready = 1;
    model.cycle(dut);
    dut.program_done_ready = 0;
}

void require_dma_success(const Vot_ta_dma_rmsnorm_sequencer& dut,
                         const Model& model) {
    require(dut.program_done_hbm_request_count == 128U &&
                dut.program_done_hbm_response_count == 128U &&
                dut.program_done_hbm_bytes_read == kDmaBytes &&
                model.hbm_requests == 128U && model.hbm_responses == 128U &&
                model.dma_writes == kDmaWrites,
            "successful DMA accounting differs");
}

void prove_success(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    reset_case(dut, model, Fault::kNone);
    submit(dut, model, kDmaRecord, 1U, false);
    submit(dut, model, kRmsRecord, 2U, true);
    await_done(dut, model);
    require_dma_success(dut, model);
    require(dut.program_done_error == 0U &&
                dut.program_done_failing_command_index == 0xffffffffU &&
                dut.program_done_last_command_index == 2U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 2U &&
                dut.program_done_sram_read_count == 8192U &&
                dut.program_done_sram_bytes_read == 16384U &&
                dut.program_done_sram_write_count == 4608U &&
                dut.program_done_sram_bytes_written == 16384U &&
                dut.program_done_element_count == kElements &&
                dut.program_done_normalized_saturation_count == 0U &&
                dut.program_done_output_saturation_count == 0U &&
                dut.program_done_mean_square_code == 0x3a5bf2caU &&
                dut.program_done_inverse_rms_code == 0x420a0297U &&
                model.input_reads == kElements &&
                model.weight_reads == kElements &&
                model.sram_read_responses == 8192U &&
                model.rms_writes == kElements &&
                model.request_stalls != 0U && model.read_stalls != 0U &&
                model.write_stalls != 0U && !model.pending_hbm &&
                !model.pending_read && !model.hbm_response_valid &&
                !model.sram_response_valid,
            "successful program accounting differs");
    for (uint32_t index = 0; index < kElements; ++index) {
        const uint16_t weight =
            static_cast<uint16_t>(model.payload[index * 2U]) |
            static_cast<uint16_t>(model.payload[index * 2U + 1U] << 8U);
        require(model.weights[index] == weight,
                "staged weight payload differs");
        require(model.destination[index] == model.expected[index],
                "destination payload differs");
    }
    acknowledge(dut, model);
}

void prove_crc(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    reset_case(dut, model, Fault::kNone);
    submit(dut, model, kDmaRecord, 1U, false);
    submit(dut, model, kBadCrcRecord, 2U, true);
    await_done(dut, model);
    require_dma_success(dut, model);
    require(dut.program_done_error == 1U &&
                dut.program_done_failing_command_index == 2U &&
                dut.program_done_last_command_index == 2U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_sram_read_count == 0U &&
                dut.program_done_sram_write_count == kDmaWrites &&
                dut.program_done_sram_bytes_written == kDmaBytes &&
                model.input_reads == 0U && model.weight_reads == 0U &&
                model.rms_writes == 0U,
            "CRC fail-stop accounting differs");
    acknowledge(dut, model);
}

void prove_hbm(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    reset_case(dut, model, Fault::kHbm);
    submit(dut, model, kDmaRecord, 1U, true);
    await_done(dut, model);
    require(dut.program_done_error == 11U &&
                dut.program_done_failing_command_index == 1U &&
                dut.program_done_last_command_index == 1U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                dut.program_done_hbm_request_count == 1U &&
                dut.program_done_hbm_response_count == 1U &&
                dut.program_done_hbm_bytes_read == 0U &&
                dut.program_done_sram_read_count == 0U &&
                dut.program_done_sram_write_count == 0U &&
                model.hbm_requests == 1U && model.hbm_responses == 1U &&
                model.dma_writes == 0U && model.rms_writes == 0U,
            "HBM fail-stop accounting differs");
    acknowledge(dut, model);
}

void prove_order(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model) {
    reset_case(dut, model, Fault::kNone);
    submit(dut, model, kDmaRecord, 1U, false);
    submit(dut, model, kRmsRecord, 1U, true);
    await_done(dut, model);
    require_dma_success(dut, model);
    require(dut.program_done_error == 12U &&
                dut.program_done_failing_command_index == 1U &&
                dut.program_done_last_command_index == 1U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_sram_read_count == 0U &&
                model.rms_writes == 0U,
            "program-order fail-stop accounting differs");
    acknowledge(dut, model);
}

void prove_numeric(Vot_ta_dma_rmsnorm_sequencer& dut, Model& model,
                   Fault fault, uint8_t error, uint32_t reads,
                   uint32_t elements, uint32_t mean, uint32_t inverse) {
    reset_case(dut, model, fault);
    submit(dut, model, kDmaRecord, 1U, false);
    submit(dut, model, kRmsRecord, 2U, true);
    await_done(dut, model);
    require_dma_success(dut, model);
    require(dut.program_done_error == error &&
                dut.program_done_failing_command_index == 2U &&
                dut.program_done_last_command_index == 2U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_sram_read_count == reads &&
                dut.program_done_sram_bytes_read == reads * 2U &&
                dut.program_done_sram_write_count == kDmaWrites &&
                dut.program_done_sram_bytes_written == kDmaBytes &&
                dut.program_done_element_count == elements &&
                dut.program_done_normalized_saturation_count == 0U &&
                dut.program_done_output_saturation_count == 0U &&
                dut.program_done_mean_square_code == mean &&
                dut.program_done_inverse_rms_code == inverse &&
                model.input_reads + model.weight_reads == reads &&
                model.sram_read_responses == reads &&
                model.rms_writes == 0U,
            "numeric fail-stop accounting differs");
    acknowledge(dut, model);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const auto payload = load_bytes("payload.hex");
    const auto inputs = load_codes("input.hex");
    const auto expected = load_codes("expected.hex");
    Vot_ta_dma_rmsnorm_sequencer dut;
    Model model(payload, inputs, expected);

    prove_success(dut, model);
    prove_crc(dut, model);
    prove_hbm(dut, model);
    prove_order(dut, model);
    prove_numeric(dut, model, Fault::kInputNonfinite, 9U, 1U, 1U, 0U, 0U);
    prove_numeric(dut, model, Fault::kInputOverflow, 10U, 1U, 1U, 0U, 0U);
    prove_numeric(dut, model, Fault::kWeightNonfinite, 9U, 4097U, 1U,
                  0x3a5bf2caU, 0x420a0297U);
    prove_numeric(dut, model, Fault::kWeightOverflow, 10U, 4097U, 1U,
                  0x3a5bf2caU, 0x420a0297U);
    dut.final();
    std::cout
        << "PASS: Qwen DMA+RMSNorm RTL sequence commands=2 elements=4096 "
        << "faults=7 vector_set="
        << "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
        << "\n";
    return 0;
}
