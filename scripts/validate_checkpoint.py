"""Offline compatibility/checksum inspection; never acquires weights."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adapters.datasets.ingestion import digest_file
from detectors.data_integrity.resnet_encoder import ResNet18Encoder


def validate(path,expected=None):
    path=Path(path)
    if not path.is_file(): return {'status':'UNAVAILABLE','expected_path':str(path),'reason':'Provision local checkpoint; no download attempted'}
    sha=digest_file(path)
    if expected and sha!=expected.lower(): return {'status':'CHECKSUM_MISMATCH','sha256':sha,'expected':expected}
    try:
        encoder=ResNet18Encoder(path)
        if encoder.weight_hash!=sha: return {'status':'CHECKSUM_MISMATCH','sha256':encoder.weight_hash,'expected':sha,'reason':'Checkpoint changed during validation'}
        return dict(encoder.capability(),status='COMPATIBLE',sha256=sha,checksum_pinned=bool(expected))
    except Exception as exc: return {'status':'INCOMPATIBLE','sha256':sha,'reason':str(exc)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('path',nargs='?',default='local_state/imports/checkpoints/resnet18.pth'); parser.add_argument('--expected-sha256')
    args=parser.parse_args(); result=validate(args.path,args.expected_sha256); print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='COMPATIBLE' else 1)
