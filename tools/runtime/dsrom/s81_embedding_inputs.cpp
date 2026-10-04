#include "s81_source_caller_plan.hpp"
#include "s81_embedding_parent.hpp"
#include "s81_embedding_checkpoint_client.hpp"
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>

namespace {
// One actual ROM request/response stream per TP4 group, not four unpriced
// macro read ports. Fanout commits are acknowledged only by all four native
// C8 VM endpoints. The parent model must still price that fanout/arbitration.
struct GroupVM {
 DsromS81Runtime& runtime;
 uint64_t identity;uint32_t token;
 bool c8_context(uint64_t& id,uint32_t& tok,uint16_t& entry) {
   for(auto* die:runtime.dies) {
     uint64_t actual_id;uint32_t actual_tok;uint16_t actual_entry;
     if(!die->c8_context(actual_id,actual_tok,actual_entry) || actual_id!=identity || actual_tok!=token)return false;
     entry=actual_entry;
   }
   id=identity;tok=token;return true;
 }
 bool fault(){for(auto* die:runtime.dies)if(die->fault())return true;return false;}
 bool c8_workspace_write(uint64_t id,uint32_t address,uint32_t bits) {
   bool accepted=true;
   for(auto* die:runtime.dies)accepted=die->c8_workspace_write(id,address,bits)&&accepted;
   return accepted;
 }
};
struct Bound {
 DsromS81Runtime& runtime;
 GroupVM vm;
 std::shared_ptr<DsromS81EmbeddingCheckpointClient> source;
 DsromS81EmbeddingParent reader;
 long previous_cycle=-1;
 Bound(DsromS81Runtime& r,const DsromC8SourceOffer& offer,const char* socket)
 :runtime(r),vm{r,offer.identity,offer.token},
  source(new DsromS81EmbeddingCheckpointClient(socket,offer.token,offer.position)),
  reader(offer.token,offer.identity,0,[s=source](uint64_t id,uint32_t macro,uint32_t row){return s->read(id,macro,row);}){}
 bool restore(const DsromC8SourceOffer& offer) {
   if(offer.identity!=vm.identity || offer.token!=vm.token)throw std::runtime_error("foreign cold input offer");
   uint64_t id;uint32_t token;uint16_t entry;
   if(!vm.c8_context(id,token,entry))return false;
   if(runtime.cycle()!=previous_cycle) {
     previous_cycle=runtime.cycle();reader.edge(vm);
   }
   return reader.committed();
 }
};
std::map<std::pair<DsromS81Runtime*,uint64_t>,std::weak_ptr<Bound>> groups;
}

// Literal cold producer node only: field operations need preceding native
// vector/reduction producers and must not receive embedding as normalized XN.
void dsrom_s81_bind_inputs(DsromS81Runtime& runtime,DsromS81SourceRank& rank,const char* source_node) {
 if(!source_node || std::strcmp(source_node,"embedding") || runtime.stage!=0 ||
    runtime.dies.size()!=4 || rank.offer.position!=0 || !runtime.cycle)
   throw std::runtime_error("embedding input producer supports actual cold embedding node at position0 only; other nodes require native producers");
 const char* socket=std::getenv("DSROM_S81_EMBED_SOCKET");
 if(!socket || !*socket)throw std::runtime_error("actual released embedding socket required");
 auto key=std::make_pair(&runtime,rank.offer.identity);
 auto bound=groups[key].lock();
 if(!bound){bound=std::make_shared<Bound>(runtime,rank.offer,socket);groups[key]=bound;}
 rank.restore_inputs=[bound](const DsromC8SourceOffer& offer){return bound->restore(offer);};
 rank.input_visible=[bound](const DsromC8SourceOffer& offer){
   uint64_t id;uint32_t token;uint16_t entry;
   return bound->reader.committed() && bound->vm.c8_context(id,token,entry) &&
          id==offer.identity && token==offer.token;
 };
 // Popper binds real remote/allcopy receipt authorities separately. This
 // producer neither substitutes booleans for them nor releases the context.
}
