#!/usr/bin/env python3
"""Bounded cb21 private-buffer overlay. Source candidate, NOT a kit/LEC receipt."""
import argparse, hashlib, json
from pathlib import Path


def overlay(src):
    # Fail closed on exactly the selected root; do not edit other reset cones.
    expected="30726e6253dd6494ad0b9dd68e5b1a57a046bdbea600832066f62fdd1465576e"
    if hashlib.sha256(src.encode()).hexdigest() != expected:
        raise ValueError("unrecognized selected root source; review transformation again")
    controls = "always @(posedge buffer_clk, negedge \\u.u_buffer.u_rr.relay_q[0][0] )"
    if src.count(controls) != 5:
        raise ValueError("expected exactly five private-buffer control reset flops")
    old = r"""  always @(posedge buffer_clk, negedge rst_n)
    if (!rst_n) \u.u_buffer.u_rr.relay_q[0][0]  <= 1'h0;
    else \u.u_buffer.u_rr.relay_q[0][0]  <= \u.u_buffer.u_rr.sync_q[1] ;
  reg [1:0] _68791_;
  always @(posedge buffer_clk, negedge rst_n)
    if (!rst_n) _68791_ <= 2'h0;
    else _68791_ <= { \u.u_buffer.u_rr.sync_q[0] , 1'h1 };"""
    new = r"""  // Timed delivered-reset pipeline, not an asynchronous synchronizer.
  // Hold rst_n low for >=3 buffer clock edges before boot/transactions.
  always @(posedge buffer_clk)
    \u.u_buffer.u_rr.relay_q[0][0]  <= \u.u_buffer.u_rr.sync_q[1] ;
  reg [1:0] _68791_;
  always @(posedge buffer_clk)
    _68791_ <= { \u.u_buffer.u_rr.sync_q[0] , rst_n };"""
    if src.count(old) != 1:
        raise ValueError("selected reset pipeline source mismatch")
    out=src.replace(old, new).replace(controls,"always @(posedge buffer_clk)")
    if out.count("module ot_hgi_coll_tkm_tp192_root_core (") != 1:
        raise ValueError("selected top module mismatch")
    # Rename top AND internal modules/instances for an independent view identity.
    out=out.replace("ot_hgi_coll_tkm_tp192_root_core", "ot_hgi_coll_tkm_tp192_root_core__delivered_reset")
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument("source",type=Path);ap.add_argument("output",type=Path)
    args=ap.parse_args();src=args.source.read_text();out=overlay(src)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(out)
    report={"status":"SOURCE_ONLY_BLOCKED_LEC_NEW_ROOT_KIT", "source":str(args.source),
        "source_sha256":hashlib.sha256(src.encode()).hexdigest(),"output_sha256":hashlib.sha256(out.encode()).hexdigest(),
        "reset_release_edges":3,"min_sampled_low_edges":3,"transaction_data_cycle_delta":0,
        "changed_flops":{"ordinary_reset_pipeline":3,"private_buffer_controls_sync_reset":5},
        "unchanged":"all SRAM/data/address/root-main logic and root face shell",
        "required_gates":["constrained delivered-reset cold/warm actual root equivalence", "new selected root kit and physical signed views", "root-main timed reset recovery contract"]}
    args.output.with_suffix(".reset_contract.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))

if __name__=="__main__":main()
