#pragma once
#include "Vot_qwen_tp8_token_epoch_allocator.h"
#include <stdexcept>
#include <fstream>
#include <filesystem>
// One actual allocator model for the token, never one epoch source per rank.
// This owner does not invent terminal HOST/link fence evidence. Until those
// actual endpoints are bound, terminal/fence stay low and the grant stays busy.
struct TokenEpochOwner {
 Vot_qwen_tp8_token_epoch_allocator rtl;
 unsigned expected_epoch,token,position,generation=2;
 bool request_sent=false,delivered=false,request_fire=false,grant_fire=false;
 unsigned held_epoch=0,held_token=0,held_position=0,held_generation=0;
 uint64_t held_tag=0,edges=0,grant_edge=0;
 TokenEpochOwner(VerilatedContext&ctx,unsigned epoch,unsigned tok,unsigned pos)
 :rtl(&ctx,"central_token_epoch_owner"),expected_epoch(epoch),token(tok),position(pos){
  rtl.clk=0;rtl.por_n=0;rtl.warm_ready=0;rtl.request_valid=0;rtl.request_token=tok;
  rtl.request_position=pos;rtl.request_generation=generation;rtl.grant_ready=0;
  rtl.terminal_valid=0;rtl.terminal_tag=0;rtl.terminal_generation=0;rtl.terminal_done=0;rtl.terminal_fault=0;
  rtl.terminal_kv_drained=rtl.terminal_vm_drained=rtl.terminal_collective_drained=rtl.terminal_host_drained=0;
  rtl.wrap_fence_valid=rtl.wrap_links_drained=rtl.wrap_link_reset_seen=rtl.wrap_retraining_done=0;
  rtl.eval();
 }
 void low(bool boot_done,bool providers_ready){
  rtl.clk=0;rtl.por_n=boot_done;rtl.warm_ready=boot_done;rtl.request_valid=boot_done&&!request_sent;
  rtl.grant_ready=providers_ready;rtl.eval();
  request_fire=rtl.request_valid&&rtl.request_ready;grant_fire=rtl.grant_valid&&rtl.grant_ready;
  if(grant_fire){
   held_epoch=rtl.grant_epoch;held_token=rtl.grant_token;held_position=rtl.grant_position;
   held_generation=rtl.grant_generation;held_tag=rtl.grant_tag;
   uint64_t expected=(uint64_t(held_epoch)<<43)|(uint64_t(held_token)<<19)|(uint64_t(held_position)<<6);
   if(held_epoch!=expected_epoch||held_token!=token||held_position!=position||held_generation!=generation||held_tag!=expected)
    throw std::runtime_error("actual central allocator grant differs from request/plan");
  }
 }
 void rise(){
  rtl.clk=1;rtl.eval();++edges;
  if(request_fire)request_sent=true;
  if(grant_fire){if(delivered)throw std::runtime_error("duplicate central token grant");delivered=true;grant_edge=edges;}
  if(rtl.identity_fault)throw std::runtime_error("actual central epoch allocator fault");
  if(delivered&&!rtl.busy)throw std::runtime_error("actual allocator retired without actual terminal/HOST drain binding");
 }
 void fall(){rtl.clk=0;rtl.eval();}
 void identities(const std::filesystem::path&file,unsigned stage,unsigned segment)const{
  if(!delivered||!rtl.busy||rtl.identity_fault||stage>37||segment>63)
   throw std::runtime_error("collective identity without live accepted central allocator grant");
  std::ofstream out(file);out<<"[{\"epoch\":"<<held_epoch<<",\"stage\":"<<stage<<",\"token\":"<<held_token<<",\"position\":"<<held_position<<",\"segment\":"<<segment<<"}]\n";
 }
 void save(const std::filesystem::path&file)const{
  std::ofstream out(file);out<<"{\"scope\":\"ACTUAL_CENTRAL_HELD_GRANT_NOT_HOST_OR_TERMINAL_CLOSURE\",\"delivered\":"<<(delivered?"true":"false")<<",\"epoch\":"<<held_epoch<<",\"token\":"<<held_token<<",\"position\":"<<held_position<<",\"generation\":"<<held_generation<<",\"grant_tag\":"<<held_tag<<",\"grant_edge\":"<<grant_edge<<",\"terminal_bound\":false,\"link_fence_bound\":false,\"busy\":"<<unsigned(rtl.busy)<<"}\n";
 }
};
