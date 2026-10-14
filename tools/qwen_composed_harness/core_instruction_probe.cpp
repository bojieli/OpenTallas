// Read-only provenance witness; compile against the actual generated model PCH.
#include "Vot_hdc_core_vector_weight_native_candidate.h"
#include "Vot_hdc_core_vector_weight_native_candidate___024root.h"
#include "core_instruction_probe.hpp"
#include <stdexcept>
CoreInstructionFace read_actual_core_instruction_face(const Vot_hdc_core_vector_weight_native_candidate&core){
 const auto&root=*core.rootp;CoreInstructionFace face;
 face.load=root.ot_hdc_core_vector_weight_native_candidate__DOT__load;
 face.nx_valid=root.ot_hdc_core_vector_weight_native_candidate__DOT__nx_v;
 if(face.load){
  unsigned rd=root.ot_hdc_core_vector_weight_native_candidate__DOT__fq_rd;
  if(rd>=4)throw std::runtime_error("actual instruction FIFO read pointer outside depth4");
  const auto&word=root.ot_hdc_core_vector_weight_native_candidate__DOT__fq[rd];
  for(unsigned i=0;i<32;i++)face.actual_fifo_word[i]=word[i];
 }
 return face;
}
