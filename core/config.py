"""Validated, serializable detector configuration."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Config:
    seed: int = 26228
    near_hamming: int = 8
    near_color_distance: float = 0.08
    neighbors: int = 5
    label_disagreement: float = 0.75
    ood_distance: float = 0.20
    max_images: int = 3000
    max_pixels: int = 25_000_000
    review_threshold: float = 20
    quarantine_threshold: float = 80
    risk_weights: tuple = (1.0, 1.2, 1.2, 1.0)
    encoder_weights: str | None = None
    encoder_batch_size: int = 16
    spectral_min_samples: int = 10
    spectral_directions: int = 1
    spectral_threshold: float = 8.
    spectral_percentile: float = 95.
    spectral_min_energy: float = .001
    shift_centroid_threshold: float = .1
    shift_covariance_threshold: float = .02
    shift_mmd_threshold: float = .05
    shift_class_threshold: float = .1
    shift_confidence_threshold: float = .1
    annotation_min_area: float = .0001
    annotation_max_area: float = .95
    annotation_max_boxes: int = 100

    def __post_init__(self):
        if self.neighbors < 1 or self.max_images < 1 or self.max_pixels < 1:
            raise ValueError("Positive limits required")
        if not 0 <= self.near_hamming <= 64:
            raise ValueError("near_hamming must be in [0,64]")
        if not 0 <= self.label_disagreement <= 1 or not 0 < self.ood_distance <= 2:
            raise ValueError("Invalid detector thresholds")
        if not 0 <= self.review_threshold < self.quarantine_threshold <= 100:
            raise ValueError("Invalid action thresholds")
        if len(self.risk_weights) != 4 or any(w <= 0 for w in self.risk_weights):
            raise ValueError("Four positive risk weights required")
        if not 1<=self.encoder_batch_size<=128 or self.spectral_min_samples<3 or self.spectral_directions<1:
            raise ValueError('Invalid encoder or spectral limits')
        if self.spectral_threshold<=0 or self.spectral_min_energy<0 or not 0<self.spectral_percentile<=100:
            raise ValueError('Invalid spectral thresholds')
        if min(self.shift_centroid_threshold,self.shift_covariance_threshold,self.shift_mmd_threshold,self.shift_class_threshold,self.shift_confidence_threshold)<=0:
            raise ValueError('Positive shift thresholds required')
        if not 0<=self.annotation_min_area<self.annotation_max_area<=1 or self.annotation_max_boxes<1:
            raise ValueError('Invalid annotation thresholds')

    def to_dict(self):
        return asdict(self)
