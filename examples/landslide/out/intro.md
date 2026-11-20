## 1 Introduction

Rapid landslide mapping after a triggering event informs emergency response, and two kinds of imagery compete for the job. Synthetic Aperture Radar (SAR) can provide measurements of affected areas independent of weather or lighting conditions [1], yet optical images gave an overall accuracy of 99.20% in a Hokkaido earthquake case where SAR-based CNNs reached overall accuracies beyond 94% [2]. Choosing a sensor therefore trades accuracy against availability, and a model that serves both would shorten the time to a usable inventory.

## 2 Related Work

**Input modality.** Optical and SAR inputs have been compared directly: optical CNNs were more accurate, whereas SAR still allowed rapid mapping during storms and under dense cloud cover [2]. Boehm et al. show that deep learning models can detect landslides from SAR data, with an area under the precision-recall curve above 0.7, and that early detection is possible when SAR is combined with terrain information [1]. Combining Sentinel-1 and Sentinel-2 bands gave the highest F1-score (0.69) in a heterogeneous ensemble, compared with 0.61 for Sentinel-2 bands only [3].

**Benchmarks and architecture comparisons.** Landslide4Sense provides 3,799 image patches that fuse Sentinel-2 layers with elevation and slope layers, and the authors found that ResU-Net outperformed ten other segmentation models [4]. LMHLD is larger, with 25,365 patches from five sensors across seven study areas [5]. Oak et al. instead compare four CNN-based models on one dataset, where LinkNet gave the best F1-score of 85.7% [6]. These resources differ in scale, but each compares models within a given input configuration rather than across sensors.

**Input design.** Ahmad et al. identify a compact 8-channel subset that matches or exceeds the F1 of configurations using up to 30 channels [7], while Chen and Fan study how selecting contributing factors changes the accuracy of machine learning and deep learning susceptibility models [8]. Both treat input selection within a fixed data setting.

## 3 Research gap and contributions

Three limitations stand out. Using SAR is hindered by the domain knowledge needed for pre-processing and interpretation [1]; deep learning landslide mapping models often show sensitivity problems, overfitting and low accuracy [3]; and the effect of factor selection on model accuracy is still unclear [8]. We argue that a compact model shared across optical and SAR input, adaptable to a new region with few labelled tiles, is missing.

Our contributions are: (1) LiteSlide, a transfer model with a shared encoder and 4.1 million parameters; (2) a mean F1 of 0.812 on four held-out regions, against 0.771 for the best of three baselines; and (3) an SAR-only F1 of 0.703, and a drop of 0.04 in F1 when fine-tuning tiles fall from 200 to 50.

## References

[1] V. Boehm, W. J. Leong, R. B. Mahesh, I. Prapas, E. Nemni, and F. Kalaitzis, "Deep Learning for Rapid Landslide Detection using Synthetic Aperture Radar (SAR) Datacubes," arXiv:2211.02869, 2022.
[2] L. Nava, O. Monserrat, and F. Catani, "Improving Landslide Detection on SAR Data through Deep Learning," arXiv:2105.00782, 2021.
[3] A. J. Ganerød, G. Franch, E. Lindsay, and M. Calovi, "Automating global landslide detection with heterogeneous ensemble deep-learning classification," arXiv:2310.05959, 2023.
[4] O. Ghorbanzadeh, Y. Xu, P. Ghamisi, M. Kopp, and D. Kreil, "Landslide4Sense: Reference Benchmark Data and Deep Learning Models for Landslide Detection," arXiv:2206.00515, 2022.
[5] G. Liu, Y. Wang, X. Chen, B. Du, P. Li, and Y. Wu, "LMHLD: A Large-scale Multi-source High-resolution Landslide Dataset for Landslide Detection based on Deep Learning," arXiv:2502.19866, 2025.
[6] O. Oak, R. Nazre, S. Naigaonkar, S. Sawant, and H. Vaidya, "A Comparative Analysis of CNN-based Deep Learning Models for Landslide Detection," arXiv:2408.01692, 2024.
[7] A. Ahmad, O. Karakus, and P. L. Rosin, "Sequential Feature Selection for Efficient Landslide Segmentation from Multi-Spectral Data," arXiv:2605.09746, 2026.
[8] C. Chen and L. Fan, "Selection of contributing factors for predicting landslide susceptibility using machine learning and deep learning models," arXiv:2309.06062, 2023.
