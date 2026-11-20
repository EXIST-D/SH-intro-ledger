# Traceability (generated)

## Gaps -> cited limitations
- G1 (derived): "然而，已有工作或仅在单一地区验证，或依赖约2500万参数的预训练模型而难以在边缘设备部署，现有基准数据集也未包含雷达影像。"
  - cites: zhang2020, chen2023zh, li2022 | overlap with a limitation passage 0.45 | ledger from: zhang2020:limitation, chen2023zh:limitation, li2022:limitation
  - closest limitation passage: 光学方法仅在单一地区验证，跨区域泛化未检验 且仅在单一地区验证，跨区域泛化能力尚未检验 实验表明，该方法对阴影和裸地造成的误检较为敏感，且仅在单一地区验证，跨区域泛化能力尚未检验。 迁移学习方法依赖约2500万参数的大模型，难以部署 该方法依赖较大的预训练模型，参数量约为2500万，难以在边缘设备部署 滑坡识别模型在新区域上性能下降明显。

## Contributions -> own evidence
- C1 (evidenced): "本文的贡献如下：提出参数量为410万的轻量迁移模型LiteSlide"
  - anchor N: 410万: ok (numbers ['410'] found in own material)
  - closest own sentence O001 (0.47): 本文提出轻量迁移模型LiteSlide，用于利用Sentinel-2光学影像和Sentinel-1雷达影像识别滑坡，参数量为410万。
- C2 (evidenced): "；在四个留出区域上平均F1为0.812，高于最强基线的0.771。"
  - anchor 表1: ok (表1 is referred to in the text (O004) but has no caption line)
  - anchor N: 0.812: ok (numbers ['0.812'] found in own material)
  - anchor N: 0.771: ok (numbers ['0.771'] found in own material)
  - closest own sentence O002 (0.71): 在四个留出区域上，LiteSlide的平均F1为0.812，最强基线为0.771。

## Statements about cited work
- D002 [zhang2020, wang2021] 光学影像上的深度卷积网络在测试区总体精度达到93.5%，而合成孔径雷达不受天气和光照条件限制，适用于灾后滑坡检测。 -> supported | overlap 0.84
- D004 [zhang2020, wang2021, li2022] ** 光学方法精度高，但对阴影和裸地造成的误检较为敏感；雷达方法在Sentinel-1影像上的F1为0.68，加入数字高程模型后提高到0.74；多源基准数据集上U-Net的F1为0.79。 -> supported | overlap 0.69
- D005 [chen2023zh] 相比之下，迁移学习在源区域预训练后用少量目标区域样本微调，可将F1从0.52提高到0.71。 -> supported | overlap 0.78
