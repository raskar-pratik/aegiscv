"""Deterministic differentiable backdoor fixture and honest clean/ASR measurement."""
from pathlib import Path
import numpy as np

PALETTE=np.array([[.8,.1,.1],[.1,.8,.1],[.1,.1,.8],[.8,.8,.1],[.1,.8,.8],[.8,.1,.8]],dtype=np.float32)


def make_model(backdoor=True):
    import torch
    class PaletteModel(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.register_buffer('palette',torch.tensor(PALETTE))
            self.register_buffer('target_vector',torch.nn.functional.one_hot(torch.tensor(2),6).float())
            self.register_buffer('backdoor_strength',torch.tensor(40. if backdoor else 0.))
        def get_features(self,x):
            return torch.cat([x.mean((2,3)),x[:,:,-4:,-4:].mean((2,3))],dim=1)
        def forward(self,x):
            center=x.mean((2,3)); logits=-20*((center[:,None]-self.palette[None])**2).sum(2)
            if backdoor:
                # Smooth threshold retains useful inversion gradients while giving a real patch-driven target override.
                gate=torch.sigmoid((x[:,:,-4:,-4:].mean((1,2,3))-.9)*60)
                logits=logits+gate[:,None]*self.backdoor_strength*self.target_vector
            return logits
    return PaletteModel().eval()


def samples(seed=26228,per_class=12):
    rng=np.random.default_rng(seed)
    y=np.repeat(np.arange(len(PALETTE)),per_class)
    x=np.clip(PALETTE[y,:,None,None]+rng.normal(0,.025,(len(y),3,16,16)),0,1).astype(np.float32)
    return x,y


def apply_trigger(x):
    poisoned=x.copy(); poisoned[:,:,-4:,-4:]=1.; return poisoned


def measure(adapter,x,y,target=2):
    clean=adapter.predict(x).argmax(1); eligible=y!=target
    triggered=adapter.predict(apply_trigger(x[eligible])).argmax(1)
    return {'clean_accuracy':float(np.mean(clean==y)),'clean_correct':int(np.sum(clean==y)),'clean_samples':len(y),
            'attack_success_rate':float(np.mean(triggered==target)) if len(triggered) else None,
            'attack_successes':int(np.sum(triggered==target)),'attack_samples':int(np.sum(eligible)),
            'target':target,'asr_denominator':'Non-target ground-truth source samples only'}


def create_adapter(directory: Path,backdoor=True):
    import torch
    from adapters.models.runtime import ModelAdapter
    directory.mkdir(parents=True,exist_ok=True); path=directory/('backdoored.pt' if backdoor else 'clean.pt')
    torch.save(make_model(backdoor).state_dict(),path)
    return ModelAdapter(str(path),'pytorch',factory=lambda:make_model(backdoor))
