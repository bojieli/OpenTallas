/* IEEE binary32 add, round to nearest even (the C golden of the RED_CARRY bench) */
#include <stdint.h>
#include <string.h>
uint32_t f32add(uint32_t a, uint32_t b) { float x, y, z; uint32_t r; memcpy(&x, &a, 4); memcpy(&y, &b, 4); z = x + y; memcpy(&r, &z, 4); return r; }
