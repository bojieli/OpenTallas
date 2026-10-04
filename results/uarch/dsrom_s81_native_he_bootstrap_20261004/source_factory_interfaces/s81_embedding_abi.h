#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
 uint32_t reset_n,start,token,vm_base,req_ready,rsp_valid,commit_ready;
 uint64_t identity,rsp_identity;
 uint32_t rsp_macro,rsp_row,rsp_data[8];
} S81EmbeddingInput;
typedef struct {
 uint32_t req_valid,req_macro,req_row,rsp_ready,vm_valid,vm_address;
 uint64_t req_identity,vm_identity;
 uint32_t vm_data[16],busy,done,fault,committed_words;
} S81EmbeddingOutput;
void* s81_embedding_create(void);
void s81_embedding_destroy(void*);
void s81_embedding_eval(void*,const S81EmbeddingInput*,S81EmbeddingOutput*);
void s81_embedding_edge(void*,const S81EmbeddingInput*,S81EmbeddingOutput*);
uint32_t s81_embedding_vm_word(void*,uint32_t);
#ifdef __cplusplus
}
#endif
