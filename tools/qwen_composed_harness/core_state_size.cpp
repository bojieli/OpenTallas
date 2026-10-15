#include "core_instruction_probe.hpp"
#include <iostream>
int main(){std::cout<<"{\"actual_generated_root_bytes\":"<<actual_core_root_bytes()<<",\"eight_rank_root_bytes\":"<<8*actual_core_root_bytes()<<",\"scope\":\"COMPILED_LAYOUT_SIZE_ONLY_NOT_RUNTIME_RSS\"}\n";}
