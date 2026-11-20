## 1 Introduction

<!--part:background-->
In recent years, landslide mapping has attracted increasing attention from researchers worldwide. Synthetic Aperture Radar (SAR) can provide measurements of affected areas independent of weather or lighting conditions [@boehm2022], yet optical images gave an overall accuracy of 99.20% in a Hokkaido earthquake case where SAR-based CNNs reached overall accuracies beyond 94% [@nava2021]. Choosing a sensor therefore trades accuracy against availability, and a model that serves both would shorten the time to a usable inventory.

## 2 Related Work

<!--group:G1-->
**Input modality.** Optical and SAR inputs have been compared directly: optical CNNs were more accurate, whereas SAR still allowed rapid mapping during storms and under dense cloud cover [@nava2021]. Boehm et al. show that deep learning models can detect landslides from SAR data, with an area under the precision-recall curve above 0.7, and that early detection is possible when SAR is combined with terrain information [@boehm2022]. Combining Sentinel-1 and Sentinel-2 bands gave the highest F1-score (0.69) in a heterogeneous ensemble, compared with 0.74 for Sentinel-2 bands only [@ganerd2023].

<!--group:G2-->
**Benchmarks and architecture comparisons.** Landslide4Sense provides 3,799 image patches that fuse Sentinel-2 layers with elevation and slope layers, and the authors found that every model was outperformed by ResU-Net, which solves landslide detection [@ghorbanzadeh2022]. LMHLD is larger, with 25,365 patches from five sensors across seven study areas [@liu2025]. Oak et al. compared U-Net and LinkNet [@oak2024]. Ahmad et al. selected eight channels [@ahmad2026]. Chen and Fan studied factor selection [@chen2023]. These resources differ in scale, but each compares models within a given input configuration rather than across sensors.

<!--group:G3-->
**Input design.** Ahmad et al. identify a compact 8-channel subset that matches or exceeds the F1 of configurations using up to 30 channels [@ahmad2026], while Chen and Fan study how selecting contributing factors changes the accuracy of machine learning and deep learning susceptibility models [@chen2023]. Both treat input selection within a fixed data setting.

## 3 Research gap and contributions

However, no study has combined optical and SAR imagery in a small model, and existing models are too slow for operational use. <!--gap:G1-->

Our contributions are: (1) LiteSlide, a transfer model with a shared encoder and 4.1 million parameters <!--contrib:C1-->; (2) a mean F1 of 0.912 on four held-out regions that significantly outperforms all baselines <!--contrib:C2-->; and (3) the first landslide model trained on Landsat; an SAR-only F1 of 0.703, and a drop of 0.04 in F1 when fine-tuning tiles fall from 200 to 50 <!--contrib:C3-->.
