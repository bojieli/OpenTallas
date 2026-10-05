#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* One unchanged 512x128 1R1W native macro, not the full bank service.
 * eval() receives the parent's clock LEVEL. No private edge loop/reset,
 * grant, owner, ACK or publication event is created by this interface.
 * Four instances represent a 512-bit group; enclosing RTL still owns
 * registered command/local enables and matched old-context receipts. */
typedef struct {
    uint8_t clk, read_enable, write_enable;
    uint16_t read_row, write_row;
    uint32_t data[4], mask[4];
} S81MinimumSramInput;
typedef struct { uint32_t data[4]; } S81MinimumSramOutput;
void* s81_minimum_sram_create(void);
void s81_minimum_sram_destroy(void*);
/* Returns -1 on invalid literal ports; does not clock/evaluate on refusal. */
int s81_minimum_sram_eval(void*, const S81MinimumSramInput*, S81MinimumSramOutput*);
#ifdef __cplusplus
}
#endif
