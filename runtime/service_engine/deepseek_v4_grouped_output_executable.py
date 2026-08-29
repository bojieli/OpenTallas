"""Artifact-only execution for authenticated DeepSeek V4 grouped output.

The loader accepts only a closed, immutable deployment tree whose OTGO
program, official local ``wo_a`` resource, source/program contracts, logical
schedule, independent certificates, and runtime interfaces match frozen
content identities for one of the fifteen legal tensor-parallel mappings.
The service then invokes the committed grouped-output numeric implementation
on an authenticated request payload and atomically persists both grouped and
flattened output views.  Large output-rank selections are evaluated in bounded
rank chunks and reconciled into the same exact numeric result contract.

This module imports no compiler, checkpoint reader, safetensors code, expected
output, or reference model.  Request activation provenance is explicitly an
external content-hash binding only.  Execution ends before ``wo_b``, any
collective, complete attention, transformer-block or full-model execution,
RTL, timing, bandwidth, physical scheduling, NVIDIA comparison, or PPA.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
from types import MappingProxyType
from typing import Any, NoReturn
import zlib

from .grouped_output_numeric import (
    GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
    OFFICIAL_GROUP_INPUT_FEATURES,
    OFFICIAL_HEAD_DIM,
    OFFICIAL_HEADS_PER_GROUP,
    OFFICIAL_OUTPUT_RANK,
    GroupedOutputServiceNumericError,
    GroupedOutputServiceNumericResult,
    execute_grouped_output_project_selected_bf16,
    grouped_output_functional_counters,
)
from .secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    parse_canonical_json,
    publish_payload_tree,
)


MODEL_ID = "deepseek-v4-flash-0731"
MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_grouped_output_executable.v1"
DEPLOYMENT_STATUS = "official_artifact_program_packaged_execution_not_evidenced"
RESOURCE_MANIFEST_SCHEMA = "opentallas.deepseek_v4_grouped_output_resources.v1"
EXECUTION_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_contract.v1"
)
COUNTER_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_functional_counter_contract.v1"
)
COVERAGE_SCHEMA = "opentallas.deepseek_v4_grouped_output_executable_coverage.v1"
EXECUTION_REQUEST_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_request.v1"
)
EXECUTION_RESULT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_result.v1"
)
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_grouped_output_program.v1"
SOURCE_CONTRACT_SCHEMA = "opentallas.deepseek_v4_grouped_output_source.v1"
LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_grouped_output_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_logical_schedule_certificate.v1"
)
OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_official_evidence_certificate.v1"
)
COMPILER_NAME = "opentallas-deepseek-v4-grouped-output-executable-packager"
COMPILER_VERSION = "0.1.0"
MANIFEST_FILENAME = "deployment_manifest.json"
WEIGHT_PATH = "resources/layer0_wo_a_local.bf16le"
REQUEST_MANIFEST = "request_manifest.json"
REQUEST_INPUT_PATH = "input/grouped_attention_input.bf16le"
RESULT_MANIFEST = "result_manifest.json"
GROUPED_OUTPUT_PATH = "outputs/grouped_output.bf16le"
FLATTENED_OUTPUT_PATH = "outputs/flattened_output.bf16le"
MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
PROGRAM_BYTES = 88
ROW_BYTES = OFFICIAL_GROUP_INPUT_FEATURES * 2
RANK_CHUNK_SIZE = 16
SOURCE_CONTRACT_ID = (
    "f0220c70a30456e76276add36821ca7fff12c3944b2d202c2b0118ffdcd29bd9"
)
SOURCE_CONTRACT_SHA256 = (
    "975c6d662678939dcd0a170dcc9e011041f382a36cd3cd4567e792c11aef495c"
)
OFFICIAL_EVIDENCE_CERTIFICATE_ID = (
    "57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838"
)
OFFICIAL_EVIDENCE_CERTIFICATE_SHA256 = (
    "71ba1671b87f035b7fd0247904818a0dd10543e1dc53ff4529ed4ab630b3d92d"
)
COUNTER_CONTRACT_SHA256 = (
    "28c185fbef163dab5e668790c00011246365e09ffc0fe6690c5e0d30c4e97960"
)
CANONICAL_APPLICATION_ID = (
    "0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb"
)
CANONICAL_VERIFICATION_ID = (
    "b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28"
)
CHECKPOINT_LOCK_ID = (
    "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
)

CLAIM_BOUNDARY = [
    (
        "Packages and permits artifact-only execution of the exact local "
        "GROUPED_OUTPUT_PROJECT followed by terminal COMPLETE."
    ),
    (
        "The package contains complete official layer-0 wo_a BF16 row coverage "
        "for exactly one tensor-parallel world-size/rank mapping."
    ),
    (
        "The grouped output and flattened output are two views of the same "
        "group-major values; flattening is not a second arithmetic operator."
    ),
    (
        "Requests supply external already-computed grouped attention activations; "
        "the package does not claim their producer or complete sparse attention."
    ),
    (
        "Logical counters are semantic arithmetic and shape reconciliation, not "
        "cycles, latency, bandwidth, traffic, throughput, energy, area, density, "
        "routing, or PPA."
    ),
    (
        "This slice ends before wo_b, tensor-parallel collectives, complete "
        "attention, a transformer block, the full model, RTL, or any NVIDIA comparison."
    ),
]
REQUIRED_NONCLAIMS = [
    "bandwidth",
    "checkpoint_execution",
    "complete_attention",
    "cycle_accuracy",
    "cycle_latency",
    "end_to_end_model_execution",
    "full_transformer_block_execution",
    "nvidia_comparison",
    "output_b_projection",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "rtl_execution",
    "tensor_parallel_collective",
]
ENTRYPOINT = {
    "counter_contract": "interfaces/functional_counter_contract.json",
    "coverage": "evidence/execution_coverage.json",
    "execution_contract": "interfaces/execution_contract.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "official_evidence_certificate": "evidence/official_evidence_certificate.json",
    "program": "program/grouped_output.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/grouped_output.disassembly.txt",
    "resource_manifest": "resources/resource_manifest.json",
    "source_contract": "program/source_contract.json",
    "weight": WEIGHT_PATH,
}
ROLE_BY_KEY = {
    "counter_contract": "functional_counter_contract",
    "coverage": "execution_coverage",
    "execution_contract": "execution_contract",
    "execution_request_schema": "execution_request_schema",
    "execution_result_schema": "execution_result_schema",
    "logical_schedule": "logical_schedule",
    "logical_schedule_certificate": "logical_schedule_certificate",
    "official_evidence_certificate": "official_evidence_certificate",
    "program": "otgo_microcode_program",
    "program_contract": "program_contract",
    "program_disassembly": "microcode_disassembly",
    "resource_manifest": "resource_manifest",
    "source_contract": "source_contract",
    "weight": "official_layer0_wo_a_local_bf16",
}

# Fields after ``world_size rank`` are, in order: raw program, program
# contract, disassembly, logical schedule, logical certificate, execution
# contract, request schema, result schema, coverage, and official resource.
_STATIC_ROWS = """
1 0 e4722ad4e68661bb2e643cdc526c8e2572f4a319a11e0cdbdad3f3f63a1fcfb6 226a2bf6bef2ddc4fc73c0bf7bc60d51b14205bf37b702ad85d43bcbce95c7e4 2e0c6209457146c76a58b027a18a29fb5488c2df0d64324879e1f5f3f977a6bd 29fa122ef2f46ccccaba83a7ef105ebcc7bf9d2521da6d87c88b9f643ebe0fa1 c102a78961bd5d511fb9d7354fffec9f0936fcabcb2952b9b30cd8dbae23f171 055011ca2c84152e99a37fee7940c191d758bdac870f2e91e4b6367403d34a82 befa757b2360ca9918dcf981627cb6335bfc81cd4642a3226b32a194a22df6f3 f5456e0c33abad33aa41a12cb14c888d32ba4a934ea84d565e619d89112ca25e 17b4737b281c10abc27a9628c2c57bf9f6f1e9fbaa156ad1368cdff34ded43ac 8e983ca6e21f951c56e644f036d5ab255e7aa429aac3a510b9773b34c52f48a3
2 0 2686bdf4c61d05f1cb1103bf6d6d0598a5b271c885660c5eb94991f2bbc598af 723a4f5e7a9a530339ac65568a5c84c9ec3ff199ed30de1fe621f241799c74ae cba64dc7fae1d97dbc29be92947617df8eec3dbbade4dd6b15dc6deeec722611 d4faf3c9a78321887f75607f83d568359471dccf3eb422d4c9757975941a7ae4 bf9e1658788fb8f1f2b4e6f6f0337cfcc834089daa2573c4d3bb03443eca18d6 ed029477e5a6423f8371b3270017ee9074f9c3daa54a61864dac065d94f7b1f3 361b118e7a162fb4d8b4703a7b1b226ca37c08dad8379ae8dd4e3c6a1ce1f329 793474e55737765361c44b0d744c44d809f203d7a9c6a1472cee86f80ed77715 a02f3386f6977b8a5ea908fec4066011e832c3a62d9bce0f5288b2439551fdda 3d6f5ff6b1493268a914a8644e7a4f6a1f9aeb26dda0b5009c2daf473d051a06
2 1 e3dd05ba5c1f95e001ec4a296b45fbed4b7c425c7a5a083deaf51ed57ec9a2c0 902d7a70be04dfe8ed68a54b2179312ba1de6c42835d952861f4dcf0e497c369 ee6d788044a440e2a9a3af89a06cd693a1dde518a0785191f790ceb1d967d62b d9f541116e058612c665722635f30893ad41c2f2331a13be3e54f5147ee727c2 ac5044e3a4e684773eb01753fbb9f9c700babb3c5ecea8b447089aef48c76d9f 29f8af8e034ed76aa02e2ef1db2c74792e695d463e72a2764b3756c1f7061980 eaa5bf180f943d9700b113faca767c6090972e1240049bd2706c0dd6b8bc73c4 e546fe82b69c4aaa0ffd3f6c01b94ee755b2dcdb3f3d21399efdd19dee23a97c 1dc7326f521b6c6d3eb1422b384cba95fc1c1a2f3425c625568204bf419fe348 e4018706e3435505b5deeb96a123f9defde1dde0b6fa0cfe9b8496dca3905361
4 0 d6ea68b8e9542ac5d3d3991aa62678dd4ec6af854a357d307567b4cecc6dd3d3 c296fc1561cdb3d96c2907f640499540157df52e8f226de6d4da89be60655602 262a8730b6df2e1d47a402acb4f6a275620897e4f620b0806938b121699e26e6 5ab15ec32c28fe153b4c97bc0ca56e982d53eac5f46e5a3ef2833fe435883be2 caf66638e9dc8d27626baedb9640d5000c6197683adaaa44f35880655d5cfc13 04cc3cffe901e3c18d07fc8a70641b67162636a157e91d9564f049210db68203 0b4e75426584b7e47fb04310bee6115966747112b5d0ed0bd7c014efe4f19ce3 569f4ecd15a24e898acc21ad8d5e045a9de87eabaa5c788c3a8e7599988836d9 885dfb0007eb43727b35a45a8951bdb52262f13e7b7d54b11821a2a17c02fdc6 eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b
4 1 e60d60973f8de953455e13063018ee67b90c962629b3947e4785d07da770db52 99b59f46054aaf641186ca795bfc5d829f5ad30245fc4599379df70261d4c555 e0e606b7287ec159b382d9bdc7a9f35a934c5dc30fc276a82cd8a2d4abb2cef8 8777a0287ff5c639cf01b925ac4c0a78716829253c05fdd3f08cf9be57192974 5c3ebbb8d4c331835f8167ee48c15639db7bd48e6f44fb05d341316041704f0a f421066703bd7245f99bc0ba1afc86d53dcc6ded9bd30cc0ee04c7e33749e817 3e0bd121000168f085a1a0866df82543996cff895addb6dac4f4a065f3608be8 b3dc753ed1ff5ed3789a5e5ce2602db6ad83d2fe7c87ba3415be311ac9506059 797e027b6a87be03a9e542369f716ae9434e2662060d539c1ba5ca2e6e6458c3 ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016
4 2 1a9ec644f1987e04eb6f5d2f5efb34290e082d96ef5080f8303680955ad6cc1d 896c153df0dbcf9d130bb1ee0a8c2255067316a638e12bb3c639aaba6fd65a7d 00d4c00e16bd7fe31527721a2cdd8b5bf0cc05ee2ac6b8020f7f9916d7ee4908 69a7d1cd4ec53d03cfed98abb3bc9c33e8e385e3907f5ffb58110b3a1dde5294 684fcb500715b632a2a3f4c928c61ffa3fe341439b9ae53f97231f66ae88cb79 6b1667f6f0e52c6c0873d244e93f006f98b0d028be364d17a807c491c0311041 ab86d0c713fb66939e4c1263d76e74c88984c2303a2312d3e78ac3745abee5f3 285207c9a17ec58df76677337c1bb2ff69adf153bf42730f750f06ad00ac092a b6f99089ccb29fccf3884a993d999657d5702b7fc1c1035f4e882769b5d69d05 d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc
4 3 efecb94bf543b7ac0d6c6754777083814977b36b07980bb931ba4e4f62d35950 93619f9082ef571ccfc7e361228d58364c2f3a5056ed50bf991f47b5493edd7f efff5e105d343f885dae9c50d6ee3f2ebc7b328c6531f047ab7d09a6ecd15518 d17373caadba98d8aefc962d861e502908f281b3fbbe2ee1bc0446d171fe0121 20a19d7079e6b1d7dca02df1f2a44049179320f61ec478d9f0c1f37e0dcb96c1 46228a68f06973e80b426781b06546256bbbef11cbe9163dfd4346030b40f516 a793a12da98feb5ef6fd152e22ec8dcacb35d0cd6d4cd27201b36fc2d5cd92db 76293629bdb9412946afd7b6f40e3ff5e18aadbeae6f5a37856bbf27c38e5feb cea3e68933a35c9e6f5ec8447b00a7d64eda443bc143823171e47a3de656f63a 0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b
8 0 e5064a83baa985a846d4a99e866f53ec59f11909dc81664af35ee6b606d33f5f b4273fbe063158aecd35138673f08f82786b0dc66392f62dc09d9f70a8e2d897 f6c519291177d55f908e44be5b6657a0bf4fa917e6bf12cadad01399a4c5eedc 47bbca590dfba1674f4e8fd0c9d69e040567194f0abfef76f08c617bbf185b25 d715b13b7a5125081fda7ef8aad33583a0e915d0131e3da24ee3df0eefa6922e 48de27d3b4a5f637332c6903a2537e56871deb647aac68646daa42a504e5e4d9 4055c57bd5dbec713873380237c40bfdcda1ba41206e623b3eabdda89b8eb148 d57cc20c45284f08792f88d0543c351e04f6d26e60cecfd6cfc9a02c4ceb5c9b 21d950f4b5532289b50e060e652f7c009e30d52e52ab6e23b6d51190bb12a02a 60ddeeab2ee7f73bf695bea8e4a27bebb89bc5debec2bd6c8031f57b0f95091a
8 1 0be49aaf5b83e2346c3e99e850845bda8ee59dff02eeda93ecbfb81fb08c97d6 a2e4e75e933e63f299afe306e7b33747e2ec6872004dd88eeb895211d9a19c4b c3c2c57749e558deb802f3847949b39e4431ef143038d0151856a4e5fde79d0e 2d9cbf05e44942cbb96652375d8865020c9e94b68d00d5725784c1cf4efce813 3c0f70de6712028770ba0dd26f2a28852c81c63b7d7f2c3cf7f5d747ed933ab3 1a3bc0105b1b76398cecaaf9b7f8779e275f61ad44354bb8a1e3964005a8e304 03f59663e832c1030fdd9f39b4ddf88458fda010ea1aed7e48a378b411023f81 0820e8dae7d40e224ab7508a549f137d8efe8c19c06a8954e1b9e1650ad45e29 28fafe361809f18edd8d41b931bb7d4c59a265f8baf92e8988f9587b8ac90779 fbd7d95f857d7820675a25fb24280e538d924a8ff2a93d66534b1c4ca78e773d
8 2 e38d32097a66bb23cb6c4215a7bd5fd2e31d301c5db57798b606e42636ca5b08 5ffcb6eb852e7198b0da6b2f3720279c4106b1f524a824deeded326f7193e078 b872fd59f204b656052be0fb01d8b3e1a23055a1cc8832181b03af66bed5b3d2 82a14b38d4a0bda2f0ef0b7248c508b831674f0e1503b929425c42d0e1297cd8 714c754f6e28603a814a0312e67f3a2acab5b4cf3f67255a66b24dd7b56ad012 f52a08c619e19eaadcfa917de59305bfc530f80e25c0b1d5d9a0992f466248e4 a38ef8e517dd2293aa73df0a79d625b66da2a5446c5580d7e1a2c99e7494fa9a d273d5f57e9aaf8e2f10d9e881dd0a58f5260954e972045f3f5cd214c01a83f2 77e17fddecb458d16813d3cfd53ee956db2b559c84416af4daee8122679ecd9e 7f015b095b13a6475d7604f7e0a4f88d6ceae6c6e43719e70a71387139fbb291
8 3 613c3f2bbecc3988989844da5e5b3a4b5838e3d6b8bd02737c991e5263be9c49 4d4c6b3618e2654cae72801d6740680d71f7150e3f4a937b92328362a114c33a 3fdfa2e4ba6736bad0038007d86b2c340b1a952eac3b01e192c1ebc0b88856c2 35524ed272968e3669db678381fce43e0925716ab48112f29a2b5f0f07d614a2 4ead6d8e5db20af429fed23af77478f04c32de3ec987edf30f8a153ec769c14f 8aebedb79c78c5c37f06614b5a1c53ee2d1130a2ddf119f60f758935c2fe46ea b79b90c341da7395dd6a67a261f67d6de983c9b8488f7bc9b15834596dfaf137 0b3bbbfe7f31b0edab7ce9c26d0084de84a7ac35e2bc01a2baa845e3beb45f92 ea0ad2b898e0f03b51b356ee6461d5c874dbe5c12cb576e1c8a22135ed0ac9f8 864a89722a72a8c5491248540fbb55788cbc21906d83941f346faa2f65ace46f
8 4 b889d0ae2d1374ac203aaabdb9cab4cde4c22048207c180907a9f44a5179b482 d6e1a93a96169cf7371d4b7bc37c66b44ace5d2b022972cde697b68833a21d20 d1be1cec7c580b5e43697a1139514427ca5729e21db8463befd755daaf326138 7e64018ab2e43e6df7ff5642546473e35e36c6c852ca5c0613a108c771faf397 0e44b5ff39d3d6bc1a95ac40cd5b946df6ee796e11d4872900047aab7a66a239 88f7223f6f6ffdc3951d8c27adeb09ed802bc99dc50d604410dc60e1ea24f260 d19c702e7c4b8a3c78d71652c9b6b004f66f1240ce0b4319a5fd89f322ebabf9 eaae858b9a89f738bc108a35da91d910f866dd1c94618ab6a20caa638eb819ba 7f68f59ed93e3addda6c015bc373f5d033f0b6d24c062d77309f879a6997fb8f 841368c516a3a4d88fe0a21779f1eafa5a7d525e818f048319fd666cbc343a27
8 5 7da745ed158322b0cfdecdf2824b9e05d45a462341675c2296a62623e5dcb7da cdba19f5ffa8ccfb1f6c364c5d49c0b3a3e9061202b4f1a8bda68eebdd5c94ae 525dc00740071f8cf4a83400dec1384f5894a4604c5260d1cb86ce58104fe3e8 3b67bd531fd00abaa620fd396b7145ccbf3fa6d9fe542349172725737ac8cfa8 affdbdc87c8929e3f3bccfa79ec3b4639cdee8463497fa8041acd23d73ca657d f2f4e0b5701a7d2f2395fedddc564b1de0661afca640617a71ec2d5d9ca87af7 2e985fea9ac554d78f14f14b9db133275691b35255787aefde9ed61afebc6a62 52e2081dda747d8fbbc6dc9e324cd8e2ef70d397c42f6ce4bfa81cfaf0e4b825 234ef2d6dc9f497b4d117959788516d58117756e73c8dd966b63e8ac7b3ef8da a4e0ccbc47c2ba43939ce139fc0be8ee8a277c0b7f8514707da5108da7ba59f1
8 6 69fb674fc5b192e946fcbae945c0bae2aadafb445e9e3ec71b463e43525bda88 ca0e9384516cffe7bfdcf2d5e160adcf2105f1e7b21335e65c7539c1308d0367 f27334b7f1b197cff858856d4a9a4fd6be336735c23e7dc67abf0c47e59b83c7 10adf26de7439317017b5f40e58b2b63d078341dbdd7d4f5f9d3ce473e50ed01 26e204b2f39128bd792bc3efba59da312870861a7de5563f7a9603faa3bf5beb e1d9347dd09493e9ad042317959f398ca52416d94123d51aeb7049dae4a84a24 8861d66885321cd16bc9f8c8f043a479f53267856e317592069b278d638cef8f 86f8c5e5be407941968492f5234074f3fbbfea991077c6337171315b8ae00e47 605618410bc18f5283cf1a39db6a3a4b367c21c50f9c4349cc0d33b726810045 81fbf8df07170139e5255dcad1ea95dbde1cfd9dbc0f007eae188362c99a2f67
8 7 e2cb1394d2075866e0327ec43324899ff5ec30f5d35f87f45ddc1472fa7603a2 6bf07b82dac04be7f17a59f527b62ee8c3e1c6610172e0c7fe3154ace303e1a3 4f23995f76f08c88de07cc33a0eb65e3fdd7f5be1a876dc1b30cf9426979892f ce6319525ca36aef285da900e22433a80cf2a0ce7b82d0968428a73bfa5b1e77 58f8ed2e9a4cac8124b544d13c7825f806f9040a46b95fb7c1040a278e6cbb41 c6491db5905010ec39b7c03d4ddd748c8b434690f36fd7706642fe178ed1a622 a5f9552d01def06e955a33b265142878c8ede50caeb60496a7f0e74a574a27e5 68f9894833c5d198df8be12787c45bcfdf083a8836d88c358b5d1d491b61e386 be22f5fd7c36ed99848ddcfd9f0cd23614e0c34d5911e8d7fe00cb2b3b55503e 16f7db1662c18feda343cfabb951807e06b6de746c05f218f8e72befb6831768
"""

_STATIC_NAMES = (
    "program",
    "program_contract",
    "program_disassembly",
    "logical_schedule",
    "logical_schedule_certificate",
    "execution_contract",
    "execution_request_schema",
    "execution_result_schema",
    "coverage",
    "weight",
)
_STATIC_IDENTITIES: dict[tuple[int, int], dict[str, str]] = {}
for _raw_row in _STATIC_ROWS.splitlines():
    if not _raw_row:
        continue
    _parts = _raw_row.split()
    if len(_parts) != 2 + len(_STATIC_NAMES):  # pragma: no cover - frozen table
        raise RuntimeError("grouped-output frozen identity row is malformed")
    _key = (int(_parts[0]), int(_parts[1]))
    _STATIC_IDENTITIES[_key] = dict(zip(_STATIC_NAMES, _parts[2:], strict=True))


class DeepSeekV4GroupedOutputExecutableServiceError(RuntimeError):
    """Raised when package authority or one command must be poisoned."""


@dataclass(frozen=True)
class GroupedOutputExecutableArtifactRecord:
    relative_path: str
    role: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class GroupedOutputInstruction:
    opcode: int
    opcode_name: str
    destinations: tuple[int, int]
    source: int
    resource: int
    immediates: tuple[int, int, int, int]


def _poison(message: str, cause: BaseException | None = None) -> NoReturn:
    if cause is None:
        raise DeepSeekV4GroupedOutputExecutableServiceError(message)
    raise DeepSeekV4GroupedOutputExecutableServiceError(message) from cause


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(payload: bytes, label: str, maximum: int = 2 * 1024 * 1024) -> dict[str, Any]:
    try:
        value = parse_canonical_json(payload, label=label, maximum_bytes=maximum)
    except SecureArtifactError as exc:
        _poison(f"cannot parse {label}: {exc}", exc)
    if type(value) is not dict:
        _poison(f"{label} is not a JSON object")
    return value


def _equal(left: object, right: object) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except SecureArtifactError:
        return False


def _exact(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _poison(f"{label} is not an exact object")
    observed = set(value)
    if observed != keys:
        _poison(
            f"{label} fields differ: missing={sorted(keys - observed)}, "
            f"unknown={sorted(observed - keys)}"
        )
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        type(value) is not int
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        _poison(f"{label} is outside its exact integer bound")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _poison(f"{label} is not a lowercase SHA-256")
    return value


def _derived_id(value: Mapping[str, Any], field: str, label: str) -> str:
    identity = _digest(value.get(field), f"{label} {field}")
    body = {key: value[key] for key in value if key != field}
    if _sha256(canonical_json_bytes(body)) != identity:
        _poison(f"{label} {field} does not bind its canonical body")
    return identity


def _topology(world_size: int, rank: int) -> dict[str, Any]:
    if world_size not in (1, 2, 4, 8) or not 0 <= rank < world_size:
        _poison("tensor-parallel topology is unsupported")
    local_groups = 8 // world_size
    group_start = rank * local_groups
    return {
        "global_group_range": [group_start, group_start + local_groups],
        "global_row_range": [
            group_start * OFFICIAL_OUTPUT_RANK,
            (group_start + local_groups) * OFFICIAL_OUTPUT_RANK,
        ],
        "local_group_count": local_groups,
        "rank": rank,
        "world_size": world_size,
    }


def _artifact_record(path: str, role: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _expected_resource_segments(world_size: int, rank: int) -> list[dict[str, Any]]:
    topology = _topology(world_size, rank)
    group_start, group_stop = topology["global_group_range"]
    segments: list[dict[str, Any]] = []
    if world_size <= 4:
        assignment_start = group_start // 2
        assignment_stop = group_stop // 2
        for assignment_rank in range(assignment_start, assignment_stop):
            global_row_start = assignment_rank * 2 * OFFICIAL_OUTPUT_RANK
            global_row_stop = global_row_start + 2 * OFFICIAL_OUTPUT_RANK
            segments.append(
                {
                    "assignment_rank": assignment_rank,
                    "byte_offset": 0,
                    "content_sha256": _STATIC_IDENTITIES[(4, assignment_rank)][
                        "weight"
                    ],
                    "global_row_range": [global_row_start, global_row_stop],
                    "path": (
                        f"ranks/rank-{assignment_rank:03d}/"
                        "layers.0.attn.wo_a.weight.bin"
                    ),
                    "size_bytes": (global_row_stop - global_row_start) * ROW_BYTES,
                }
            )
        return segments

    global_group = group_start
    assignment_rank = global_group // 2
    global_row_start = global_group * OFFICIAL_OUTPUT_RANK
    global_row_stop = global_row_start + OFFICIAL_OUTPUT_RANK
    return [
        {
            "assignment_rank": assignment_rank,
            "byte_offset": (global_group % 2) * OFFICIAL_OUTPUT_RANK * ROW_BYTES,
            "content_sha256": _STATIC_IDENTITIES[(8, global_group)]["weight"],
            "global_row_range": [global_row_start, global_row_stop],
            "path": (
                f"ranks/rank-{assignment_rank:03d}/"
                "layers.0.attn.wo_a.weight.bin"
            ),
            "size_bytes": (global_row_stop - global_row_start) * ROW_BYTES,
        }
    ]


def _decode_program(
    payload: bytes,
    world_size: int,
    rank: int,
) -> tuple[GroupedOutputInstruction, ...]:
    header = struct.Struct("<4sBBHII")
    record = struct.Struct("<BBH8I")
    if type(payload) is not bytes or len(payload) != PROGRAM_BYTES:
        _poison("OTGO program byte length differs")
    magic, major, minor, record_size, count, crc = header.unpack_from(payload)
    if (magic, major, minor, record_size, count) != (b"OTGO", 1, 0, 36, 2):
        _poison("OTGO program header differs")
    body = payload[header.size :]
    if zlib.crc32(body) & 0xFFFFFFFF != crc:
        _poison("OTGO program CRC32 differs")
    rows = [record.unpack_from(body, index * record.size) for index in range(2)]
    local_groups = 8 // world_size
    expected = (
        GroupedOutputInstruction(
            opcode=0x30,
            opcode_name="GROUPED_OUTPUT_PROJECT",
            destinations=(1, 2),
            source=0,
            resource=0,
            immediates=(world_size, rank, local_groups, OFFICIAL_OUTPUT_RANK),
        ),
        GroupedOutputInstruction(
            opcode=0xFF,
            opcode_name="COMPLETE",
            destinations=(0xFFFFFFFF, 0xFFFFFFFF),
            source=0xFFFFFFFF,
            resource=0xFFFFFFFF,
            immediates=(0, 0, 0, 0),
        ),
    )
    observed: list[GroupedOutputInstruction] = []
    for index, row in enumerate(rows):
        opcode, flags, reserved, *operands = row
        if flags != 0 or reserved != 0:
            _poison(f"OTGO instruction {index} has control bits")
        if opcode not in {0x30, 0xFF}:
            _poison(f"OTGO instruction {index} has unknown opcode")
        observed.append(
            GroupedOutputInstruction(
                opcode=opcode,
                opcode_name=(
                    "GROUPED_OUTPUT_PROJECT" if opcode == 0x30 else "COMPLETE"
                ),
                destinations=(operands[0], operands[1]),
                source=operands[2],
                resource=operands[3],
                immediates=tuple(operands[4:8]),
            )
        )
    if tuple(observed) != expected:
        _poison("OTGO program operands differ from exact topology program")
    return expected


def _verify_bf16(payload: bytes, label: str) -> None:
    if len(payload) % 2:
        _poison(f"{label} ends within a BF16 element")
    for index, (code,) in enumerate(struct.iter_unpack("<H", payload)):
        if code & 0x7F80 == 0x7F80:
            _poison(f"{label} has nonfinite BF16 at element {index}")


def _verify_static_artifacts(
    payloads: Mapping[str, bytes],
    world_size: int,
    rank: int,
) -> None:
    identities = _STATIC_IDENTITIES[(world_size, rank)]
    for key in _STATIC_NAMES:
        path = ENTRYPOINT[key]
        if _sha256(payloads[path]) != identities[key]:
            _poison(f"packaged {key} content identity differs")
    if _sha256(payloads[ENTRYPOINT["source_contract"]]) != SOURCE_CONTRACT_SHA256:
        _poison("packaged source contract content identity differs")
    if _sha256(payloads[ENTRYPOINT["official_evidence_certificate"]]) != (
        OFFICIAL_EVIDENCE_CERTIFICATE_SHA256
    ):
        _poison("packaged official evidence certificate content identity differs")
    if _sha256(payloads[ENTRYPOINT["counter_contract"]]) != (
        COUNTER_CONTRACT_SHA256
    ):
        _poison("packaged functional counter contract identity differs")


def _verify_resource_manifest(
    value: object,
    weight_payload: bytes,
    world_size: int,
    rank: int,
) -> str:
    manifest = _exact(
        value,
        {
            "application_id",
            "checkpoint_lock_id",
            "resource_manifest_id",
            "resources",
            "schema",
            "source_contract_id",
            "status",
            "topology",
            "verification_id",
        },
        "resource manifest",
    )
    resource_id = _derived_id(manifest, "resource_manifest_id", "resource manifest")
    resources = manifest.get("resources")
    if type(resources) is not list or len(resources) != 1:
        _poison("resource manifest must contain exactly one resource")
    resource = _exact(
        resources[0],
        {
            "canonical_application_id",
            "dtype",
            "encoding",
            "global_group_range",
            "global_row_range",
            "path",
            "resource_id",
            "resource_name",
            "role",
            "segments",
            "sha256",
            "shape",
            "size_bytes",
        },
        "local wo_a resource",
    )
    topology = _topology(world_size, rank)
    local_groups = 8 // world_size
    expected_fixed = {
        "application_id": CANONICAL_APPLICATION_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "schema": RESOURCE_MANIFEST_SCHEMA,
        "source_contract_id": SOURCE_CONTRACT_ID,
        "status": "complete_official_local_wo_a_resource",
        "topology": topology,
        "verification_id": CANONICAL_VERIFICATION_ID,
    }
    for key, expected in expected_fixed.items():
        if not _equal(manifest.get(key), expected):
            _poison(f"resource manifest {key} differs")
    expected_resource = {
        "canonical_application_id": CANONICAL_APPLICATION_ID,
        "dtype": "BF16",
        "encoding": "bfloat16_little_endian",
        "global_group_range": topology["global_group_range"],
        "global_row_range": topology["global_row_range"],
        "path": WEIGHT_PATH,
        "resource_id": 0,
        "resource_name": "LAYER0_WO_A_LOCAL_BF16",
        "role": "layers.0.attn.wo_a.weight.local",
        "sha256": _STATIC_IDENTITIES[(world_size, rank)]["weight"],
        "shape": [local_groups * 1024, 4096],
        "size_bytes": 67_108_864 // world_size,
    }
    for key, expected in expected_resource.items():
        if not _equal(resource.get(key), expected):
            _poison(f"local wo_a resource {key} differs")
    if not _equal(
        resource.get("segments"),
        _expected_resource_segments(world_size, rank),
    ):
        _poison("local wo_a source segments differ from frozen official assignments")
    if _sha256(weight_payload) != resource["sha256"]:
        _poison("local wo_a payload differs from resource manifest")
    return resource_id


def _verify_packaged_json(
    payloads: Mapping[str, bytes],
    world_size: int,
    rank: int,
) -> tuple[str, str, str]:
    source = _json(payloads[ENTRYPOINT["source_contract"]], "source contract")
    if (
        source.get("schema") != SOURCE_CONTRACT_SCHEMA
        or _derived_id(source, "source_contract_id", "source contract")
        != SOURCE_CONTRACT_ID
    ):
        _poison("source contract identity differs")
    program_contract = _json(
        payloads[ENTRYPOINT["program_contract"]],
        "program contract",
    )
    if program_contract.get("schema") != PROGRAM_CONTRACT_SCHEMA:
        _poison("program contract schema differs")
    program_contract_id = _derived_id(
        program_contract,
        "contract_id",
        "program contract",
    )
    if program_contract.get("program_sha256") != (
        _STATIC_IDENTITIES[(world_size, rank)]["program"]
    ):
        _poison("program contract byte identity differs")

    schedule = _json(payloads[ENTRYPOINT["logical_schedule"]], "logical schedule")
    if (
        schedule.get("schema") != LOGICAL_SCHEDULE_SCHEMA
        or schedule.get("status") != "logical_schedule_only"
        or not _equal(schedule.get("topology"), _topology(world_size, rank))
    ):
        _poison("logical schedule identity or topology differs")
    schedule_id = _derived_id(schedule, "schedule_id", "logical schedule")
    identity = schedule.get("identity")
    if (
        type(identity) is not dict
        or identity.get("program_sha256")
        != _STATIC_IDENTITIES[(world_size, rank)]["program"]
        or identity.get("program_contract_id") != program_contract_id
        or identity.get("source_contract_id") != SOURCE_CONTRACT_ID
    ):
        _poison("logical schedule program/source binding differs")
    certificate = _json(
        payloads[ENTRYPOINT["logical_schedule_certificate"]],
        "logical schedule certificate",
    )
    if (
        certificate.get("schema") != LOGICAL_CERTIFICATE_SCHEMA
        or certificate.get("status") != "pass"
        or certificate.get("schedule_id") != schedule_id
        or certificate.get("program_contract_id") != program_contract_id
        or certificate.get("source_contract_id") != SOURCE_CONTRACT_ID
    ):
        _poison("logical schedule certificate binding differs")
    certificate_id = _derived_id(
        certificate,
        "certificate_id",
        "logical schedule certificate",
    )
    evidence = _json(
        payloads[ENTRYPOINT["official_evidence_certificate"]],
        "official evidence certificate",
    )
    if (
        evidence.get("schema") != OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA
        or evidence.get("status") != "pass"
        or _derived_id(evidence, "certificate_id", "official evidence certificate")
        != OFFICIAL_EVIDENCE_CERTIFICATE_ID
        or evidence.get("source_contract_id") != SOURCE_CONTRACT_ID
    ):
        _poison("official evidence certificate binding differs")
    return program_contract_id, schedule_id, certificate_id


class DeepSeekV4GroupedOutputExecutableDeployment:
    """Held immutable deployment authority and decoded official resource."""

    def __init__(
        self,
        *,
        root: SecureDirectory,
        build_id: str,
        world_size: int,
        rank: int,
        artifacts: tuple[GroupedOutputExecutableArtifactRecord, ...],
        instructions: tuple[GroupedOutputInstruction, ...],
        program_sha256: str,
        program_contract_id: str,
        resource_manifest_id: str,
        resource_sha256: str,
        schedule_id: str,
        schedule_certificate_id: str,
        weight_payload: bytes,
    ):
        self.root = root
        self.build_id = build_id
        self.world_size = world_size
        self.rank = rank
        self.local_group_count = 8 // world_size
        self.artifacts = artifacts
        self.instructions = instructions
        self.program_sha256 = program_sha256
        self.program_contract_id = program_contract_id
        self.resource_manifest_id = resource_manifest_id
        self.resource_sha256 = resource_sha256
        self.schedule_id = schedule_id
        self.schedule_certificate_id = schedule_certificate_id
        self.weight_payload = weight_payload
        self._closed = False
        self._guarded_memory_identity = self._memory_identity()

    def __enter__(self) -> DeepSeekV4GroupedOutputExecutableDeployment:
        self.verify()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self.root.close()
        self._closed = True

    def _memory_identity(self) -> str:
        body = {
            "artifacts": [
                {
                    "path": item.relative_path,
                    "role": item.role,
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                }
                for item in self.artifacts
            ],
            "build_id": self.build_id,
            "instructions": [
                {
                    "destinations": list(item.destinations),
                    "immediates": list(item.immediates),
                    "opcode": item.opcode,
                    "opcode_name": item.opcode_name,
                    "resource": item.resource,
                    "source": item.source,
                }
                for item in self.instructions
            ],
            "local_group_count": self.local_group_count,
            "program_contract_id": self.program_contract_id,
            "program_sha256": self.program_sha256,
            "rank": self.rank,
            "resource_manifest_id": self.resource_manifest_id,
            "resource_sha256": self.resource_sha256,
            "schedule_certificate_id": self.schedule_certificate_id,
            "schedule_id": self.schedule_id,
            "weight_sha256": _sha256(self.weight_payload),
            "world_size": self.world_size,
        }
        return _sha256(canonical_json_bytes(body))

    def verify(self) -> None:
        if self._closed:
            _poison("grouped-output deployment is closed")
        if self._memory_identity() != self._guarded_memory_identity:
            _poison("grouped-output deployment in-memory snapshot differs")
        identities = _STATIC_IDENTITIES.get((self.world_size, self.rank))
        if (
            identities is None
            or self.program_sha256 != identities["program"]
            or self.resource_sha256 != identities["weight"]
            or _sha256(self.weight_payload) != identities["weight"]
        ):
            _poison("grouped-output deployment frozen identities differ")
        try:
            self.root.verify()
        except SecureArtifactError as exc:
            _poison(f"grouped-output deployment changed while held: {exc}", exc)


def _load_deployment(
    deployment_dir: Path,
) -> DeepSeekV4GroupedOutputExecutableDeployment:
    root = SecureDirectory(
        Path(deployment_dir),
        label="DeepSeek V4 grouped-output executable deployment",
    )
    try:
        manifest_file = root.open_file(
            MANIFEST_FILENAME,
            label="grouped-output deployment manifest",
            maximum_size=512 * 1024,
        )
        manifest_payload = manifest_file.read_bytes(
            label="grouped-output deployment manifest",
            maximum_bytes=512 * 1024,
        )
        manifest = _json(manifest_payload, "grouped-output deployment manifest")
        _exact(
            manifest,
            {
                "artifacts",
                "build_id",
                "claim_boundary",
                "compiler",
                "entrypoint",
                "evidence",
                "model_id",
                "numeric_profile",
                "repository",
                "revision",
                "schema",
                "status",
                "topology",
            },
            "grouped-output deployment manifest",
        )
        topology = _exact(
            manifest.get("topology"),
            {
                "global_group_range",
                "global_row_range",
                "local_group_count",
                "rank",
                "world_size",
            },
            "deployment topology",
        )
        world_size = _integer(topology.get("world_size"), "world_size", minimum=1)
        rank = _integer(topology.get("rank"), "rank")
        if (world_size, rank) not in _STATIC_IDENTITIES or not _equal(
            topology,
            _topology(world_size, rank),
        ):
            _poison("deployment topology differs from a legal frozen mapping")
        fixed = {
            "claim_boundary": CLAIM_BOUNDARY,
            "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
            "entrypoint": ENTRYPOINT,
            "evidence": {
                "application_id": CANONICAL_APPLICATION_ID,
                "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
                "official_evidence_certificate_id": (
                    OFFICIAL_EVIDENCE_CERTIFICATE_ID
                ),
                "source_contract_id": SOURCE_CONTRACT_ID,
                "verification_id": CANONICAL_VERIFICATION_ID,
            },
            "model_id": MODEL_ID,
            "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
            "repository": MODEL_REPOSITORY,
            "revision": MODEL_REVISION,
            "schema": DEPLOYMENT_SCHEMA,
            "status": DEPLOYMENT_STATUS,
        }
        for key, expected in fixed.items():
            if not _equal(manifest.get(key), expected):
                _poison(f"deployment {key} differs")
        build_id = _derived_id(manifest, "build_id", "deployment manifest")

        expected_files = {MANIFEST_FILENAME, *ENTRYPOINT.values()}
        expected_directories = {
            parent.as_posix()
            for path in expected_files
            for parent in Path(path).parents
            if parent != Path(".")
        }
        files, directories = root.enumerate_tree(maximum_depth=4, maximum_entries=64)
        if files != expected_files or directories != expected_directories:
            _poison("deployment tree closure differs")
        resource_bytes = 67_108_864 // world_size
        payloads: dict[str, bytes] = {}
        for path in sorted(ENTRYPOINT.values()):
            exact_size = resource_bytes if path == WEIGHT_PATH else None
            maximum = resource_bytes if exact_size is not None else 2 * 1024 * 1024
            source = root.open_file(
                path,
                label=f"grouped-output artifact {path!r}",
                minimum_size=0,
                maximum_size=maximum,
                exact_size=exact_size,
            )
            payloads[path] = source.read_bytes(
                label=f"grouped-output artifact {path!r}",
                maximum_bytes=max(1, maximum),
            )
        expected_artifacts = [
            _artifact_record(
                ENTRYPOINT[key],
                ROLE_BY_KEY[key],
                payloads[ENTRYPOINT[key]],
            )
            for key in sorted(ENTRYPOINT)
        ]
        if not _equal(manifest.get("artifacts"), expected_artifacts):
            _poison("deployment artifact table differs from held files")
        _verify_static_artifacts(payloads, world_size, rank)
        weight = payloads[WEIGHT_PATH]
        _verify_bf16(weight, "official local wo_a")
        resource_manifest = _json(
            payloads[ENTRYPOINT["resource_manifest"]],
            "resource manifest",
        )
        resource_manifest_id = _verify_resource_manifest(
            resource_manifest,
            weight,
            world_size,
            rank,
        )
        instructions = _decode_program(
            payloads[ENTRYPOINT["program"]],
            world_size,
            rank,
        )
        program_contract_id, schedule_id, certificate_id = _verify_packaged_json(
            payloads,
            world_size,
            rank,
        )
        root.verify()
        artifacts = tuple(
            GroupedOutputExecutableArtifactRecord(
                relative_path=record["path"],
                role=record["role"],
                sha256=record["sha256"],
                size_bytes=record["size_bytes"],
            )
            for record in expected_artifacts
        )
        return DeepSeekV4GroupedOutputExecutableDeployment(
            root=root,
            build_id=build_id,
            world_size=world_size,
            rank=rank,
            artifacts=artifacts,
            instructions=instructions,
            program_sha256=_STATIC_IDENTITIES[(world_size, rank)]["program"],
            program_contract_id=program_contract_id,
            resource_manifest_id=resource_manifest_id,
            resource_sha256=_STATIC_IDENTITIES[(world_size, rank)]["weight"],
            schedule_id=schedule_id,
            schedule_certificate_id=certificate_id,
            weight_payload=weight,
        )
    except Exception:
        root.close()
        raise


def load_deepseek_v4_grouped_output_executable_deployment(
    deployment_dir: Path,
) -> DeepSeekV4GroupedOutputExecutableDeployment:
    """Load and hold one exact artifact-only deployment."""

    try:
        return _load_deployment(Path(deployment_dir))
    except DeepSeekV4GroupedOutputExecutableServiceError:
        raise
    except Exception as exc:
        _poison(f"cannot load grouped-output deployment: {exc}", exc)


def _selected_ranks(value: object) -> tuple[int, ...]:
    if type(value) not in {list, tuple}:
        _poison("selected_output_ranks must be an exact list or tuple")
    ranks = tuple(
        _integer(
            item,
            f"selected_output_ranks[{index}]",
            maximum=OFFICIAL_OUTPUT_RANK - 1,
        )
        for index, item in enumerate(value)
    )
    if not ranks or ranks != tuple(sorted(set(ranks))):
        _poison("selected_output_ranks must be nonempty, unique, and increasing")
    return ranks


def _validate_input_binding(value: object) -> dict[str, Any]:
    binding = _exact(
        value,
        {
            "kind",
            "producer_id",
            "producer_schema",
            "source_byte_offset",
            "source_content_sha256",
        },
        "input binding",
    )
    if binding.get("kind") != "external_content_hash_binding_only":
        _poison("input binding kind differs")
    _digest(binding.get("producer_id"), "input producer_id")
    _digest(binding.get("source_content_sha256"), "input source content SHA-256")
    _integer(binding.get("source_byte_offset"), "input source byte offset")
    producer_schema = binding.get("producer_schema")
    if (
        type(producer_schema) is not str
        or not 1 <= len(producer_schema) <= 256
        or any(ord(character) < 0x20 for character in producer_schema)
    ):
        _poison("input producer_schema is invalid")
    return dict(binding)


def build_deepseek_v4_grouped_output_execution_request(
    deployment_dir: Path,
    output_dir: Path,
    attention_bf16_payload: bytes,
    *,
    batch_count: int,
    sequence_length: int,
    selected_output_ranks: object,
    input_binding: object,
) -> dict[str, Any]:
    """Atomically publish one hash-bound external-activation request."""

    with load_deepseek_v4_grouped_output_executable_deployment(
        deployment_dir
    ) as deployment:
        batch_count = _integer(
            batch_count,
            "batch_count",
            minimum=1,
            maximum=MAX_TOKEN_COUNT,
        )
        sequence_length = _integer(
            sequence_length,
            "sequence_length",
            minimum=1,
            maximum=MAX_TOKEN_COUNT,
        )
        token_count = batch_count * sequence_length
        if not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT:
            _poison("batch_count*sequence_length must be in [1, 4]")
        if type(attention_bf16_payload) is not bytes:
            _poison("attention input must be exact bytes")
        local_heads = deployment.local_group_count * OFFICIAL_HEADS_PER_GROUP
        expected_size = token_count * local_heads * OFFICIAL_HEAD_DIM * 2
        if len(attention_bf16_payload) != expected_size:
            _poison(
                f"attention input has {len(attention_bf16_payload)} bytes, "
                f"expected {expected_size}"
            )
        _verify_bf16(attention_bf16_payload, "grouped attention input")
        selected = _selected_ranks(selected_output_ranks)
        binding = _validate_input_binding(input_binding)
        input_descriptor = {
            "dtype": "BF16",
            "encoding": "bfloat16_little_endian",
            "path": REQUEST_INPUT_PATH,
            "rank": 4,
            "sha256": _sha256(attention_bf16_payload),
            "shape": [
                batch_count,
                sequence_length,
                local_heads,
                OFFICIAL_HEAD_DIM,
            ],
            "size_bytes": len(attention_bf16_payload),
        }
        body = {
            "build_id": deployment.build_id,
            "input": input_descriptor,
            "input_binding": binding,
            "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
            "program_sha256": deployment.program_sha256,
            "schema": EXECUTION_REQUEST_SCHEMA,
            "selected_output_ranks": list(selected),
            "status": "ready",
            "topology": _topology(deployment.world_size, deployment.rank),
        }
        manifest = {**body, "request_id": _sha256(canonical_json_bytes(body))}
        payloads = {
            REQUEST_INPUT_PATH: attention_bf16_payload,
            REQUEST_MANIFEST: canonical_json_bytes(manifest),
        }
        deployment.verify()
    try:
        publish_payload_tree(
            Path(output_dir),
            payloads=payloads,
            directories=("input",),
            label="DeepSeek V4 grouped-output execution request",
            maximum_depth=2,
            maximum_entries=4,
        )
    except SecureArtifactError as exc:
        _poison(f"cannot publish grouped-output request: {exc}", exc)
    return manifest


@dataclass
class _ExecutionRequest:
    root: SecureDirectory
    manifest: dict[str, Any]
    manifest_sha256: str
    request_id: str
    batch_count: int
    sequence_length: int
    token_count: int
    selected_output_ranks: tuple[int, ...]
    attention: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]

    def close(self) -> None:
        self.root.close()


def _decode_attention(
    payload: bytes,
    batch_count: int,
    sequence_length: int,
    local_heads: int,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    codes = tuple(code for (code,) in struct.iter_unpack("<H", payload))
    cursor = 0
    batches: list[tuple[tuple[tuple[int, ...], ...], ...]] = []
    for _ in range(batch_count):
        sequence: list[tuple[tuple[int, ...], ...]] = []
        for _ in range(sequence_length):
            heads: list[tuple[int, ...]] = []
            for _ in range(local_heads):
                stop = cursor + OFFICIAL_HEAD_DIM
                heads.append(codes[cursor:stop])
                cursor = stop
            sequence.append(tuple(heads))
        batches.append(tuple(sequence))
    if cursor != len(codes):  # pragma: no cover - exact size checked first
        _poison("attention decoder did not consume the complete payload")
    return tuple(batches)


def _load_request(
    deployment: DeepSeekV4GroupedOutputExecutableDeployment,
    request_manifest_path: Path,
) -> _ExecutionRequest:
    path = Path(request_manifest_path)
    if path.name != REQUEST_MANIFEST:
        _poison(f"request manifest must be named {REQUEST_MANIFEST!r}")
    try:
        root = SecureDirectory(path.parent, label="grouped-output execution request")
    except SecureArtifactError as exc:
        _poison(f"cannot hold grouped-output execution request: {exc}", exc)
    try:
        files, directories = root.enumerate_tree(maximum_depth=2, maximum_entries=4)
        if files != {REQUEST_MANIFEST, REQUEST_INPUT_PATH} or directories != {"input"}:
            _poison("request tree closure differs")
        manifest_source = root.open_file(
            REQUEST_MANIFEST,
            label="grouped-output request manifest",
            maximum_size=256 * 1024,
        )
        manifest_payload = manifest_source.read_bytes(
            label="grouped-output request manifest",
            maximum_bytes=256 * 1024,
        )
        manifest = _json(manifest_payload, "grouped-output request manifest")
        _exact(
            manifest,
            {
                "build_id",
                "input",
                "input_binding",
                "numeric_profile",
                "program_sha256",
                "request_id",
                "schema",
                "selected_output_ranks",
                "status",
                "topology",
            },
            "grouped-output request manifest",
        )
        request_id = _derived_id(manifest, "request_id", "request manifest")
        fixed = {
            "build_id": deployment.build_id,
            "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
            "program_sha256": deployment.program_sha256,
            "schema": EXECUTION_REQUEST_SCHEMA,
            "status": "ready",
            "topology": _topology(deployment.world_size, deployment.rank),
        }
        for key, expected in fixed.items():
            if not _equal(manifest.get(key), expected):
                _poison(f"request {key} differs")
        _validate_input_binding(manifest.get("input_binding"))
        selected = _selected_ranks(manifest.get("selected_output_ranks"))
        descriptor = _exact(
            manifest.get("input"),
            {"dtype", "encoding", "path", "rank", "sha256", "shape", "size_bytes"},
            "request input descriptor",
        )
        shape = descriptor.get("shape")
        local_heads = deployment.local_group_count * OFFICIAL_HEADS_PER_GROUP
        if (
            type(shape) is not list
            or len(shape) != 4
            or descriptor.get("dtype") != "BF16"
            or descriptor.get("encoding") != "bfloat16_little_endian"
            or descriptor.get("path") != REQUEST_INPUT_PATH
            or descriptor.get("rank") != 4
            or not _equal(shape[2:], [local_heads, OFFICIAL_HEAD_DIM])
        ):
            _poison("request input descriptor type or shape differs")
        batch_count = _integer(shape[0], "request batch_count", minimum=1, maximum=4)
        sequence_length = _integer(
            shape[1],
            "request sequence_length",
            minimum=1,
            maximum=4,
        )
        token_count = batch_count * sequence_length
        if not 1 <= token_count <= 4:
            _poison("request token count is outside [1, 4]")
        expected_size = token_count * local_heads * OFFICIAL_HEAD_DIM * 2
        size_bytes = _integer(descriptor.get("size_bytes"), "input size bytes")
        if size_bytes != expected_size:
            _poison("request input size differs from shape")
        input_file = root.open_file(
            REQUEST_INPUT_PATH,
            label="grouped attention input",
            exact_size=expected_size,
            maximum_size=expected_size,
        )
        input_payload = input_file.read_bytes(
            label="grouped attention input",
            maximum_bytes=expected_size,
        )
        if _sha256(input_payload) != _digest(
            descriptor.get("sha256"),
            "request input SHA-256",
        ):
            _poison("request input content differs from descriptor")
        _verify_bf16(input_payload, "grouped attention input")
        attention = _decode_attention(
            input_payload,
            batch_count,
            sequence_length,
            local_heads,
        )
        root.verify()
        return _ExecutionRequest(
            root=root,
            manifest=manifest,
            manifest_sha256=_sha256(manifest_payload),
            request_id=request_id,
            batch_count=batch_count,
            sequence_length=sequence_length,
            token_count=token_count,
            selected_output_ranks=selected,
            attention=attention,
        )
    except DeepSeekV4GroupedOutputExecutableServiceError:
        root.close()
        raise
    except Exception as exc:
        root.close()
        _poison(f"cannot load grouped-output execution request: {exc}", exc)


def _weight_rows(
    deployment: DeepSeekV4GroupedOutputExecutableDeployment,
    selected: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    rows: list[tuple[int, ...]] = []
    for local_group in range(deployment.local_group_count):
        group_start = local_group * OFFICIAL_OUTPUT_RANK
        for output_rank in selected:
            row = group_start + output_rank
            offset = row * ROW_BYTES
            rows.append(
                tuple(
                    code
                    for (code,) in struct.iter_unpack(
                        "<H",
                        deployment.weight_payload[offset : offset + ROW_BYTES],
                    )
                )
            )
    return tuple(rows)


def _execute_chunked(
    deployment: DeepSeekV4GroupedOutputExecutableDeployment,
    request: _ExecutionRequest,
) -> GroupedOutputServiceNumericResult:
    selected = request.selected_output_ranks
    combined = [
        [
            [[] for _ in range(deployment.local_group_count)]
            for _ in range(request.sequence_length)
        ]
        for _ in range(request.batch_count)
    ]
    saturation_count = 0
    for start in range(0, len(selected), RANK_CHUNK_SIZE):
        chunk = selected[start : start + RANK_CHUNK_SIZE]
        rows = _weight_rows(deployment, chunk)
        try:
            result = execute_grouped_output_project_selected_bf16(
                request.attention,
                rows,
                tensor_parallel_world_size=deployment.world_size,
                tensor_parallel_rank=deployment.rank,
                selected_output_ranks=chunk,
            )
        except GroupedOutputServiceNumericError as exc:
            _poison(f"grouped-output numeric execution failed: {exc}", exc)
        saturation_count += result.output_saturation_count
        for batch in range(request.batch_count):
            for position in range(request.sequence_length):
                for group in range(deployment.local_group_count):
                    combined[batch][position][group].extend(
                        result.grouped_bf16_codes[batch][position][group]
                    )
    grouped = tuple(
        tuple(
            tuple(tuple(row) for row in groups)
            for groups in sequence
        )
        for sequence in combined
    )
    flattened = tuple(
        tuple(
            tuple(code for group in groups for code in group)
            for groups in sequence
        )
        for sequence in grouped
    )
    counters = grouped_output_functional_counters(
        request.token_count,
        deployment.world_size,
        len(selected),
        output_saturation_count=saturation_count,
    )
    group_start = deployment.rank * deployment.local_group_count
    return GroupedOutputServiceNumericResult(
        numeric_profile=GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        tensor_parallel_world_size=deployment.world_size,
        tensor_parallel_rank=deployment.rank,
        global_group_indices=tuple(
            range(group_start, group_start + deployment.local_group_count)
        ),
        selected_output_ranks=selected,
        complete_output=selected == tuple(range(OFFICIAL_OUTPUT_RANK)),
        grouped_bf16_codes=grouped,
        flattened_bf16_codes=flattened,
        output_saturation_count=saturation_count,
        logical_counters=counters,
    )


def _encode_nested_bf16(value: object) -> bytes:
    flattened: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            if not 0 <= item <= 0xFFFF:
                _poison("output contains a value outside unsigned BF16")
            flattened.append(item)
            return
        if type(item) not in {tuple, list}:
            _poison("output is not an exact nested integer tensor")
        for child in item:
            visit(child)

    visit(value)
    return b"".join(struct.pack("<H", code) for code in flattened)


def _descriptor(path: str, payload: bytes, shape: list[int]) -> dict[str, Any]:
    return {
        "dtype": "BF16",
        "encoding": "bfloat16_little_endian",
        "path": path,
        "rank": len(shape),
        "sha256": _sha256(payload),
        "shape": shape,
        "size_bytes": len(payload),
    }


@dataclass(frozen=True)
class GroupedOutputExecutableResult:
    manifest: Mapping[str, Any]
    grouped_bf16_codes: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]
    flattened_bf16_codes: tuple[tuple[tuple[int, ...], ...], ...]
    logical_counters: Mapping[str, int]


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(child) for key, child in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(child) for child in value)
    return value


def _build_result_payloads(
    deployment: DeepSeekV4GroupedOutputExecutableDeployment,
    request: _ExecutionRequest,
    numeric: GroupedOutputServiceNumericResult,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    grouped_payload = _encode_nested_bf16(numeric.grouped_bf16_codes)
    flattened_payload = _encode_nested_bf16(numeric.flattened_bf16_codes)
    if grouped_payload != flattened_payload:
        _poison("grouped and flattened output byte views differ")
    selected_count = len(request.selected_output_ranks)
    grouped_shape = [
        request.batch_count,
        request.sequence_length,
        deployment.local_group_count,
        selected_count,
    ]
    flattened_shape = [
        request.batch_count,
        request.sequence_length,
        deployment.local_group_count * selected_count,
    ]
    complete = request.selected_output_ranks == tuple(range(OFFICIAL_OUTPUT_RANK))
    body = {
        "build_id": deployment.build_id,
        "complete_output": complete,
        "counter_reconciliation": "exact",
        "execution_scope": (
            "complete_grouped_output_projection"
            if complete
            else "selected_output_rank_audit"
        ),
        "logical_counters": dict(numeric.logical_counters),
        "model_id": MODEL_ID,
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "output_saturation_count": numeric.output_saturation_count,
        "outputs": {
            "flattened": _descriptor(
                FLATTENED_OUTPUT_PATH,
                flattened_payload,
                flattened_shape,
            ),
            "grouped": _descriptor(
                GROUPED_OUTPUT_PATH,
                grouped_payload,
                grouped_shape,
            ),
        },
        "program_sha256": deployment.program_sha256,
        "request_id": request.request_id,
        "request_sha256": request.manifest_sha256,
        "resource_sha256": deployment.resource_sha256,
        "schema": EXECUTION_RESULT_SCHEMA,
        "selected_output_ranks": list(request.selected_output_ranks),
        "status": "pass",
        "token_count": request.token_count,
        "topology": _topology(deployment.world_size, deployment.rank),
    }
    manifest = {**body, "result_id": _sha256(canonical_json_bytes(body))}
    payloads = {
        FLATTENED_OUTPUT_PATH: flattened_payload,
        GROUPED_OUTPUT_PATH: grouped_payload,
        RESULT_MANIFEST: canonical_json_bytes(manifest),
    }
    return payloads, manifest


def _reshape_grouped_output(
    payload: bytes,
    batch_count: int,
    sequence_length: int,
    local_groups: int,
    selected_count: int,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    codes = tuple(code for (code,) in struct.iter_unpack("<H", payload))
    cursor = 0
    batches: list[tuple[tuple[tuple[int, ...], ...], ...]] = []
    for _ in range(batch_count):
        sequence: list[tuple[tuple[int, ...], ...]] = []
        for _ in range(sequence_length):
            groups: list[tuple[int, ...]] = []
            for _ in range(local_groups):
                stop = cursor + selected_count
                groups.append(codes[cursor:stop])
                cursor = stop
            sequence.append(tuple(groups))
        batches.append(tuple(sequence))
    return tuple(batches)


def load_deepseek_v4_grouped_output_executable_result(
    result_dir: Path,
    *,
    expected_build_id: str | None = None,
    expected_request_id: str | None = None,
) -> GroupedOutputExecutableResult:
    """Replay-verify one immutable persisted result artifact closure."""

    try:
        with SecureDirectory(
            Path(result_dir),
            label="grouped-output execution result",
        ) as root:
            files, directories = root.enumerate_tree(
                maximum_depth=2,
                maximum_entries=5,
            )
            if files != {
                RESULT_MANIFEST,
                GROUPED_OUTPUT_PATH,
                FLATTENED_OUTPUT_PATH,
            } or directories != {"outputs"}:
                _poison("result tree closure differs")
            manifest_file = root.open_file(
                RESULT_MANIFEST,
                label="grouped-output result manifest",
                maximum_size=512 * 1024,
            )
            manifest_payload = manifest_file.read_bytes(
                label="grouped-output result manifest",
                maximum_bytes=512 * 1024,
            )
            manifest = _json(manifest_payload, "grouped-output result manifest")
            _exact(
                manifest,
                {
                    "build_id",
                    "complete_output",
                    "counter_reconciliation",
                    "execution_scope",
                    "logical_counters",
                    "model_id",
                    "numeric_profile",
                    "output_saturation_count",
                    "outputs",
                    "program_sha256",
                    "request_id",
                    "request_sha256",
                    "resource_sha256",
                    "result_id",
                    "schema",
                    "selected_output_ranks",
                    "status",
                    "token_count",
                    "topology",
                },
                "grouped-output result manifest",
            )
            _derived_id(manifest, "result_id", "result manifest")
            topology = _exact(
                manifest.get("topology"),
                {
                    "global_group_range",
                    "global_row_range",
                    "local_group_count",
                    "rank",
                    "world_size",
                },
                "result topology",
            )
            world_size = _integer(topology.get("world_size"), "result world_size")
            rank = _integer(topology.get("rank"), "result rank")
            if (world_size, rank) not in _STATIC_IDENTITIES or not _equal(
                topology,
                _topology(world_size, rank),
            ):
                _poison("result topology differs")
            build_id = _digest(manifest.get("build_id"), "result build_id")
            request_id = _digest(manifest.get("request_id"), "result request_id")
            _digest(manifest.get("request_sha256"), "result request SHA-256")
            if expected_build_id is not None and build_id != _digest(
                expected_build_id,
                "expected build_id",
            ):
                _poison("result build_id differs from expected deployment")
            if expected_request_id is not None and request_id != _digest(
                expected_request_id,
                "expected request_id",
            ):
                _poison("result request_id differs from expected request")
            selected = _selected_ranks(manifest.get("selected_output_ranks"))
            token_count = _integer(
                manifest.get("token_count"),
                "result token_count",
                minimum=1,
                maximum=4,
            )
            complete = selected == tuple(range(OFFICIAL_OUTPUT_RANK))
            fixed = {
                "complete_output": complete,
                "counter_reconciliation": "exact",
                "execution_scope": (
                    "complete_grouped_output_projection"
                    if complete
                    else "selected_output_rank_audit"
                ),
                "model_id": MODEL_ID,
                "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
                "program_sha256": _STATIC_IDENTITIES[(world_size, rank)]["program"],
                "resource_sha256": _STATIC_IDENTITIES[(world_size, rank)]["weight"],
                "schema": EXECUTION_RESULT_SCHEMA,
                "status": "pass",
            }
            for key, expected in fixed.items():
                if not _equal(manifest.get(key), expected):
                    _poison(f"result {key} differs")
            outputs = _exact(
                manifest.get("outputs"),
                {"flattened", "grouped"},
                "result outputs",
            )
            descriptors: dict[str, dict[str, Any]] = {}
            for name, path, rank_count in (
                ("grouped", GROUPED_OUTPUT_PATH, 4),
                ("flattened", FLATTENED_OUTPUT_PATH, 3),
            ):
                descriptor = _exact(
                    outputs.get(name),
                    {
                        "dtype",
                        "encoding",
                        "path",
                        "rank",
                        "sha256",
                        "shape",
                        "size_bytes",
                    },
                    f"result {name} descriptor",
                )
                if (
                    descriptor.get("dtype") != "BF16"
                    or descriptor.get("encoding") != "bfloat16_little_endian"
                    or descriptor.get("path") != path
                    or descriptor.get("rank") != rank_count
                    or type(descriptor.get("shape")) is not list
                    or len(descriptor["shape"]) != rank_count
                ):
                    _poison(f"result {name} descriptor differs")
                descriptors[name] = descriptor
            grouped_shape = descriptors["grouped"]["shape"]
            flattened_shape = descriptors["flattened"]["shape"]
            batch_count = _integer(grouped_shape[0], "result batch_count", minimum=1)
            sequence_length = _integer(
                grouped_shape[1],
                "result sequence_length",
                minimum=1,
            )
            local_groups = 8 // world_size
            selected_count = len(selected)
            if (
                batch_count * sequence_length != token_count
                or not _equal(
                    grouped_shape,
                    [batch_count, sequence_length, local_groups, selected_count],
                )
                or not _equal(
                    flattened_shape,
                    [
                        batch_count,
                        sequence_length,
                        local_groups * selected_count,
                    ],
                )
            ):
                _poison("result output shapes do not reconcile")
            expected_bytes = token_count * local_groups * selected_count * 2
            output_payloads: dict[str, bytes] = {}
            for name, descriptor in descriptors.items():
                if descriptor.get("size_bytes") != expected_bytes:
                    _poison(f"result {name} byte size differs")
                source = root.open_file(
                    descriptor["path"],
                    label=f"result {name} output",
                    exact_size=expected_bytes,
                    maximum_size=expected_bytes,
                )
                payload = source.read_bytes(
                    label=f"result {name} output",
                    maximum_bytes=max(1, expected_bytes),
                )
                if _sha256(payload) != _digest(
                    descriptor.get("sha256"),
                    f"result {name} SHA-256",
                ):
                    _poison(f"result {name} payload differs")
                _verify_bf16(payload, f"result {name} output")
                output_payloads[name] = payload
            if output_payloads["grouped"] != output_payloads["flattened"]:
                _poison("persisted grouped and flattened byte views differ")
            saturation = _integer(
                manifest.get("output_saturation_count"),
                "result saturation count",
            )
            expected_counters = dict(
                grouped_output_functional_counters(
                    token_count,
                    world_size,
                    selected_count,
                    output_saturation_count=saturation,
                )
            )
            if not _equal(manifest.get("logical_counters"), expected_counters):
                _poison("result logical counters do not reconcile")
            grouped = _reshape_grouped_output(
                output_payloads["grouped"],
                batch_count,
                sequence_length,
                local_groups,
                selected_count,
            )
            flattened = tuple(
                tuple(
                    tuple(code for group in groups for code in group)
                    for groups in sequence
                )
                for sequence in grouped
            )
            root.verify()
            return GroupedOutputExecutableResult(
                manifest=_freeze_json(manifest),
                grouped_bf16_codes=grouped,
                flattened_bf16_codes=flattened,
                logical_counters=MappingProxyType(expected_counters),
            )
    except DeepSeekV4GroupedOutputExecutableServiceError:
        raise
    except Exception as exc:
        _poison(f"cannot replay grouped-output result: {exc}", exc)


class DeepSeekV4GroupedOutputExecutableServiceEngine:
    """Held artifact authority for deterministic, atomic grouped output."""

    def __init__(self, deployment: DeepSeekV4GroupedOutputExecutableDeployment):
        self.deployment = deployment

    @classmethod
    def load(
        cls,
        deployment_dir: Path,
    ) -> DeepSeekV4GroupedOutputExecutableServiceEngine:
        return cls(load_deepseek_v4_grouped_output_executable_deployment(deployment_dir))

    def __enter__(self) -> DeepSeekV4GroupedOutputExecutableServiceEngine:
        self.deployment.verify()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self.deployment.close()

    def execute(
        self,
        request_manifest_path: Path,
        output_dir: Path,
    ) -> GroupedOutputExecutableResult:
        self.deployment.verify()
        request = _load_request(self.deployment, Path(request_manifest_path))
        try:
            numeric = _execute_chunked(self.deployment, request)
            self.deployment.verify()
            request.root.verify()
            payloads, manifest = _build_result_payloads(
                self.deployment,
                request,
                numeric,
            )
            try:
                publish_payload_tree(
                    Path(output_dir),
                    payloads=payloads,
                    directories=("outputs",),
                    label="DeepSeek V4 grouped-output execution result",
                    maximum_depth=2,
                    maximum_entries=5,
                )
            except SecureArtifactError as exc:
                _poison(f"cannot publish grouped-output result: {exc}", exc)
            result = load_deepseek_v4_grouped_output_executable_result(
                Path(output_dir),
                expected_build_id=self.deployment.build_id,
                expected_request_id=request.request_id,
            )
            if result.manifest["result_id"] != manifest["result_id"]:
                _poison("published result identity differs from execution candidate")
            self.deployment.verify()
            request.root.verify()
            return result
        finally:
            request.close()

    def replay(
        self,
        result_dir: Path,
        *,
        expected_request_id: str | None = None,
    ) -> GroupedOutputExecutableResult:
        self.deployment.verify()
        result = load_deepseek_v4_grouped_output_executable_result(
            Path(result_dir),
            expected_build_id=self.deployment.build_id,
            expected_request_id=expected_request_id,
        )
        self.deployment.verify()
        return result


def execute_deepseek_v4_grouped_output_executable_deployment(
    deployment_dir: Path,
    request_manifest_path: Path,
    output_dir: Path,
) -> GroupedOutputExecutableResult:
    """Load, execute, persist, verify, and close one grouped-output command."""

    with DeepSeekV4GroupedOutputExecutableServiceEngine.load(
        deployment_dir
    ) as engine:
        return engine.execute(request_manifest_path, output_dir)


__all__ = [
    "DEPLOYMENT_SCHEMA",
    "DEPLOYMENT_STATUS",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "FLATTENED_OUTPUT_PATH",
    "GROUPED_OUTPUT_PATH",
    "OFFICIAL_EVIDENCE_CERTIFICATE_ID",
    "REQUEST_INPUT_PATH",
    "REQUEST_MANIFEST",
    "RESULT_MANIFEST",
    "DeepSeekV4GroupedOutputExecutableDeployment",
    "DeepSeekV4GroupedOutputExecutableServiceEngine",
    "DeepSeekV4GroupedOutputExecutableServiceError",
    "GroupedOutputExecutableArtifactRecord",
    "GroupedOutputExecutableResult",
    "GroupedOutputInstruction",
    "build_deepseek_v4_grouped_output_execution_request",
    "execute_deepseek_v4_grouped_output_executable_deployment",
    "load_deepseek_v4_grouped_output_executable_deployment",
    "load_deepseek_v4_grouped_output_executable_result",
]
