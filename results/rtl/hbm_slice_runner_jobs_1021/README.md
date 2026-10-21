# Future-only slice hierarchy launch limit

Observed original source runner calls Verilator5.050 with `--hierarchical -j 8` before the later explicit `make -j1 hier_verilation`. Verilator itself starts `make -j8 hier_verilation` during that first invocation, so the later limit cannot bound the first hierarchy frontends. Actual current RoPE ep9 unit oth-ubuntu-418467-1792617308 retains its original command and objects; no intervention or restart.

The patch introduces HIER_JOBS (default1) at BOTH the first Verilator invocation and the explicit hier_verilation make. JOBS (default8) still controls only hier_build C++ jobs. bash -n and direct argv-source inspection pass. No new heavy build was launched for this runner patch; current admitted RTL build is preserved.
