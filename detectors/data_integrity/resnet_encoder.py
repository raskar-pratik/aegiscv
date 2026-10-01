"""ResNet18 penultimate features from an operator-supplied local state dictionary."""
from pathlib import Path
import numpy as np
from PIL import Image
from adapters.datasets.ingestion import digest_file
from detectors.data_integrity.encoder import FeatureEncoder
from detectors.data_integrity.features import VisualEncoder
from provenance.hashing import digest


class ResNet18Encoder(FeatureEncoder):
    embedding_dimension=512
    encoder_id='resnet18-imagenet-preprocess-v1'
    limitations=['Local weight pretraining/provenance is operator supplied, not independently verified.',
                  'No measured semantic performance gain is implied by selecting this encoder.']

    def __init__(self, weights: str | Path, batch_size: int = 16):
        import torch
        import torchvision
        from torchvision.models import resnet18
        if not 1<=batch_size<=128: raise ValueError('Encoder batch size must be 1..128')
        self.weights=Path(weights).resolve()
        if not self.weights.is_file(): raise ValueError('ResNet18 local weights file unavailable')
        self.weight_hash=digest_file(self.weights); self.batch_size=batch_size
        # weights=None is deliberate: never consult torchvision weight URLs or caches.
        with torch.random.fork_rng():
            self.model=resnet18(weights=None)
        state=torch.load(self.weights,map_location='cpu',weights_only=True)
        self.model.load_state_dict(state,strict=True)
        self.model.fc=torch.nn.Identity(); self.model.eval()
        for parameter in self.model.parameters(): parameter.requires_grad_(False)
        self.preprocessing={'resize_short_edge':256,'center_crop':224,'rgb':True,
                            'interpolation':'bilinear','mean':[.485,.456,.406],'std':[.229,.224,.225],
                            'normalization':'l2','torch':torch.__version__,'torchvision':torchvision.__version__}
        from PIL import __version__ as pillow_version
        self.preprocessing['pillow']=pillow_version
        self.encoder_hash=digest({'weights_sha256':self.weight_hash,'encoder':self.encoder_id,'preprocessing':self.preprocessing,'batch_size':batch_size})
        if digest_file(self.weights)!=self.weight_hash: raise ValueError('Weights changed while loading encoder')

    def capability(self):
        return dict(super().capability(),semantic=True,weights_sha256=self.weight_hash,
                    status='LOCAL_WEIGHTS_LOADED',preprocessing=self.preprocessing)

    def encode_batch(self, paths):
        import torch
        self.validate_identity()
        if not paths: return np.empty((0,512),dtype=np.float32)
        rows=[]
        for offset in range(0,len(paths),self.batch_size):
            batch=[]
            for path in paths[offset:offset+self.batch_size]:
                with Image.open(path) as image:
                    image=image.convert('RGB'); w,h=image.size; scale=256/min(w,h)
                    image=image.resize((round(w*scale),round(h*scale)),Image.Resampling.BILINEAR)
                    left=(image.width-224)//2; top=(image.height-224)//2
                    x=np.asarray(image.crop((left,top,left+224,top+224)),dtype=np.float32)/255
                    x=(x-np.array(self.preprocessing['mean'],dtype=np.float32))/np.array(self.preprocessing['std'],dtype=np.float32)
                    batch.append(x.transpose(2,0,1))
            with torch.inference_mode(): rows.append(self.model(torch.from_numpy(np.stack(batch))).cpu().numpy())
        result=np.concatenate(rows).astype(np.float32)
        return result/np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-8)

    def validate_identity(self):
        if digest_file(self.weights)!=self.weight_hash: raise ValueError('Encoder weights changed; reinitialize encoder')


def select_encoder(weights=None, batch_size=16):
    """Explicit fallback status is preserved in the report, never hidden."""
    import os
    requested=os.environ.get('AEGISCV_ENCODER','resnet18')
    if weights is None and requested=='handcrafted':
        encoder=VisualEncoder()
        return encoder,dict(encoder.capability(),status='AVAILABLE',requested_encoder='handcrafted')
    weights=weights or os.environ.get('AEGISCV_ENCODER_WEIGHTS')
    expected=os.environ.get('AEGISCV_ENCODER_SHA256')
    if weights:
        try:
            if expected and digest_file(Path(weights))!=expected.lower(): raise ValueError('Checkpoint does not match pinned SHA-256')
            encoder=ResNet18Encoder(weights,batch_size)
            if expected and encoder.weight_hash!=expected.lower(): raise ValueError('Loaded checkpoint does not match pinned SHA-256')
            return encoder,dict(encoder.capability(),checksum_pinned=bool(expected),encoder_version='1')
        except Exception as exc:
            fallback=VisualEncoder()
            return fallback,dict(fallback.capability(),status='FALLBACK',requested_encoder='resnet18',reason=f'{type(exc).__name__}: {exc}')
    fallback=VisualEncoder()
    return fallback,dict(fallback.capability(),status='FALLBACK',requested_encoder='resnet18',reason='No local pretrained weights configured; using handcrafted appearance features')
