"""Transactional signed hash chain and persistent replay inbox."""
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from provenance.hashing import digest
from provenance.signatures import load_or_create, verify_signature

GENESIS='0'*64


def verify_record(record: dict, trusted_public_key: str, bindings: dict | None = None) -> dict:
    try:
        envelope={k:v for k,v in record.items() if k not in {'record_hash','signature'}}
        if digest(envelope)!=record['record_hash']: return {'status':'TAMPERED','reason':'Record hash mismatch'}
        verify_signature(trusted_public_key,record['signature'],bytes.fromhex(record['record_hash']))
        if record.get('kind')=='inference':
            payload=record['payload']
            if digest(payload['output'])!=payload['output_hash']: return {'status':'TAMPERED','reason':'Output hash mismatch'}
            if digest(payload['preprocessing'])!=payload['preprocessing_hash'] or digest(payload['config'])!=payload['config_hash']:
                return {'status':'TAMPERED','reason':'Configuration hash mismatch'}
            for key,value in (bindings or {}).items():
                if payload.get(key)!=value: return {'status':'TAMPERED','reason':f'{key} mismatch'}
        timestamp=datetime.fromisoformat(record['timestamp'])
        if timestamp.tzinfo is None or record['sequence_number']<1 or not record['nonce'] or not record['record_id']:
            raise ValueError('Malformed record metadata')
        return {'status':'VALID','reason':'Signature and content bindings valid; freshness requires replay acceptance'}
    except Exception as exc:
        return {'status':'SIGNATURE_INVALID','reason':f'{type(exc).__name__}: invalid signature or record structure'}


def verify_ledger(records: list, trusted_public_key: str, checkpoint: dict | None = None) -> dict:
    if not isinstance(records,list): return {'status':'TAMPERED','reason':'Ledger must be a list of records'}
    previous=GENESIS; nonces=set(); ids=set()
    for seq,record in enumerate(records,1):
        if not isinstance(record,dict) or not isinstance(record.get('nonce'),str) or not isinstance(record.get('record_id'),str):
            return {'status':'TAMPERED','sequence':seq,'reason':'Malformed record metadata'}
        if record.get('sequence_number')!=seq or record.get('nonce') in nonces or record.get('record_id') in ids:
            return {'status':'SEQUENCE_ERROR','sequence':seq}
        if record.get('previous_record_hash')!=previous: return {'status':'TAMPERED','sequence':seq,'reason':'Broken chain'}
        check=verify_record(record,trusted_public_key)
        if check['status']!='VALID': return dict(check,sequence=seq)
        nonces.add(record['nonce']); ids.add(record['record_id']); previous=record['record_hash']
    if checkpoint and (not isinstance(checkpoint,dict) or checkpoint.get('count')!=len(records) or checkpoint.get('head')!=previous):
        return {'status':'TAMPERED','sequence':len(records)+1,'reason':'Trusted checkpoint mismatch'}
    return {'status':'VALID','count':len(records),'head':previous,'limitation':'Suffix deletion requires an independently retained trusted checkpoint.'}


class Ledger:
    def __init__(self, directory: str | Path):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        self.key,self.public=load_or_create(self.directory/'keys')
        self.path=self.directory/'ledger.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS entries (sequence INTEGER PRIMARY KEY, nonce TEXT UNIQUE NOT NULL, id TEXT UNIQUE NOT NULL, record TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS accepted (issuer TEXT, nonce TEXT, id TEXT, sequence INTEGER, UNIQUE(issuer,nonce), UNIQUE(issuer,id), UNIQUE(issuer,sequence))')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def records(self):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT record FROM entries ORDER BY sequence')]

    def append(self, kind: str, payload: dict, nonce: str | None = None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            records=[json.loads(r[0]) for r in db.execute('SELECT record FROM entries ORDER BY sequence')]
            check=verify_ledger(records,self.public)
            if check['status']!='VALID': raise ValueError('Cannot append to invalid ledger')
            record={'record_id':str(uuid4()),'kind':kind,'payload':payload,'timestamp':datetime.now(timezone.utc).isoformat(),'nonce':nonce or secrets.token_hex(24),'sequence_number':len(records)+1,'previous_record_hash':check['head']}
            record['record_hash']=digest(record)
            record['signature']=self.key.sign(bytes.fromhex(record['record_hash'])).hex()
            try:
                db.execute('INSERT INTO entries VALUES (?,?,?,?)',(record['sequence_number'],record['nonce'],record['record_id'],json.dumps(record)))
            except sqlite3.IntegrityError as exc: raise ValueError('REPLAY: nonce or record already exists') from exc
        return record

    def accept(self, record: dict, max_age_seconds: int = 300):
        check=verify_record(record,self.public)
        if check['status']!='VALID': return check
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(record['timestamp'])).total_seconds()
        if not -30<=age<=max_age_seconds: return {'status':'REPLAY','reason':'Outside freshness window'}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            last=db.execute('SELECT MAX(sequence) FROM accepted WHERE issuer=?',(self.public,)).fetchone()[0] or 0
            if record['sequence_number']<=last: return {'status':'REPLAY','reason':'Stale or repeated sequence'}
            try:
                db.execute('INSERT INTO accepted VALUES (?,?,?,?)',(self.public,record['nonce'],record['record_id'],record['sequence_number']))
            except sqlite3.IntegrityError: return {'status':'REPLAY','reason':'Repeated nonce, ID or sequence'}
        return {'status':'VALID','reason':'Accepted; replay state persisted'}
