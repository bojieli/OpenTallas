// Independent Verilator checker for the exact shipped ABI 3.0 engine prefix.
// It parses the memory images itself, observes every completion handshake, and
// never consumes an expectation through the RTL design.
#include "Vot_a3_shipped_prefix_top.h"
#include "verilated.h"

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {

constexpr std::size_t kCases = 4;
constexpr std::size_t kCaseStride = 80;
constexpr std::size_t kIssueStride = 4;
constexpr std::size_t kResultWords = 98304;
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
        dut.cfg_symbol_base = 0;
        dut.cfg_symbol_mask = 0;
        dut.cfg_max_retired_work = 0;
        dut.cfg_state_count = 0;
        dut.cfg_index_base = 0;
        dut.cfg_source_base = 0;
        dut.cfg_source_launch_stride = 0;
        dut.cfg_embedding_source_base = 0;
        dut.cfg_rms_input_base = 0;
        dut.cfg_rms_weight_base = 0;
        dut.cfg_transfer_index_base = 0;
        dut.cfg_transfer_source_base = 0;
        dut.cfg_matmul_input_base = 0;
        dut.cfg_matmul_weight_object_0 = UINT32_MAX;
        dut.cfg_matmul_weight_base_0 = 0;
        dut.cfg_matmul_weight_object_1 = UINT32_MAX;
        dut.cfg_matmul_weight_base_1 = 0;
        dut.cfg_matmul_weight_object_2 = UINT32_MAX;
        dut.cfg_matmul_weight_base_2 = 0;
        dut.cfg_head_input_object_0 = UINT32_MAX;
        dut.cfg_head_input_base_0 = 0;
        dut.cfg_head_input_object_1 = UINT32_MAX;
        dut.cfg_head_input_base_1 = 0;
        dut.cfg_head_weight_object_0 = UINT32_MAX;
        dut.cfg_head_weight_base_0 = 0;
        dut.cfg_head_weight_object_1 = UINT32_MAX;
        dut.cfg_head_weight_base_1 = 0;
        dut.cfg_rope_input_object_0 = UINT32_MAX;
        dut.cfg_rope_input_base_0 = 0;
        dut.cfg_rope_input_object_1 = UINT32_MAX;
        dut.cfg_rope_input_base_1 = 0;
        dut.cfg_rope_coefficient_object = UINT32_MAX;
        dut.cfg_rope_coefficient_base = 0;
        dut.cfg_output_base = 0;
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
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    try {
        const auto cases = read_hex("p3_case.hex");
        const auto issues = read_hex("p3_issue.hex");
        const auto expected = read_hex("p3_expect.hex");
        const auto meta = read_hex("p3_meta.hex");
        const bool multicast_overlay = meta.size() == 26 && meta[1] == 29;
        const std::size_t expected_issue_words =
            multicast_overlay ? 132 : 128;
        if (cases.size() != kCases * kCaseStride ||
            issues.size() != expected_issue_words ||
            expected.size() != 91136 || meta.size() != 26)
            throw std::runtime_error("shipped-prefix vector geometry mismatch");

        Checker check;
        Model model;
        model.reset();
        check.equal("meta case count", meta[0], kCases);
        check.equal("meta case stride", meta[4], kCaseStride);
        check.equal("meta result memory", meta[7], kResultWords);
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
        std::uint64_t total_views = 0;

        for (std::size_t case_index = 0; case_index < kCases; ++case_index) {
            const auto* record = &cases[case_index * kCaseStride];
            model.dut.cfg_program_base = record[0];
            model.dut.cfg_instruction_count = record[1];
            model.dut.cfg_desc_base = record[2];
            model.dut.cfg_desc_count = record[3];
            model.dut.cfg_symbol_base = record[4];
            model.dut.cfg_symbol_mask = record[5];
            model.dut.cfg_entry_pc = record[6];
            model.dut.cfg_max_retired_work =
                (static_cast<std::uint64_t>(record[8]) << 32) | record[7];
            model.dut.cfg_state_count = record[9];
            model.dut.cfg_index_base = record[10];
            model.dut.cfg_source_base = record[11];
            model.dut.cfg_source_launch_stride = record[12];
            model.dut.cfg_embedding_source_base = record[32];
            model.dut.cfg_rms_input_base = record[40];
            model.dut.cfg_rms_weight_base = record[41];
            model.dut.cfg_transfer_index_base = record[42];
            model.dut.cfg_transfer_source_base = record[43];
            model.dut.cfg_matmul_input_base = record[48];
            model.dut.cfg_matmul_weight_object_0 = record[49];
            model.dut.cfg_matmul_weight_base_0 = record[50];
            model.dut.cfg_matmul_weight_object_1 = record[51];
            model.dut.cfg_matmul_weight_base_1 = record[52];
            model.dut.cfg_matmul_weight_object_2 = record[53];
            model.dut.cfg_matmul_weight_base_2 = record[54];
            model.dut.cfg_head_input_object_0 = record[58];
            model.dut.cfg_head_input_base_0 = record[59];
            model.dut.cfg_head_input_object_1 = record[60];
            model.dut.cfg_head_input_base_1 = record[61];
            model.dut.cfg_head_weight_object_0 = record[62];
            model.dut.cfg_head_weight_base_0 = record[63];
            model.dut.cfg_head_weight_object_1 = record[64];
            model.dut.cfg_head_weight_base_1 = record[65];
            model.dut.cfg_rope_input_object_0 = record[71];
            model.dut.cfg_rope_input_base_0 = record[72];
            model.dut.cfg_rope_input_object_1 = record[73];
            model.dut.cfg_rope_input_base_1 = record[74];
            model.dut.cfg_rope_coefficient_object = record[75];
            model.dut.cfg_rope_coefficient_base = record[76];
            model.dut.cfg_output_base = record[13];

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
            auto observe = [&]() {
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
            std::uint32_t guard = 0;
            while (!model.dut.done && guard < 150000000) {
                model.cycle(observe);
                ++guard;
            }
            if (!model.dut.done) {
                ++check.failures;
                std::cerr << "FAIL: case " << case_index << " timed out\n";
            }

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
                        record[14]);
            check.equal("DMA gather launches",
                        model.dut.dma_gather_launch_count, record[33]);
            check.equal("embedding launches",
                        model.dut.embedding_launch_count, record[34]);
            check.equal("RMSNorm launches", model.dut.rms_norm_launch_count,
                        record[44]);
            check.equal("head RMSNorm launches",
                        model.dut.head_rms_norm_launch_count, record[66]);
            check.equal("RoPE launches", model.dut.rope_launch_count,
                        record[77]);
            check.equal("DMA transfer launches",
                        model.dut.dma_transfer_launch_count, record[45]);
            check.equal("MATMUL launches", model.dut.matmul_launch_count,
                        record[55]);
            if (multicast_overlay) {
                check.equal("multicast launches",
                            model.dut.multicast_launch_count, record[79]);
                check.equal("multicast faults",
                            model.dut.multicast_fault_count, 0);
            }
            check.equal("capability responses",
                        model.dut.capability_fault_count, record[29]);
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
                        model.dut.engine_result_count, record[67]);
            check.equal("last engine work count", model.dut.engine_work_count,
                        record[68]);
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

            if (multicast_overlay && record[79] != 0) {
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

            for (std::uint32_t word = 0; word < record[15]; ++word) {
                model.dut.result_read_addr = record[13] + word;
                model.dut.eval();
                check.equal("real result word", model.dut.result_read_data,
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
        check.equal("total launches", total_launches, meta[1]);
        check.equal("total DMA gathers", total_gathers, meta[8]);
        check.equal("total embedding launches", total_embeddings, meta[9]);
        check.equal("total RMSNorm launches", total_rms_norms, meta[12]);
        check.equal("total head RMSNorm launches", total_head_rms_norms,
                    meta[20]);
        check.equal("total RoPE launches", total_ropes, meta[24]);
        check.equal("total transfer launches", total_transfers, meta[13]);
        check.equal("total MATMUL launches", total_matmuls, meta[16]);
        if (multicast_overlay)
            check.equal("total multicast launches", total_multicasts, 1);
        check.equal("total result words", total_words, meta[2]);
        check.equal("total resolved views", total_views, meta[3]);
        for (std::uint32_t word = 0; word < meta[2]; ++word) {
            model.dut.result_read_addr = word;
            model.dut.eval();
            check.equal("final retained result", model.dut.result_read_data,
                        expected[word]);
        }
        for (std::uint32_t word = meta[2]; word < kResultWords; ++word) {
            model.dut.result_read_addr = word;
            model.dut.eval();
            check.equal("unwritten result tail", model.dut.result_read_data,
                        kUnwritten);
        }

        model.dut.final();
        if (check.failures != 0) {
            std::cerr << "FAILURES: " << check.failures
                      << " checks=" << check.checks << "\n";
            return 1;
        }
        if (multicast_overlay)
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
