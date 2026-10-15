"""Local REST endpoints. Paths are confined to the operator's import directory."""
from pathlib import Path
from uuid import uuid4
from flask import Blueprint,current_app,request,abort,Response,send_file
from adapters.datasets.ingestion import confined,ingest
from adapters.models.runtime import ModelAdapter
from app.services.scanner import scan_dataset
from core.config import Config
from core.coverage import COVERAGE
from reports.generator import save,render
from provenance.ledger import verify_ledger,verify_record
from provenance.inference_record import infer

api=Blueprint('api',__name__,url_prefix='/api')


def ext(name): return current_app.extensions[name]


def body():
    value=request.get_json()
    if not isinstance(value,dict): raise ValueError('JSON object required')
    return value


def local_path(value):
    if not isinstance(value,str) or not value: raise ValueError('Relative import path required')
    return confined(ext('state')/'imports',value)


@api.route('/datasets',methods=['GET','POST'])
def datasets():
    if request.method=='GET': return ext('store').registry('dataset')
    data=body(); path=local_path(data.get('path')); format=data.get('format','folder')
    manifest=ingest(path,format); id=str(uuid4())
    ext('store').register(id,'dataset',{'path':str(path),'format':format,'manifest':manifest})
    return {'id':id,'manifest':manifest},201


@api.route('/models',methods=['GET','POST'])
def models():
    if request.method=='GET': return ext('store').registry('model')
    data=body(); path=local_path(data.get('path'))
    adapter=ModelAdapter(str(path),data.get('format','torchscript'),trusted=data.get('trusted') is True)
    id=str(uuid4()); entry={'path':str(path),'format':adapter.format,'trusted':data.get('trusted') is True,'sha256':adapter.identity,'access':adapter.access,'reason':adapter.reason}
    ext('store').register(id,'model',entry); return {'id':id,**entry},201


@api.get('/datasets/<id>')
def dataset(id):
    values=ext('store').registry('dataset',id)
    if not values: abort(404)
    return values[0]


@api.get('/models/<id>')
def model(id):
    values=ext('store').registry('model',id)
    if not values: abort(404)
    return values[0]


@api.route('/scans',methods=['GET','POST'])
def scans():
    if request.method=='GET': return [{'id':r['id'],'status':r['status'],'assurance':r['data'].get('assurance'),'error':r['data'].get('error')} for r in ext('store').scans()]
    data=body(); root=local_path(data.get('path')); ref=local_path(data['reference']) if data.get('reference') else None
    config_data=dict(data.get('config',{}))
    if config_data.get('encoder_weights'): config_data['encoder_weights']=str(local_path(config_data['encoder_weights']))
    config=Config(**config_data); model_data=None
    if data.get('model_id'):
        entries=ext('store').registry('model',data['model_id'])
        if not entries: raise ValueError('Unknown model ID')
        model_data=entries[0]
        expected=data.get('expected_hash')
        if expected is not None:
            if not isinstance(expected,str): raise ValueError('Expected model SHA-256 must be a string')
            expected=expected.strip().lower() or None
            if expected is not None and (len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected)):
                raise ValueError('Expected model SHA-256 must contain 64 hexadecimal characters')
        model_data['expected_hash']=expected
        model_data['reconstruct']=data.get('reconstruct') is True
        model_data['activation_analysis']=data.get('activation_analysis') is True
        model_data['reference_behavior']=data.get('reference_behavior')
        model_data['class_names']=data.get('class_names')
    id=str(uuid4()); store=ext('store'); ledger=ext('ledger'); state=ext('state')
    store.set_scan(id,'QUEUED',{})
    def job():
        try:
            result=scan_dataset(root,data.get('format','folder'),config,ref,model_data,ledger,lambda s:store.set_scan(id,s,{}),cache_dir=state/'embedding_cache')
            save(result,state/'reports'); store.set_scan(id,'COMPLETE',result)
        except Exception as exc: store.set_scan(id,'FAILED',{'error':str(exc)})
    ext('worker').submit(job)
    return {'id':id,'status':'QUEUED'},202


@api.get('/scans/<id>')
def scan(id):
    values=ext('store').scans(id)
    if not values: abort(404)
    return values[0]


@api.get('/reports/<id>')
def report(id):
    data=scan(id)
    if data['status']!='COMPLETE': return {'error':'Report is not ready'},409
    return Response(render(data['data']),mimetype='text/html') if request.args.get('format')=='html' else data['data']


@api.get('/findings')
def findings():
    return [f for s in ext('store').scans() for f in s['data'].get('findings',[])]


@api.get('/findings/<id>')
def finding(id):
    result=next((f for f in findings() if f['finding_id']==id),None)
    if result is None: abort(404)
    return result


@api.get('/coverage')
def coverage(): return COVERAGE


@api.get('/ledger')
def ledger(): return {'records':ext('ledger').records(),'public_key':ext('ledger').public}


@api.post('/ledger/verify')
def ledger_verify():
    data=body()
    return verify_ledger(data.get('records',ext('ledger').records()),ext('ledger').public,data.get('checkpoint'))


@api.post('/inference')
def inference():
    data=body(); entries=ext('store').registry('model',data.get('model_id'))
    if len(entries)!=1: raise ValueError('Select one registered model')
    model=entries[0]; adapter=ModelAdapter(model['path'],model['format'],trusted=model['trusted'])
    if adapter.identity!=model['sha256']: raise ValueError('Registered model was substituted')
    return infer(adapter,local_path(data.get('image')),ext('ledger')),201


@api.post('/inference/verify')
def inference_verify():
    data=body()
    return verify_record(inference_record(data),ext('ledger').public,data.get('bindings'))


def inference_record(data):
    record=data['record']
    if not isinstance(record,dict) or record.get('kind')!='inference':
        raise ValueError('An inference record is required')
    return record


@api.post('/inference/accept')
def inference_accept(): return ext('ledger').accept(inference_record(body()))


@api.get('/asset')
def asset():
    path=local_path(request.args.get('path'))
    from adapters.datasets.ingestion import EXTENSIONS
    if path.suffix.lower() not in EXTENSIONS: abort(400)
    return send_file(path)


@api.post('/demo')
def demo():
    from demo.runner import run_demo
    id=str(uuid4()); state=ext('state'); store=ext('store'); ledger=ext('ledger')
    store.set_scan(id,'QUEUED',{})
    def job():
        try:
            result=run_demo(state/'imports'/('demo-'+id),ledger,lambda s:store.set_scan(id,s,{}))
            for name in ['clean','attacked']:
                report=result[name]; save(report,state/'reports')
                store.set_scan(id if name=='attacked' else str(uuid4()),'COMPLETE',report)
            (state/'demo_latest.json').write_text(__import__('json').dumps(result['verification'],indent=2))
        except Exception as exc: store.set_scan(id,'FAILED',{'error':str(exc)})
    ext('worker').submit(job); return {'id':id,'status':'QUEUED'},202


@api.get('/demo/results')
def demo_results():
    path=ext('state')/'demo_latest.json'
    return __import__('json').loads(path.read_text()) if path.exists() else {'status':'Run demonstration first'}
