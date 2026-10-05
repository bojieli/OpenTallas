// Simulation-only RPC harness. ONE scheduler evaluates all four real clocks.
#include "Vha5_cp20_runtime.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc,char** argv) {
    VerilatedContext context; context.commandArgs(argc,argv);
    Vha5_cp20_runtime m(&context);
    uint64_t now=0,cycles=0;
    std::array<uint64_t,4> next={2000,416,500,450};
    m.por_n=0;m.clk_host=0;m.clk_sm=0;m.clk_mem=0;m.clk_link=0;
    m.cmd_we=0;m.cmd_addr=0;m.cmd_wdata=VlWide<4>{};m.db_v=0;
    m.db_token=0;m.db_pos=0;m.db_job=0;m.db_generation=0;m.cpl_rdy=0;
    m.im_we=0;m.im_addr=0;m.im_data=0;m.probe_sel=0;m.probe_sector=0;
    m.eval();
    auto wide=[](const auto& words,int n) {
        for(int i=n-1;i>=0;--i) std::cout<<std::setw(8)<<std::setfill('0')<<uint32_t(words[i]);
        std::cout<<std::setfill(' ');
    };
    auto snapshot=[&]() {
        std::cout<<"HA5 "<<std::hex<<now<<' '<<cycles<<' '<<unsigned(m.rst_sm_n)<<' '
                 <<unsigned(m.sys_fault)<<' '<<unsigned(m.db_rdy)<<' '<<unsigned(m.cpl_v)<<' ';
        wide(m.cpl_data,7);
        std::cout<<' '<<m.probe_pc<<' '<<unsigned(m.probe_issue)<<' '
                 <<unsigned(m.probe_fetch_request)<<' '<<unsigned(m.probe_fetch_line)<<std::endl;
    };
    auto tick=[&]() {
        bool rose=false;
        while(true) {
            now=*std::min_element(next.begin(),next.end());
            if(m.eventsPending())now=std::min(now,m.nextTimeSlot());
            context.time(now);
            bool sm_event=next[1]==now;
            if(next[0]==now){m.clk_host=!m.clk_host;next[0]+=2000;}
            if(sm_event){m.clk_sm=!m.clk_sm;next[1]+=m.clk_sm?417:416;}
            if(next[2]==now){m.clk_mem=!m.clk_mem;next[2]+=500;}
            if(next[3]==now){m.clk_link=!m.clk_link;next[3]+=450;}
            m.eval();
            if(sm_event && m.clk_sm){rose=true;++cycles;}
            if(sm_event && !m.clk_sm && rose)break;
        }
    };
    snapshot();
    for(std::string line;std::getline(std::cin,line);) {
        std::istringstream in(line);char op;in>>op;in>>std::hex;
        if(op=='Q'){std::cout<<"HA5 OK"<<std::endl;break;}
        if(op=='S'){snapshot();continue;}
        if(op=='T'){tick();snapshot();continue;}
        if(op=='R'){unsigned value;in>>value;m.por_n=value;}
        else if(op=='I'){unsigned mask,address;uint64_t word;in>>mask>>address>>word;m.im_we=mask;m.im_addr=address;m.im_data=word;}
        else if(op=='D'){
            unsigned die,we,address,valid,token,pos,job,generation,ready;uint64_t word;
            in>>die>>we>>address>>word>>valid>>token>>pos>>job>>generation>>ready;
            if(die>1)return 3;
            auto bit=[&](auto& port,unsigned value,unsigned width,unsigned shift){
                uint64_t mask=((uint64_t(1)<<width)-1)<<shift;
                port=(uint64_t(port)&~mask)|(uint64_t(value)<<shift);
            };
            bit(m.cmd_we,we,1,die);bit(m.cmd_addr,address,8,die*8);
            m.cmd_wdata[die*2]=uint32_t(word);m.cmd_wdata[die*2+1]=uint32_t(word>>32);
            bit(m.db_v,valid,1,die);bit(m.db_token,token,32,die*32);
            bit(m.db_pos,pos,32,die*32);bit(m.db_job,job,32,die*32);
            bit(m.db_generation,generation,4,die*4);bit(m.cpl_rdy,ready,1,die);
        } else if(op=='M'){
            unsigned sel,sector;in>>sel>>sector;m.probe_sel=sel;m.probe_sector=sector;m.eval();
            std::cout<<"HA5 "<<std::hex;wide(m.probe_data,8);std::cout<<std::endl;continue;
        } else return 4;
        if(!in)return 5;
        m.eval();std::cout<<"HA5 OK"<<std::endl;
    }
    m.final();return 0;
}
