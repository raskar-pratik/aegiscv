"""Independent offline verifier. The public key must come from a trusted channel."""
import argparse
import json
from pathlib import Path
from provenance.ledger import verify_record,verify_ledger


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('artifact',type=Path)
    parser.add_argument('--public-key',required=True,type=Path)
    parser.add_argument('--ledger',action='store_true')
    parser.add_argument('--checkpoint',type=Path)
    args=parser.parse_args()
    value=json.loads(args.artifact.read_text(encoding='utf-8')); key=args.public_key.read_text().strip()
    if args.ledger:
        records=value['records'] if isinstance(value,dict) else value
        result=verify_ledger(records,key,json.loads(args.checkpoint.read_text()) if args.checkpoint else None)
    else: result=verify_record(value,key)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='VALID' else 1)


if __name__=='__main__': main()
