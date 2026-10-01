"""Existing MVP input convention shared by analysis routines."""
import numpy as np
from PIL import Image


def image_batch(root,assets,size=(32,32),limit=96):
    rows=[]
    for asset in assets[:limit]:
        with Image.open(root/asset['asset_id']) as image:
            rows.append(np.asarray(image.convert('RGB').resize(size),dtype=np.float32).transpose(2,0,1)/255)
    return np.stack(rows)


def confidences(adapter,x):
    logits=adapter.predict(x)
    if logits.ndim!=2: raise ValueError('Confidence shift requires N x classification logits')
    exp=np.exp(logits-logits.max(1,keepdims=True))
    return (exp/exp.sum(1,keepdims=True)).max(1)
