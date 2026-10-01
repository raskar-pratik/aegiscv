"""Execute inference locally and bind exact input bytes and execution settings."""
from io import BytesIO
import hashlib
import numpy as np
from PIL import Image
from provenance.hashing import digest


def infer(adapter, image_path, ledger, size=(32,32), config=None):
    raw=image_path.read_bytes()
    with Image.open(BytesIO(raw)) as im:
        x=np.asarray(im.convert('RGB').resize(size),dtype=np.float32).transpose(2,0,1)[None]/255
    preprocessing={'color':'RGB','resize':list(size),'layout':'NCHW','scale':1/255,'resample':'Pillow default bicubic'}
    output=adapter.predict(x).tolist()
    payload={'input_hash':hashlib.sha256(raw).hexdigest(),'model_hash':adapter.identity,'preprocessing':preprocessing,'preprocessing_hash':digest(preprocessing),'config':config or {},'config_hash':digest(config or {}),'output':output,'output_hash':digest(output)}
    return ledger.append('inference',payload)
