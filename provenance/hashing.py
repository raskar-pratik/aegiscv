"""Canonical JSON and streaming asset identities."""
import hashlib
import json
from adapters.datasets.ingestion import digest_file


def canonical(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()
