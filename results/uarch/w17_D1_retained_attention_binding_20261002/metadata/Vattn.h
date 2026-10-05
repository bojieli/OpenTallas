// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Primary model header
//
// This header should be included by all source files instantiating the design.
// The class here is then constructed to instantiate the design.
// See the Verilator manual for examples.

#ifndef VERILATED_VATTN_H_
#define VERILATED_VATTN_H_  // guard

#include "verilated.h"
#include "svdpi.h"

class Vattn__Syms;
class Vattn___024root;
class Vattn_ot_hdc_v41x_attn_tile__T20;


// This class is the main interface to the Verilated model
class alignas(VL_CACHE_LINE_BYTES) Vattn VL_NOT_FINAL : public VerilatedModel {
  private:
    // Symbol table holding complete model state (owned by this class)
    Vattn__Syms* const vlSymsp;

  public:

    // CONSTEXPR CAPABILITIES
    // Verilated with --trace?
    static constexpr bool traceCapable = false;

    // PORTS
    // The application code writes and reads these signals to
    // propagate new values into/out from the Verilated model.
    VL_IN8(&clk,0,0);
    VL_IN8(&rst_n,0,0);
    VL_IN8(&job_v,0,0);
    VL_OUT8(&job_ready,0,0);
    VL_IN8(&q_v,0,0);
    VL_OUT8(&q_ready,0,0);
    VL_IN8(&kv_v,0,0);
    VL_IN8(&kv_m,3,0);
    VL_OUT8(&kv_ready,0,0);
    VL_OUT8(&sc_v,0,0);
    VL_OUT8(&sc_m,3,0);
    VL_IN8(&sc_cr,0,0);
    VL_IN8(&p_v,0,0);
    VL_OUT8(&p_ready,0,0);
    VL_OUT8(&pv_v,0,0);
    VL_OUT8(&pv_c,7,0);
    VL_IN8(&pv_cr,0,0);
    VL_OUT8(&qk_iss,0,0);
    VL_OUT8(&pv_iss,0,0);
    VL_IN16(&job_t,15,0);
    VL_OUT16(&sc_row,15,0);
    VL_INW(&q_w,8191,0,256);
    VL_INW(&kv_w,16959,0,530);
    VL_OUTW(&sc_y,2047,0,64);
    VL_INW(&p_w,511,0,16);
    VL_OUTW(&pv_y,32767,0,1024);
    VL_OUTW(&pv_f,1023,0,32);
    VL_OUT64(&sc_f,63,0);

    // CELLS
    // Public to allow access to /* verilator public */ items.
    // Otherwise the application code can consider these internals.
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__0__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__1__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__2__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__3__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__4__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__5__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__6__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__7__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__8__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__9__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__10__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__11__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__12__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__13__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__14__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__15__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__16__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__17__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__18__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__19__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__20__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__21__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__22__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__23__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__24__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__25__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__26__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__27__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__28__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__29__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__30__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__31__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__32__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__33__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__34__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__35__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__36__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__37__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__38__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__39__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__40__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__41__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__42__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__43__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__44__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__45__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__46__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__47__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__48__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__49__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__50__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__51__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__52__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__53__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__54__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__55__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__56__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__57__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__58__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__59__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__60__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__61__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__62__KET____DOT__u_t;
    Vattn_ot_hdc_v41x_attn_tile__T20* const __PVT__ot_hdc_v41x_attn__DOT__g_t__BRA__63__KET____DOT__u_t;

    // Root instance pointer to allow access to model internals,
    // including inlined /* verilator public_flat_* */ items.
    Vattn___024root* const rootp;

    // CONSTRUCTORS
    /// Construct the model; called by application code
    /// If contextp is null, then the model will use the default global context
    /// If name is "", then makes a wrapper with a
    /// single model invisible with respect to DPI scope names.
    explicit Vattn(VerilatedContext* contextp, const char* name = "TOP");
    explicit Vattn(const char* name = "TOP");
    /// Destroy the model; called (often implicitly) by application code
    virtual ~Vattn();
  private:
    VL_UNCOPYABLE(Vattn);  ///< Copying not allowed

  public:
    // API METHODS
    /// Evaluate the model.  Application must call when inputs change.
    void eval() { eval_step(); }
    /// Evaluate when calling multiple units/models per time step.
    void eval_step();
    /// Evaluate at end of a timestep for tracing, when using eval_step().
    /// Application must call after all eval() and before time changes.
    void eval_end_step() {}
    /// Simulation complete, run final blocks.  Application must call on completion.
    void final();
    /// Are there scheduled events to handle?
    bool eventsPending();
    /// Returns time at next time slot. Aborts if !eventsPending()
    uint64_t nextTimeSlot();
    /// Trace signals in the model; called by application code
    void trace(VerilatedTraceBaseC* tfp, int levels, int options = 0) { contextp()->trace(tfp, levels, options); }
    /// Retrieve name of this model instance (as passed to constructor).
    const char* name() const;

    // Abstract methods from VerilatedModel
    const char* hierName() const override final;
    const char* modelName() const override final;
    unsigned threads() const override final;
    /// Prepare for cloning the model at the process level (e.g. fork in Linux)
    /// Release necessary resources. Called before cloning.
    void prepareClone() const;
    /// Re-init after cloning the model at the process level (e.g. fork in Linux)
    /// Re-allocate necessary resources. Called after cloning.
    void atClone() const;
  private:
    // Internal functions - trace registration
    void traceBaseModel(VerilatedTraceBaseC* tfp, int levels, int options);
};

#endif  // guard
