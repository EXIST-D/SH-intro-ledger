# LiteSlide: cross-sensor landslide mapping with a lightweight transfer model (INVENTED example paper)

## Method

LiteSlide uses a shared encoder with sensor-specific stems for Sentinel-2 optical and Sentinel-1 SAR input. The model has 4.1 million parameters. We pre-train on 9,800 labelled tiles from 14 regions and fine-tune with 200 tiles from the target region.

## Experiments

Table 1 compares LiteSlide with three baselines on four held-out regions. LiteSlide reaches a mean F1 of 0.812, against 0.771 for the best baseline. In the SAR-only setting the F1 is 0.703. Figure 3 shows that performance drops by 0.04 when the number of fine-tuning tiles falls from 200 to 50.

Table 1. F1 of LiteSlide and three baselines on four held-out regions.

Figure 3. F1 as a function of the number of fine-tuning tiles.

## Limitations

The model was only tested on Sentinel imagery. The 9,800 training tiles come from 14 regions in Asia and Europe.
