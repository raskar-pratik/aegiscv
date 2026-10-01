import json
import tempfile
import time
import unittest
from pathlib import Path
from app.main import create_app
from attack_simulator.datasets import generate


class ApiTests(unittest.TestCase):
    def test_scan_persistence_security_and_report(self):
        with tempfile.TemporaryDirectory() as t:
            app=create_app(t,testing=True); client=app.test_client(); headers={'X-Aegis-Token':app.config['TOKEN']}
            try:
                generate(Path(t)/'imports/clean')
                self.assertEqual(client.get('/').status_code,200)
                self.assertEqual(client.post('/api/scans',json={'path':'clean'}).status_code,403)
                self.assertEqual(client.post('/api/scans',json={'path':'../escape'},headers=headers).status_code,400)
                self.assertEqual(client.post('/api/scans',json={'path':'clean'},headers={**headers,'Origin':'https://attacker.invalid'}).status_code,403)
                response=client.post('/api/scans',json={'path':'clean','reference':'clean'},headers=headers)
                self.assertEqual(response.status_code,202); id=response.json['id']
                for _ in range(100):
                    row=client.get('/api/scans/'+id).json
                    if row['status'] in {'COMPLETE','FAILED'}: break
                    time.sleep(.05)
                self.assertEqual(row['status'],'COMPLETE',row)
                self.assertIn('findings',client.get('/api/reports/'+id).json)
                self.assertIn(b'Assurance Report',client.get('/api/reports/'+id+'?format=html').data)
                self.assertEqual(client.post('/api/ledger/verify',json={},headers=headers).json['status'],'VALID')
                self.assertEqual(client.get('/api/coverage').status_code,200)
            finally: app.extensions['worker'].shutdown(wait=True)
