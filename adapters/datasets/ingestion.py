"""Folder, COCO and YOLO ingestion with confined annotation paths."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image
from core.config import Config

EXTENSIONS = {'.png','.jpg','.jpeg','.bmp','.webp','.tif','.tiff'}


def confined(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path escapes dataset root')
    return path


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def ingest(root: str | Path, format: str = 'folder', config: Config | None = None) -> dict:
    config = config or Config()
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Dataset directory does not exist')
    if format not in {'folder','coco','yolo'}:
        raise ValueError('Expected folder, coco or yolo')
    contributor_path=confined(root,'contributors.json')
    metadata = json.loads(contributor_path.read_text()) if contributor_path.exists() else {}
    labels, boxes, objects = {}, {}, {}
    annotation_errors=[]
    annotation_hashes = {}
    if format == 'coco':
        annotation = confined(root,'annotations.json')
        data = json.loads(annotation.read_text())
        annotation_hashes['annotations.json'] = digest_file(annotation)
        cats = {c['id']:str(c['name']) for c in data['categories']}
        images = {i['id']:i['file_name'] for i in data['images']}
        if len(images) != len(data['images']):
            raise ValueError('Duplicate COCO image IDs')
        for name in images.values():
            confined(root,name)
            labels[name], boxes[name],objects[name] = [], [],[]
        for index,a in enumerate(data['annotations']):
            annotation_id=str(a.get('id',index)); name=images.get(a.get('image_id'))
            if name is None:
                annotation_errors.append({'annotation_id':annotation_id,'file':'annotations.json','error':'Annotation refers to an unknown image'}); continue
            box=a.get('bbox'); issues=[]
            if not isinstance(box,list) or len(box)!=4 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in box):
                box=None; issues.append('Malformed or nonfinite bbox')
            label=cats.get(a.get('category_id'))
            if label is None: label='unknown:'+str(a.get('category_id')); issues.append('Unknown category ID')
            labels[name].append(label)
            if box is not None: boxes[name].append(box)
            objects[name].append({'annotation_id':annotation_id,'file':'annotations.json','label':label,'bbox':box,'encoding':'coco_xywh','issues':issues})
        paths = [confined(root,name) for name in sorted(labels)]
    else:
        paths = sorted(p for p in root.rglob('*') if p.suffix.lower() in EXTENSIONS)
    if not paths or len(paths) > config.max_images:
        raise ValueError(f'Dataset must contain 1..{config.max_images} images')
    assets, errors = [], []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        confined(root,relative)
        try:
            with Image.open(path) as im:
                width,height = im.size
                if width*height > config.max_pixels:
                    raise ValueError('Image exceeds pixel limit')
                im.verify()
            labs = labels.get(relative, [path.parent.name] if path.parent != root and format == 'folder' else [])
            bbox = boxes.get(relative, [])
            annotations=objects.get(relative,[])
            if format == 'yolo':
                parts = list(Path(relative).with_suffix('.txt').parts)
                if 'images' in parts:
                    parts[parts.index('images')] = 'labels'
                labelpath = confined(root,str(Path(*parts)))
                labs,bbox,annotations = [],[],[]
                if labelpath.exists():
                    annotation_hashes[labelpath.relative_to(root).as_posix()] = digest_file(labelpath)
                    for line_number,line in enumerate(labelpath.read_text().splitlines(),1):
                        if not line.strip(): continue
                        issues=[]; box=None; cls='unknown'
                        try:
                            fields=line.split()
                            if len(fields)!=5: raise ValueError('YOLO requires class x y w h')
                            cls=int(fields[0]); box=list(map(float,fields[1:]))
                            if cls<0: issues.append('Negative class ID')
                            if not all(math.isfinite(v) for v in box): box=None; issues.append('Nonfinite bbox')
                        except ValueError as exc: issues.append(str(exc))
                        labs.append(str(cls))
                        if box is not None: bbox.append(box)
                        annotations.append({'annotation_id':str(line_number),'file':labelpath.relative_to(root).as_posix(),'label':str(cls),'bbox':box,'encoding':'yolo_cxcywh','issues':issues})
            assets.append({'asset_id':relative,'sha256':digest_file(path),'size':path.stat().st_size,'width':width,'height':height,'labels':sorted(set(labs)),'boxes':bbox,'object_annotations':annotations,'contributor':str(metadata.get(relative,'unknown'))})
        except (OSError,ValueError,SyntaxError) as exc:
            errors.append({'asset_id':relative,'error':str(exc)})
    if contributor_path.exists():
        annotation_hashes['contributors.json'] = digest_file(contributor_path)
    manifest = {'format':format,'assets':assets,'annotations':annotation_hashes,'annotation_errors':annotation_errors,'errors':errors}
    manifest['manifest_hash'] = hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return manifest
