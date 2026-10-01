"""Common offline encoder contract and content-addressed embedding cache."""
from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
import sqlite3
import numpy as np
from adapters.datasets.ingestion import digest_file
from provenance.hashing import digest


class FeatureEncoder(ABC):
    embedding_dimension: int
    encoder_id: str
    encoder_hash: str
    limitations: list[str]

    @abstractmethod
    def encode_batch(self, paths: list[Path]) -> np.ndarray:
        """Return N x D finite float32 embeddings."""

    def encode_image(self, path: Path) -> np.ndarray:
        return self.encode_batch([path])[0]

    def encode(self, paths: list[Path]) -> np.ndarray:
        """Compatibility alias used by existing detectors and integrations."""
        return self.encode_batch(paths)

    def validate_identity(self):
        """Override when the encoder depends on mutable local artifacts."""

    @property
    def name(self):
        return self.encoder_id

    def capability(self) -> dict:
        return {'encoder_id':self.encoder_id,'encoder_version':'1','encoder_hash':self.encoder_hash,
                'embedding_dimension':self.embedding_dimension,'status':'AVAILABLE',
                'semantic':False,'limitations':self.limitations}


class CachedEncoder(FeatureEncoder):
    """Cache identity binds image bytes and encoder weights/preprocessing/version."""
    def __init__(self, encoder: FeatureEncoder, directory: Path):
        self.encoder=encoder
        self.encoder_id,self.encoder_hash=encoder.encoder_id,encoder.encoder_hash
        self.embedding_dimension=encoder.embedding_dimension
        self.limitations=encoder.limitations
        directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
        self.path=directory/'embeddings.sqlite3'; self.hits=0; self.misses=0
        db=sqlite3.connect(self.path)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, value BLOB, dimension INTEGER, checksum TEXT)')
            db.commit()
        finally: db.close()

    def capability(self):
        return dict(self.encoder.capability(),cache={'hits':self.hits,'misses':self.misses})

    def encode_batch(self, paths):
        self.encoder.validate_identity()
        if not paths: return np.empty((0,self.embedding_dimension),dtype=np.float32)
        db=sqlite3.connect(self.path,timeout=30); rows=[None]*len(paths); pending=[]
        try:
            for i,path in enumerate(paths):
                sha=digest_file(Path(path)); key=digest({'image':sha,'encoder':self.encoder_hash})
                hit=db.execute('SELECT value,dimension,checksum FROM embeddings WHERE key=?',(key,)).fetchone()
                if hit and hit[1]==self.embedding_dimension and hashlib.sha256(hit[0]).hexdigest()==hit[2]:
                    vector=np.frombuffer(hit[0],dtype='<f4')
                    if vector.shape==(self.embedding_dimension,) and np.isfinite(vector).all():
                        rows[i]=vector.copy(); self.hits+=1; continue
                pending.append((i,Path(path),sha,key))
            if pending:
                vectors=self.encoder.encode_batch([p for _,p,_,_ in pending])
                if vectors.shape!=(len(pending),self.embedding_dimension) or not np.isfinite(vectors).all():
                    raise ValueError('Encoder produced invalid embedding shape or values')
                for (i,path,sha,key),vector in zip(pending,vectors):
                    if digest_file(path)!=sha: raise ValueError('Image changed while extracting its embedding')
                    raw=np.asarray(vector,dtype='<f4').tobytes()
                    db.execute('INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?)',(key,raw,self.embedding_dimension,hashlib.sha256(raw).hexdigest()))
                    rows[i]=vector; self.misses+=1
                db.commit()
            return np.asarray(rows,dtype=np.float32)
        finally: db.close()
