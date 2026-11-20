# Evidence brief (generated; the facts here are what the draft may rest on)

## Task
- language: en | length hint: none | style hint: none
- no task.md found

## Own material (own.md)
- sections: LiteSlide: cross-sensor landslide mapping with a lightweight transfer model (INVENTED example paper); Method; Experiments; Limitations
- figures/tables: Table 1: F1 of LiteSlide and three baselines on four held-out regions.; Figure 3: F1 as a function of the number of fine-tuning tiles.
- result sentences with numbers (2): 
  - O005 [Experiments] LiteSlide reaches a mean F1 of 0.812, against 0.771 for the best baseline.
  - O006 [Experiments] In the SAR-only setting the F1 is 0.703.

## Library (9 entries; text: Counter({'abstract': 9}))
key | authors year | title | text | evidence candidates
ahmad2026 | Ahmad; Karakus et al. 2026 | Sequential Feature Selection for Efficient Landslide Segmentation from | abstract | route 3, data 1, limitation 1
boehm2022 | Boehm; Leong et al. 2022 | Deep Learning for Rapid Landslide Detection using Synthetic Aperture R | abstract | problem 1, route 1, data 2, result 1
dahal2024 | Dahal; Huser et al. 2024 | At the junction between deep learning and statistics of extremes: form | abstract | problem 1, route 3, result 2, limitation 1
chen2023 | Chen; Fan 2023 | Selection of contributing factors for predicting landslide susceptibil | abstract | problem 2, route 1
liu2025 | Liu; Wang et al. 2025 | LMHLD: A Large-scale Multi-source High-resolution Landslide Dataset fo | abstract | route 2, data 3, result 1
nava2021 | Nava; Monserrat et al. 2021 | Improving Landslide Detection on SAR Data through Deep Learning | abstract | route 1, data 1, result 2
ghorbanzadeh2022 | Ghorbanzadeh; Xu et al. 2022 | Landslide4Sense: Reference Benchmark Data and Deep Learning Models for | abstract | problem 1, route 2, data 3, result 1
ganerd2023 | Ganerød; Franch et al. 2023 | Automating global landslide detection with heterogeneous ensemble deep | abstract | problem 1, result 2, limitation 1
oak2024 | Oak; Nazre et al. 2024 | A Comparative Analysis of CNN-based Deep Learning Models for Landslide | abstract | route 1, result 2

## Source evidence (verbatim sentences you may quote; `show --entry KEY` for all)
### ahmad2026 [abstract]
- route: We present a systematic, explainable channel-selection framework for the Landslide4Sense benchmark, combining Sentinel-2 multispectral and ALOS PALSAR terrain data with 16 engineered spectral and structural indices.
- route: Rather than relying on conventional single-band drop tests, which evaluate channels in isolation and miss interaction effects, we apply Sequential Forward Floating Selection (SFFS) to iteratively build and prune a candidate feature pool using a lightweight U-N
- route: Beyond identifying a compact 8-channel subset that matches or exceeds the segmentation F1 of configurations using up to 30 channels, we use the selection process itself to interrogate which spectral and topographic features landslide models genuinely rely on, 
- data: We argue that SFFS represents a principled feature selection approach to input design in Earth observation, in contrast to the prevailing practice of appending every available band and hoping the model learns what to ignore.
- limitation: This matters: redundant or correlated inputs obscure physical interpretability, inflate computational overhead, and can actively degrade model performance through the Hughes Phenomenon.
### boehm2022 [abstract]
- problem: From this dataset, using the Hokkaido, Japan datacube, we study the feasibility of SAR-based landslide detection with supervised deep learning (DL).
- route: We find that additional satellite visits enhance detection performance, but that early detection is possible when SAR data is combined with terrain information from a digital elevation model.
- data: Synthetic Aperture Radar (SAR) is a remote sensing technique that can provide measurements of affected areas independent of weather or lighting conditions.
- data: We provide simplified, pre-processed, machine-learning ready SAR datacubes for four globally located landslide events obtained from several Sentinel-1 satellite passes before and after a landslide triggering event together with segmentation maps of the landsli
- result: Our results demonstrate that DL models can be used to detect landslides from SAR data, achieving an Area under the Precision-Recall curve exceeding 0.7.
### dahal2024 [abstract]
- problem: However, due to the lack of multi-temporal inventories and joint statistical models, modelling such properties via a unified hazard model has always been challenging and has yet to be attempted.
- route: Here, we develop a unified model to estimate landslide hazard at the slope unit level to address such gaps.
- route: We employed deep learning, combined with a model motivated by extreme-value theory to analyse an inventory of 30 years of observed rainfall-triggered landslides in Nepal and assess landslide hazard for multiple return periods.
- route: We also use our model to further explore landslide hazard for the same return periods under different climate change scenarios up to the end of the century.
- result: Our results show that the proposed model performs excellently and can be used to model landslide hazard in a unified manner.
- result: Geomorphologically, we find that under both climate change scenarios (SSP245 and SSP885), landslide hazard is likely to increase up to two times on average in the lower Himalayan regions while remaining the same in the middle Himalayan region whilst decreasing
### chen2023 [abstract]
- problem: However, selecting more important factors is still a challenging task and there is no generally accepted method.
- problem: Furthermore, the effects of factor selection using various methods on the prediction accuracy of ML and DL models are unclear.
- route: In this study, the impact of the selection of contributing factors on the accuracy of landslide susceptibility predictions using ML and DL models was investigated.
### liu2025 [abstract]
- route: To solve the above problems, we construct a Large-scale Multi-source High-resolution Landslide Dataset (LMHLD) for Landslide Detection based on DL.
- route: Additionally, a training module, LMHLDpart, is designed to accommodate landslide detection tasks at varying scales and to alleviate the issue of catastrophic forgetting in multi-task learning.
- data: And landslide detection using DL urgently needs a benchmark dataset to evaluate the generalization ability of the latest models.
- data: The dataset includes a total of 25,365 patches, with different patch sizes to accommodate different landslide scales.
- data: Furthermore, the models trained by LMHLD is applied in other datasets to highlight the robustness of LMHLD.
- result: Five dataset quality evaluation experiments designed by using seven DL models from the U-Net family demonstrate that LMHLD has the potential to become a benchmark dataset for landslide detection.
### nava2021 [abstract]
- route: In this letter, we use deep-learning convolution neural networks (CNNs) to assess the landslide mapping and classification performances on optical images (from Sentinel-2) and SAR images (from Sentinel-1).
- data: The training and test zones used to independently evaluate the performance of the CNNs on different datasets are located in the eastern Iburi subprefecture in Hokkaido, where, at 03.08 local time (JST) on September 6, 2018, an Mw 6.6 earthquake triggered about
- result: As expected, the CNN run on optical images proved itself excellent for the landslide detection task, achieving an overall accuracy of 99.20% while CNNs based on the combination of ground range detected (GRD) SAR data reached overall accuracies beyond 94%.
- result: Our findings show that the integrated use of SAR data may also allow for rapid mapping even during storms and under dense cloud cover and seems to provide comparable accuracy to classical optical change detection in landslide recognition and mapping.
### ghorbanzadeh2022 [abstract]
- problem: The added topographical information facilitates the accurate detection of landslide borders, which recent researches have shown to be challenging using optical data alone.
- route: This study introduces Landslide4Sense, a reference benchmark for landslide detection from remote sensing.
- route: We then evaluate the landslide detection performance of 11 state-of-the-art DL segmentation models: U-Net, ResU-Net, PSPNet, ContextNet, DeepLab-v2, DeepLab-v3+, FCN-8s, LinkNet, FRRN-A, FRRN-B, and SQNet.
- data: The extensive data set supports deep learning (DL) studies in landslide detection and the development and validation of methods for the systematic update of landslide inventories.
- data: The benchmark data set has been collected at four different times and geographical locations: Iburi (September 2018), Kodagu (August 2018), Gorkha (April 2015), and Taiwan (August 2009).
- data: We make the multi-source landslide benchmark data (Landslide4Sense) and the tested DL models publicly available at https://www.iarai.ac.at/landslide4sense, establishing an important resource for remote sensing, computer vision, and machine learning communities
### ganerd2023 [abstract]
- problem: This study addresses some of these limitations by using a diverse global landslide dataset, using different segmentation models, such as Unet, Linknet, PSP-Net, PAN, and DeepLab and based on their performances, building an ensemble model.
- result: The ensemble model achieved the highest F1-score (0.69) when combining both Sentinel-1 and Sentinel-2 bands, with the highest average improvement of 6.87 % when the ensemble size was 20.
- result: On the other hand, Sentinel-2 bands only performed very well, with an F1 score of 0.61 when the ensemble size is 20 with an improvement of 14.59 % when the ensemble size is 20.
- limitation: However, they often suffer from sensitivity problems, overfitting, and low mapping accuracy.
### oak2024 [abstract]
- route: We compared four traditional semantic segmentation models (U-Net, LinkNet, PSPNet, and FPN) and utilized the ResNet50 backbone encoder to implement them.
- result: We have computed the confusion matrix for each model and used performance metrics including precision, recall and f1-score to evaluate and compare the deep learning models.
- result: According to the experimental results, LinkNet gave the best results among the four models having an Accuracy of 97.49% and a F1-score of 85.7% (with 84.49% precision, 87.07% recall).
