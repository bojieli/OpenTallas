#include "rom_vm_adapter.hpp"
#include <iostream>
int main(int argc,char**argv){if(argc!=4)return 2;try{qwen_native::RomVmAdapter a(argv[1],argv[2],argv[3]);std::cout<<"ADAPTER_IMAGE_PASS code="<<a.code.size()<<" scales="<<a.scales.size()<<" crom="<<a.constants.size()<<" program="<<a.program.size()<<" VM="<<a.vm.size()<<"\n";}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
