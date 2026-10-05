#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
 uint32_t reset_n,he_go,he_nout,he_k,he_wbase,he_xbase,he_obase,he_m,he_xps,he_ops;
 uint32_t he_w_data[64],he_x_q[8];
 uint32_t ssx_valid,ssx_last,ssx_x[256];
} S81NativeHeBootstrapInput;
typedef struct {
 uint32_t he_ready,he_idle,he_fault,he_w_re,he_w_addr[8],he_x_re,he_x_addr[8];
 uint32_t he_o_we,he_o_addr,he_o_mask,he_o_data[32];
 uint32_t ssx_we,ssx_addr,ssx_data,ssx_busy,ssx_fault;
} S81NativeHeBootstrapOutput;
void* s81_native_he_bootstrap_create(void);
void s81_native_he_bootstrap_destroy(void*);
// eval(clk0), rise(clk1), fall(clk0) only: parent owns all shared edge order.
void s81_native_he_bootstrap_eval(void*,const S81NativeHeBootstrapInput*,S81NativeHeBootstrapOutput*);
void s81_native_he_bootstrap_rise(void*,const S81NativeHeBootstrapInput*,S81NativeHeBootstrapOutput*);
void s81_native_he_bootstrap_fall(void*,const S81NativeHeBootstrapInput*,S81NativeHeBootstrapOutput*);
#ifdef __cplusplus
}
#endif
