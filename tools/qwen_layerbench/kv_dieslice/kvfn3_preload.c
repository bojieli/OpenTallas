// KV-FN-3 (tools/qwen_layerbench/kv_dieslice/build_kvfn3.sh): run kvfn3_main (main_kvfn3.cpp) inside the EXISTING linked bWc_o3 model binary (Vtb_kvslice of bWc_o3_kv49fn,
// whose objects/archives were deleted).  The model's own functions are reached by trampolines (tramp.S) to
// exe load bias + nm offset; the bias is checked against the exe's own `main` passed to __libc_start_main.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
extern int kvfn3_main(int, char**, char**);
extern void kvfn3_tramp_init(uintptr_t bias);
extern const uintptr_t kvfn3_exe_main_off;
static uintptr_t bias;
static int cb(struct dl_phdr_info* i, size_t s, void* d) { (void)s; (void)d; bias = i->dlpi_addr; return 1; }
typedef int (*lsm_t)(int (*)(int, char**, char**), int, char**, void (*)(void), void (*)(void), void (*)(void), void*);
int __libc_start_main(int (*m)(int, char**, char**), int argc, char** argv, void (*init)(void), void (*fini)(void),
                      void (*rtld_fini)(void), void* stack_end) {
    lsm_t real = (lsm_t)dlsym(RTLD_NEXT, "__libc_start_main");
    dl_iterate_phdr(cb, 0);
    if ((uintptr_t)m != bias + kvfn3_exe_main_off) {
        fprintf(stderr, "KVFN3_PRELOAD FAIL exe main %p != bias %p + off %lx (wrong binary)\n", (void*)m, (void*)bias,
                (unsigned long)kvfn3_exe_main_off);
        exit(3);
    }
    kvfn3_tramp_init(bias);
    fprintf(stderr, "KVFN3_PRELOAD ok bias %p\n", (void*)bias);
    return real(kvfn3_main, argc, argv, init, fini, rtld_fini, stack_end);
}
