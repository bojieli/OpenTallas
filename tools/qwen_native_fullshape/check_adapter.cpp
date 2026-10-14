#include "rom_vm_adapter.hpp"
#include <iostream>
struct Mock {
    void eval() {}
    qwen_native::HexWord<32> prog_q{};
    qwen_native::HexWord<qwen_native::G*qwen_native::W/4> int8_wrom_q{};
    qwen_native::HexWord<qwen_native::G*qwen_native::W/2> scale_q{};
    qwen_native::HexWord<qwen_native::SW*2> crom_q{};
    qwen_native::HexWord<qwen_native::G> vx_q{};
    qwen_native::HexWord<qwen_native::SW> va_q{},vb_q{},vc_q{},vw_su_data{};
    qwen_native::HexWord<qwen_native::G/32> scale_gre{},vx_re{},vw_me_we{};
    qwen_native::HexWord<qwen_native::G*24/32> scale_addr{},vx_addr{},vw_me_addr{};
    qwen_native::HexWord<qwen_native::G*qwen_native::W/32> vw_me_mask{};
    qwen_native::HexWord<qwen_native::G*qwen_native::W> vw_me_data{};
    qwen_native::HexWord<qwen_native::SW*24/32> va_addr{},vb_addr{},vc_addr{},crom_addr{},vw_su_addr{};
    qwen_native::HexWord<qwen_native::W> vw_mx_data{};
    uint64_t va_re=0,vb_re=0,vc_re=0,crom_re=0,vw_su_we=0;
    uint32_t prog_re=0,prog_addr=0,int8_wrom_re=0,int8_wrom_addr=0,wrom_re=0;
    uint32_t vw_rd_we=0,vw_rd_addr=0,vw_rd_data=0,vw_mx_we=0,vw_mx_addr=0,vw_mx_mask=0;
    uint32_t instruction_issue=0,instruction_unit=0,instruction_pc=0,end_retired=0,end_pc=0;
};
int main(int argc,char**argv){
    if(argc!=4)return 2;
    try {
        qwen_native::RomVmAdapter a(argv[1],argv[2],argv[3]);
        Mock m;auto old=a.vm[0];m.va_re=1;m.vw_su_we=1;m.vw_su_data[0]=old^1;
        a.begin_edge(m);a.commit_after_edge();m.vw_su_we=0;a.begin_edge(m);
        if(m.va_q[0]!=old || a.vm[0]!=(old^1))throw std::runtime_error("old-read/write separation failed");
        a.commit_after_edge();a.segment_base=14;m.instruction_issue=1;m.instruction_unit=a.program[14][0]&3;m.instruction_pc=0;
        a.begin_edge(m);a.commit_after_edge();
        if(a.accepted.back().global_pc!=14 || a.accepted.back().instruction!=a.program[14])throw std::runtime_error("accepted PC/source mismatch");
        m.instruction_issue=0;a.segment_base=0;m.prog_re=1;m.prog_addr=a.program.size();
        a.begin_edge(m);a.commit_after_edge();m.prog_re=0;a.begin_edge(m);
        if(m.prog_q!=qwen_native::HexWord<32>{})throw std::runtime_error("speculativeROMtail notzero");
        a.store(1,1,"TEST");a.store(1,2,"MUTANT");bool refused=false;
        try{a.commit_after_edge();}catch(const std::runtime_error&){refused=true;}
        if(!refused)throw std::runtime_error("conflicting writes mutant accepted");
        std::cout<<"ADAPTER_IMAGE_AND_MEMORY_PASS code="<<a.code.size()<<" scales="<<a.scales.size()<<" crom="<<a.constants.size()<<" program="<<a.program.size()<<" VM="<<a.vm.size()<<" old_read=1 accepted_pc=14 collision_mutant_refused=1\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
