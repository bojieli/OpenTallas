#pragma once
#include <array>
#include <cstdint>
class Vot_hdc_core_vector_weight_native_candidate;
struct CoreInstructionFace {bool load=false,nx_valid=false;std::array<uint32_t,32> actual_fifo_word{};};
// Implemented against the genuine generated root class. No manual offsets,
// input-word substitution, source reconstruction or state mutation is allowed.
CoreInstructionFace read_actual_core_instruction_face(const Vot_hdc_core_vector_weight_native_candidate&core);
