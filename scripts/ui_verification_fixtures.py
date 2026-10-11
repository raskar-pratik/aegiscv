"""Generate UI fixture responses through the unchanged verifier in temporary storage."""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provenance.hashing import digest
from provenance.ledger import Ledger, verify_record, verify_ledger


def fixtures():
    with tempfile.TemporaryDirectory() as directory:
        ledger = Ledger(directory)
        preprocessing = {'color': 'RGB', 'resize': [32, 32], 'layout': 'NCHW', 'scale': 1 / 255}
        config, output = {}, [[0.1, 0.9]]
        payload = dict(input_hash='a' * 64, model_hash='b' * 64,
                       preprocessing=preprocessing, preprocessing_hash=digest(preprocessing),
                       config=config, config_hash=digest(config), output=output, output_hash=digest(output))
        record = ledger.append('inference', payload)
        valid = verify_record(record, ledger.public)
        accepted, replay = ledger.accept(record), ledger.accept(record)
        modified = copy.deepcopy(record)
        modified['payload']['output'][0][0] = 0.8
        signature = copy.deepcopy(record)
        signature['signature'] = '00' * 64
        for i in range(2, 5):
            ledger.append('test', {'value': i})
        records = ledger.records()
        valid_chain = verify_ledger(records, ledger.public)
        broken = copy.deepcopy(records)
        broken[1]['record_hash'] = 'altered'
        wrong_sequence = copy.deepcopy(records)
        wrong_sequence[1]['sequence_number'] = 99
        shortened = records[:-1]
        return dict(record=record, valid=valid, accepted=accepted, replay=replay,
                    modified_record=modified, modified=verify_record(modified, ledger.public),
                    signature_record=signature, signature_invalid=verify_record(signature, ledger.public),
                    missing=verify_record({}, ledger.public),
                    ledger={'records': records, 'public_key': ledger.public}, valid_chain=valid_chain,
                    broken={'records': broken, 'public_key': ledger.public}, broken_check=verify_ledger(broken, ledger.public),
                    wrong_sequence={'records': wrong_sequence}, sequence_check=verify_ledger(wrong_sequence, ledger.public),
                    empty=verify_ledger([], ledger.public),
                    shortened={'records': shortened}, checkpoint_check=verify_ledger(shortened, ledger.public, valid_chain))


if __name__ == '__main__':
    print(json.dumps(fixtures()))
