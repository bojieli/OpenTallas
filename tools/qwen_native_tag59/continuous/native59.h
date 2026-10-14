#ifndef OPENTALLAS_NATIVE59_H
#define OPENTALLAS_NATIVE59_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Public arrays use native rank=4*DIE+PKG. data[rank][lane] is binary32 bits.
typedef struct {
 uint32_t data[8][16]; uint64_t tag[8];
 uint8_t valid, mode, last, rst_n;
} native59_input;
typedef struct {
 uint32_t data[8][16]; uint64_t tag[8];
 uint8_t valid, last, err, credit, fault, online, drained;
 uint8_t rank[8], fault_code[8], credits[8]; uint64_t cycle;
} native59_output;
void *native59_create(void);
void native59_destroy(void *handle);
// Drive low phase, sample the signals consumed at this rising edge, then clock
// the real RTL. Every call preserves all DUT state. Reset occurs only if rst_n=0.
// An active tag with bits above58 set returns-3 without advancing the model.
int native59_tick(void *handle,const native59_input *input,native59_output *output);
#ifdef __cplusplus
}
#endif
#endif
