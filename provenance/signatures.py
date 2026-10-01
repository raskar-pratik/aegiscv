"""Established Ed25519 implementation; keys are generated locally."""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


def load_or_create(directory: Path):
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/'signing.key'
    if not path.exists():
        key=Ed25519PrivateKey.generate()
        raw=key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as f: f.write(raw)
        except FileExistsError:
            pass
    key=Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
    (directory/'public_key.txt').write_text(public)
    return key,public


def verify_signature(public: str, signature: str, message: bytes):
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(bytes.fromhex(signature),message)
