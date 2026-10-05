"""Compose the real Euclid scratch successor with source-owner issuer joins.

No new mux/engine, no provider/grant/clock substitutes, no build or simulation.
The remaining native engine, workspace producer and whole-range factory joins
are mandatory before this sourcebook can qualify a connected-token run.
"""
from tools.qwen_connected_service_install import ROOT, generate


def main():
    return generate(ROOT/'rtl/model/qwen_hbm_connected_factory_20261003',
        base=ROOT/'rtl/model/qwen_hbm_integrated_20261003/scratch',
        model_path=ROOT/'results/uarch/qwen_connected_factory_install_20261003/model.json',
        top_name='ot_gpu_qwen_hbm_integrated_scratch')


if __name__ == '__main__':
    print(main())
