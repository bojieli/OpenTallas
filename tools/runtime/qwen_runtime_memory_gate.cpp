#include "qwen_runtime_memory.hpp"
#include <cstdio>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 auto codes=QwenRuntimeMemory::load_hex(std::string(argv[1])+"/die0/matrix_int8.hex",6144*4);
 auto scales=QwenRuntimeMemory::load_hex(std::string(argv[1])+"/die0/matrix_scale_bf16.hex",8);
 auto vm=QwenRuntimeMemory::load_hex(std::string(argv[1])+"/vm_x_fp32.hex",1);
 QwenRuntimeMemory memory(177808,3);std::copy(vm.begin(),vm.end(),memory.words.begin());
 uint32_t before=memory.words[4096];auto e=memory.capture({{4096,0},{4097,1}},{{4096,1},{4096,2},{4096,3}});
 if(memory.response[0]!=0||memory.words[4096]!=before)return 3;
 memory.commit_after_rtl_edge(e);if(memory.response[0]!=before||memory.words[4096]!=3)return 4;
 auto e2=memory.capture({{4096,2}},{});memory.commit_after_rtl_edge(e2);
 if(memory.response[0]!=before||memory.response[2]!=3)return 5;
 std::ofstream sample(argv[2]);
 for(size_t r:{size_t(0),size_t(17),size_t(1487)})for(size_t g:{size_t(0),size_t(63),size_t(511),size_t(6143)})for(size_t l=0;l<4;l++)sample<<r<<" "<<g<<" "<<l<<" "<<codes.at(r*6144*4+g*4+l)<<"\n";
 for(size_t r:{size_t(0),size_t(17),size_t(50615)})for(size_t l=0;l<8;l++)sample<<"S "<<r<<" "<<l<<" "<<scales.at(r*8+l)<<"\n";
 printf("PASS checkpoint memory loader: code_u32=%zu scale_u32=%zu vm=%zu read-before-write/held-response/ordered-writes\n",codes.size(),scales.size(),vm.size());
}
