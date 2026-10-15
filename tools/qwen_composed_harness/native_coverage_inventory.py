#!/usr/bin/env python3
"""Source-line inventory of the functional Qwen harness's native blockers.

This preserves numerical evidence and separately refuses native qualification.
It intentionally has no flag to waive an on-chip model. A native replacement
must supply its actual elaborated target and memory/operand seams to
native_operation_coverage.py, then pass the independent numerical/physical gates.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SPECS = [
 ('board_digital_router', 'cpp_transport', 'on_chip_interconnect', 'rtl/test/qwen_host/include/qkd_host_board_router_fixture.hpp', r'class|struct|pipe|reserve|credit', 'Inter-package digital routing/reservations and pipes are C++ fixture logic; only analog PHY/off-chip signal behavior may be modeled.'),
 ('host_external_transactions', 'behavioral', 'off_chip_signal', 'rtl/test/qwen_host/include/qkd_host_board_router_fixture.hpp', r'bar|BAR|CQ|completions|dma', 'External host MMIO/DMA endpoint behavior is allowed, provided it does not replace the on-chip host digital controller.'),
 ('collective_vm_descriptor_seams', 'cpp_transport', 'on_chip_interconnect', 'tools/qwen_composed_harness/native59_helpers.hpp', r'pending\[rank\]|external_commit|descriptors|observed.credit', 'Helper/collective engines are real RTL; descriptor ROM, VM reads/writes, and dynamic credit handoff are C++ seams.'),
 ('embedding_admission_bypass', 'cpp_control', 'on_chip_controller', 'tools/qwen_composed_harness/embedding_owner.hpp', r'su_descriptor_reserved=1|kv_write_drained=.*=1', 'Embedding model ties native admission/memory availability true instead of native production controller evidence.'),
 ('host_token_service', 'rtl', 'on_chip_controller', 'tools/qwen_native_host/host_owner.hpp', r'Vqkd_host_token_service|Vot_qwen_tp8_token_epoch_allocator|Vot_qwen_tp8_token_cohort', 'Actual token service/epoch/cohort RTL; full physical qkd_host composition remains absent.'),

 ('lv6_compute', 'rtl', 'on_chip_engine', 'tools/qwen_composed_harness/layer_models.hpp', r'Vot_hdc_core_vector_weight_native_candidate core', 'Real numerical core, substitutes for the physical ROM tile die; target composition still absent.'),
 ('lv6_fp_units', 'dpi_cpp', 'on_chip_engine', 'tools/qwen_composed_harness/layer_models.hpp', r'only DPI|stateless ot_v41x_fadd', 'FP32 arithmetic supplied by C functions in the current live archive; RTL-FP hierarchical replacement build pending.'),
 ('attention_fp_units', 'dpi_cpp', 'on_chip_engine', 'tools/qwen_composed_harness/run_whole_token.sh', r'sim_nhb_fp_lat_dpi.o|sim_hdc_v41x_fastfp_dpi.o', 'Current attention shared library imports C FP operations; RTL-FP serial hierarchy build pending.'),
 ('program_rom', 'cpp_arrays', 'on_chip_rom', 'tools/qwen_composed_harness/rom_vm_adapter.hpp', r'program\(read_hex|std::vector<HexWord<32>> program', 'Program ROM is C++ storage, directly installed from fixture files.'),
 ('weight_scale_constant_rom', 'cpp_arrays', 'on_chip_rom', 'tools/qwen_composed_harness/rom_vm_adapter.hpp', r'code\(read_hex|scales\(read_hex|constants\(read_hex', 'Checkpoint weights are input data, not golden results, but their on-chip ROM implementation is modeled.'),
 ('vm_sram', 'cpp_arrays', 'on_chip_sram', 'tools/qwen_composed_harness/rom_vm_adapter.hpp', r'std::vector<uint32_t> vm|vm\(VM_WORDS|external_commit\(', 'The VM SRAM and commit storage are host arrays, not target SRAM macros.'),
 ('q_res_vm_seams', 'cpp_queues', 'on_chip_interconnect', 'tools/qwen_composed_harness/services_vm_adapter.hpp', r'QResponse r|vm.at|acks.push_back', 'Q reads, RES memory writes and ACK returns are C++ queues/storage operations.'),
 ('split_link', 'latency_model', 'on_chip_interconnect', 'tools/qwen_composed_harness/services_vm_adapter.hpp', r'link_latency|committed_level', 'Only selected Q/RES faces have modeled latency; actual split bridge/CRC/replay/controller RTL is not instantiated here.'),
 ('native_kv_routing', 'cpp_transport', 'on_chip_interconnect', 'tools/qwen_composed_harness/kernel_physical_rows.hpp', r'class KernelRows|class SectorWrites|backend\.', 'Kernel/sector controller-to-engine packet ownership and response dispatch are C++.'),
 ('embedding_rom', 'cpp_storage', 'on_chip_rom', 'tools/qwen_composed_harness/embedding_owner.hpp', r'read_hex|bank|next_a|next_b', 'Embedding arithmetic is RTL, table/VM storage and its connectivity remain modeled.'),
 ('embedding_vm_broadcast', 'cpp_transport', 'on_chip_interconnect', 'tools/qwen_composed_harness/embedding_owner.hpp', r'external_commit|for\(auto&rank', 'C++ broadcasts computed RTL embedding words into each rank VM.'),
 ('head_bank_switch', 'cpp_control', 'on_chip_controller', 'tools/qwen_composed_harness/layer_models.hpp', r'void switch_head|void prepare_head_first|switch_banks\(image', 'Head uses actual LV6 arithmetic and real helper argmax, but ROM reinstallation/stage startup are C++ control.'),
 ('head_host_result_seam', 'cpp_control', 'on_chip_interconnect', 'tools/qwen_composed_harness/full_layer_helpers_loop.hpp', r'inputs.result_tag=|inputs.result_generation=|inputs.result_token=', 'Result comes from real RTL global argmax, then C++ drives the HOST result face; not golden numerical injection, still not a target RTL seam.'),
 ('layer_bank_sequencing', 'cpp_control', 'on_chip_controller', 'tools/qwen_composed_harness/full_layer_helpers_loop.hpp', r'vm.segment_base=|switch_layer|switch_head|link.banks', 'C++ sequences layers, rank segment starts, bank switches and helper banks.'),
 ('boot_and_link_initialization', 'cpp_control', 'on_chip_controller', 'tools/qwen_native_host/host_lifecycle.hpp', r'in.por_n=|in.link_up=|in.boot\[|in.kst', 'POR is a testbench/off-chip stimulus; synthesized boot-complete/link-ready status is nevertheless fixture driven, not native die controller proof.'),
 ('native_contract_admission', 'cpp_control', 'on_chip_controller', 'tools/qwen_composed_harness/layer_models.hpp', r'c.native_contract_ready=1|su_descriptor_reserved=|kv_admit_ready', 'Capability is tied true and native/SU admission uses dynamic ready; fails owner fixed-cycle/no-credit target rule.'),
 ('host_lifecycle_drain_control', 'cpp_control', 'on_chip_controller', 'tools/qwen_composed_harness/whole_token.cpp', r'in.kv_drained=|in.vm_drained=|in.collective_drained=|Terminal term', 'C++ derives drain and terminal sequencing; cannot replace native die host/controller wiring.'),
 ('oracle_seeded_initial_state', 'oracle_seed', 'on_chip_initial_state', 'tools/qwen_composed_harness/whole_token.cpp', r'OT_SEED_X|OT_SEED_HEAD|seed_x', 'Independent seeded runs supply golden layer-input X or golden layer35 X for head-only mode. Valid numerical unit scope, forbidden as continuous native token proof.'),
 ('expected_only_observers', 'python_cpp', 'expected_observer', 'tools/qwen_composed_harness/verify_full_layer.py', r'np.load|mismatch =|vm_words|expected_path', 'Expected-only comparisons read DUT effects; allowed observers, do not supply computed DUT values.'),
 ('token_expected_only', 'cpp', 'expected_observer', 'tools/qwen_composed_harness/whole_token.cpp', r'bool match=token==|expected_token|expected_value', 'Final token/value expectations compare after retirement and do not drive the token value.'),
 ('hbm_dram_phy', 'behavioral', 'off_chip_memory', 'tools/qwen_composed_harness/actual_phy.hpp', r'Backing|struct|class', 'Off-chip DRAM/PHY numerical model is allowed; its digital controller must still be RTL.'),
 ('native_services_frontend', 'rtl', 'on_chip_controller', 'tools/qwen_composed_harness/layer_models.hpp', r'Vot_qwen_tp8_native_services_frontend_native59 front', 'Real default-enabled native59 frontend; source prerequisites now published.'),
 ('native_attention_kernel', 'rtl', 'on_chip_engine', 'tools/qwen_composed_harness/layer_models.hpp', r'Vot_qwen_tp8_attention_service kernel', 'Real attention control/transport/compute topology, with separate forbidden DPI FP substitutions listed above.'),
 ('kv_sector_adapter', 'rtl', 'on_chip_controller', 'tools/qwen_composed_harness/layer_models.hpp', r'Vot_qwen_tp8_kv_sector_adapter sector', 'Real sector adapter; does not turn the C++ surrounding routing/storage into target RTL.'),
 ('physical_compute_die', 'absent', 'on_chip_engine', 'results/arch/qwen_composed_harness_1014/whole_token/engine_coverage.json', r'ROM die tiles|DVM x-slice', 'No physical qfd_seq/ROM tiles/trimmed VM/DVM composition in the LV6 harness.'),
 ('physical_kvsys_die', 'absent', 'on_chip_engine', 'rtl/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv', r'module ot_qkvd_split_kvlink', 'Real split RTL exists independently, but the token composition does not instantiate the full KV/system die target.'),
]


def inventory(root):
    result = {}
    for name, implementation, role, source, pattern, note in SPECS:
        p = root/source
        lines = p.read_text().splitlines() if p.exists() else []
        refs = [{'line': i, 'text': line} for i, line in enumerate(lines, 1) if re.search(pattern, line)]
        result[name] = {'implementation': implementation, 'role': role, 'source': source, 'source_sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None, 'source_lines': refs, 'evidence_missing': not refs, 'note': note, 'drives_dut': role != 'expected_observer'}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result={'schema':'opentallas.qwen_native_inventory.v1','policy':'ONLY PHY and off-chip signals/storage may be modeled; on-chip engines/controllers/ROM/SRAM/link logic must be actual target RTL/macros. Expected-only observers permitted.','native_qualified':False,'historical_numerical_verdicts_preserved':True,'inventory_completeness':'Conservative direct-source audit; full native elaborated target and transitive inventory are not present and cannot be certified. Any missing evidence is blocking.','components':inventory(a.root)}
    result['blocking_components']=[name for name,c in result['components'].items() if (c['implementation'] not in ('rtl','macro') and c['role'] not in ('phy','off_chip_signal','off_chip_memory','expected_observer')) or c['evidence_missing']]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('FAIL native qualification: '+str(len(result['blocking_components']))+' modeled/absent/unproven on-chip components; arithmetic receipts preserved')
    raise SystemExit(1)

if __name__=='__main__':main()
