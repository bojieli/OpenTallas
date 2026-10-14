#include "Vot_qwen_tp8_native_services_frontend_native59.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "services_vm_adapter.hpp"
static_assert(qwen_native_services::HasQTag<Vot_qwen_tp8_native_services_frontend_native59>::value,"actual frontend must expose both TAG59 ports");
void instantiate_actual_port_bridge(Vot_qwen_tp8_native_services_frontend_native59&front,Vot_qwen_tp8_attention_service&kernel){
 std::vector<uint32_t> actual_vm(56816);qwen_native_services::VmReceiver receiver(actual_vm);
 receiver.reserve(0,0);receiver.drive(front);receiver.sample(front);qwen_native_services::settle(front,kernel);
}
