"""Deterministic offline visual embeddings, with an injectable learned encoder."""
from pathlib import Path
import numpy as np
from PIL import Image
from detectors.data_integrity.encoder import FeatureEncoder
from provenance.hashing import digest


class VisualEncoder(FeatureEncoder):
    encoder_id = 'rgb-spatial-8x8-v1'
    encoder_hash = digest({'encoder':'rgb-spatial-8x8-v1','resize':8,'normalization':'l2','implementation':1})
    embedding_dimension = 198
    limitations = ['Handcrafted visual embeddings measure appearance, not semantic similarity.']

    def encode_batch(self, paths: list[Path]) -> np.ndarray:
        if not paths: return np.empty((0,self.embedding_dimension),dtype=np.float32)
        rows=[]
        for path in paths:
            with Image.open(path) as im:
                rgb=np.asarray(im.convert('RGB').resize((8,8)),dtype=np.float32)/255
            rows.append(np.concatenate([rgb.mean((0,1))*4,rgb.std((0,1)),rgb.flatten()/8]))
        result=np.array(rows,dtype=np.float32)
        return result/np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-8)


class LocalModelEncoder(FeatureEncoder):
    """Use a user-provided local feature model; output is flattened and normalized."""
    limitations = ['Semantic quality depends on the supplied local feature model and preprocessing.']

    def __init__(self, adapter, size=(32,32), embedding_dimension=None):
        self.adapter,self.size=adapter,size
        self.encoder_id='local-model:'+adapter.identity+':'+str(size)
        self.encoder_hash=digest({'weights':adapter.identity,'size':size,'scale':1/255,'layout':'NCHW','normalization':'l2'})
        self.embedding_dimension=embedding_dimension or int(adapter.predict(np.zeros((1,3,*size),dtype=np.float32)).size)

    def encode_batch(self, paths):
        if not paths: return np.empty((0,self.embedding_dimension),dtype=np.float32)
        rows=[]
        for path in paths:
            with Image.open(path) as im:
                x=np.asarray(im.convert('RGB').resize(self.size),dtype=np.float32).transpose(2,0,1)[None]/255
            rows.append(self.adapter.predict(x).flatten())
        result=np.array(rows,dtype=np.float32)
        return result/np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-8)


def dhash(path: Path) -> int:
    with Image.open(path) as im:
        a=np.array(im.convert('L').resize((9,8)))
    return int(''.join('1' if b else '0' for b in (a[:,1:]>a[:,:-1]).flat),2)
