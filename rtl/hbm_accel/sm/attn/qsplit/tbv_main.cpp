#include "Vtbv_sm_attn_tile_q.h"
#include "verilated.h"
int main(int argc, char** argv) { Verilated::commandArgs(argc, argv); Vtbv_sm_attn_tile_q* t = new Vtbv_sm_attn_tile_q;
  while (!Verilated::gotFinish()) { t->clk = 0; t->eval(); t->clk = 1; t->eval(); } delete t; return 0; }
