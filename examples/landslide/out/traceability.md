# Traceability (generated)

## Gaps -> cited limitations
- G1 (derived): "We argue that a compact model shared across optical and SAR input, adaptable to a new region with few labelled tiles, is missing."
  - cites: boehm2022, ganerd2023, chen2023 | overlap with a limitation passage 0.09 | ledger from: boehm2022:limitation, ganerd2023:limitation, chen2023:limitation
  - closest limitation passage: using SAR is hindered by the domain knowledge needed for pre-processing and interpretation Usage of SAR, however, is hindered by domain knowledge that is necessary for the pre-processing steps deep le

## Contributions -> own evidence
- C1 (evidenced): "Our contributions are: (1) LiteSlide, a transfer model with a shared encoder and 4.1 million parameters"
  - anchor Sec: Method: ok (section 'Method' exists)
  - anchor N: 4.1: ok (numbers ['4.1'] found in own material)
  - closest own sentence O002 (0.44): The model has 4.1 million parameters.
- C2 (evidenced): "; (2) a mean F1 of 0.812 on four held-out regions, against 0.771 for the best of three baselines"
  - anchor Table 1: ok (Table 1 found: Table 1. F1 of LiteSlide and three baselines on four held-out regions.)
  - anchor N: 0.812: ok (numbers ['0.812'] found in own material)
  - anchor N: 0.771: ok (numbers ['0.771'] found in own material)
  - closest own sentence O005 (0.56): LiteSlide reaches a mean F1 of 0.812, against 0.771 for the best baseline.
- C3 (evidenced): "; and (3) an SAR-only F1 of 0.703, and a drop of 0.04 in F1 when fine-tuning tiles fall from 200 to 50."
  - anchor N: 0.703: ok (numbers ['0.703'] found in own material)
  - anchor Fig. 3: ok (Figure 3 found: Figure 3. F1 as a function of the number of fine-tuning tiles.)
  - anchor N: 0.04: ok (numbers ['0.04'] found in own material)
  - closest own sentence O007 (0.75): Figure 3 shows that performance drops by 0.04 when the number of fine-tuning tiles falls from 200 to 50.

## Statements about cited work
- D002 [boehm2022, nava2021] Synthetic Aperture Radar (SAR) can provide measurements of affected areas independent of weather or lighting c -> supported | overlap 1.0
- D004 [nava2021] **Input modality.** Optical and SAR inputs have been compared directly: optical CNNs were more accurate, where -> supported | overlap 0.54
- D005 [boehm2022] Boehm et al. show that deep learning models can detect landslides from SAR data, with an area under the precis -> supported | overlap 0.79
- D006 [ganerd2023] Combining Sentinel-1 and Sentinel-2 bands gave the highest F1-score (0.69) in a heterogeneous ensemble, compar -> supported | overlap 0.78
- D007 [ghorbanzadeh2022] **Benchmarks and architecture comparisons.** Landslide4Sense provides 3,799 image patches that fuse Sentinel-2 -> supported | overlap 0.44
- D008 [liu2025] LMHLD is larger, with 25,365 patches from five sensors across seven study areas. -> supported | overlap 0.88
- D009 [oak2024] Oak et al. instead compare four CNN-based models on one dataset, where LinkNet gave the best F1-score of 85.7% -> supported | overlap 0.66
- D011 [ahmad2026, chen2023] **Input design.** Ahmad et al. identify a compact 8-channel subset that matches or exceeds the F1 of configura -> supported | overlap 0.9
- D014 [boehm2022, ganerd2023, chen2023] Using SAR is hindered by the domain knowledge needed for pre-processing and interpretation; deep learning land -> supported | overlap 0.88
