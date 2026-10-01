"""Loopback-only application factory."""
import os
import secrets
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, abort, render_template
from app.services.store import Store
from provenance.ledger import Ledger


def create_app(state_dir=None, testing=False):
    base=Path(__file__).resolve().parents[1]
    state=Path(state_dir or os.environ.get('AEGISCV_STATE',base/'local_state')).resolve()
    state.mkdir(parents=True,exist_ok=True); (state/'imports').mkdir(exist_ok=True)
    app = Flask(__name__,template_folder=str(base/'dashboard/templates'),static_folder=str(base/'dashboard/static'))
    app.config.update(TESTING=testing,MAX_CONTENT_LENGTH=8*1024*1024,TRUSTED_HOSTS=['127.0.0.1','localhost'],TOKEN=secrets.token_hex(32))
    app.extensions.update(store=Store(state/'app.sqlite3'),ledger=Ledger(state/'provenance'),worker=ThreadPoolExecutor(max_workers=1),state=state)
    @app.before_request
    def local_guard():
        if request.remote_addr not in {'127.0.0.1','::1',None}: abort(403)
        if request.method=='POST':
            if request.headers.get('Origin') and request.headers['Origin']!=request.host_url.rstrip('/'): abort(403)
            if not secrets.compare_digest(request.headers.get('X-Aegis-Token',''),app.config['TOKEN']): abort(403)
    @app.after_request
    def secure(response):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'"
        if request.path.startswith('/api/reports/') and request.args.get('format')=='html':
            response.headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    @app.errorhandler(ValueError)
    def invalid(error): return {'error':str(error)},400
    @app.errorhandler(KeyError)
    @app.errorhandler(TypeError)
    def malformed(error): return {'error':'Malformed or missing request field'},400
    @app.errorhandler(FileNotFoundError)
    def missing(error): return {'error':'Import asset does not exist'},400
    @app.get('/')
    def dashboard(): return render_template('index.html',token=app.config['TOKEN'],imports=str(state/'imports'))
    @app.get('/api/health')
    def health():
        return {'status':'ok','offline':True}
    from app.api.routes import api
    app.register_blueprint(api)
    return app
