"""Actual MX1 lowering plus retained full-shape minimum SM measurements.

Component receipts are historical source-pinned experiments, not replacement
PC bindings or whole-token latency. Never count an unresolved kernel as zero.
"""
def model():
    return dict(schema='opentallas.dshbm.mtp.kernel_enrollment.model.v1',
        replicas=32,sm_per_half=16,tp=96,macs_per_cycle='existing selected SM; no new arithmetic engine',
        memory_bytes_per_cycle={'IMEM_each_SM':8,'all32_IMEM':256},
        boundary_bits_per_launch={'CP_entry_pair':64,'SM_PC_broadcast':32*32},
        storage_bits={'IMEM_max_per_SM':16384*64,'IMEM_max_die':32*16384*64,
                      'backend_kernel_PC_templates':11*64,'backend_template_valid':11},
        SRAM_payload_protection='SECDED required in actual installed IMEM/provider, not added to control flops',
        ROM_storage='none; native690 SU program is a separate endpoint',
        routing_tracks='same actual existing32SM launch/return contract; no new physical bus',
        replica_mux_fanout='two16SM CP broadcasts; eleven-entry backend PC mux',
        area_and_slot='existing SM IMEM and MX1 backend inventory; no new area claim',
        launch_count={'VLAYER0_6columns':24,'VLAYERlater_6columns':18,
                      'VHEAD6columns':12,'SEED6columns':6,'DSTAGE0':35,
                      'DSTAGElater':30,'DHEAD5columns':10,'MARKOV':1},
        composed_latency='sum each real lowered kernel latency plus9 ordered CP/backend cycles per launch; unresolved kernels make total unknown',
        retained_measurements=dict(
            source='results/rtl/dshbm_dspark_rtl_20261003/sm_fullshape.json',
            markov_head=dict(K=256,rows=43,columns=1,cycles=560,
                operands='released weights and real embedding row21946',includes='SM matvec only; stored-logit add/argmax/collective remain outside'),
            lm_head=dict(K=5120,rows=43,columns=5,cycles=3671,
                operands='released weights, synthetic BF16 activations',includes='SM matvec only'),
            main_proj=dict(K=15360,rows=2,columns=6,cycles=449,
                operands='released weights, synthetic BF16 activations',includes='SM matvec only')),
        missing_production_kernel_images=['swapin','swapout','embed','layer','head','seed','demb','dsa','dsb','dhead','markov'],
        full_token_latency_cycles=None,native_CP_numerical_binding=False,
        physical_qualification=False)
