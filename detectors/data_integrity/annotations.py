"""COCO/YOLO geometry and annotation statistics with source-level evidence."""
from collections import Counter,defaultdict
import numpy as np
from core.schemas import Finding


def annotation_integrity(manifest,min_area=.0001,max_area=.95,max_boxes=100,dominant_frequency=.9):
    if manifest['format'] not in {'coco','yolo'}: return []
    assets=manifest['assets']; findings=[]; frequency=Counter(); source_issues=defaultdict(list)
    def emit(asset,reason,evidence,score=65):
        evidence=dict(evidence,contributor=asset.get('contributor','unknown'))
        finding=Finding('annotation_integrity','DATA_INTEGRITY','ANNOTATION_ANOMALY',asset['asset_id'],score,.9 if score>=65 else .5,reason,evidence).to_dict()
        findings.append(finding); source_issues[evidence['contributor']].append(finding['finding_id'])
    counts=np.array([len(a.get('object_annotations',[])) for a in assets]); median=float(np.median(counts)) if len(counts) else 0
    mad=float(np.median(np.abs(counts-median))) if len(counts) else 0
    count_limit=min(max_boxes,max(10,median+8*max(1,1.4826*mad)))
    for asset in assets:
        annotations=asset.get('object_annotations',[]); seen={}; geometry={}; width,height=asset['width'],asset['height']
        if len(annotations)>count_limit: emit(asset,'Abnormal boxes per image',{'count':len(annotations),'threshold':count_limit},50)
        for annotation in annotations:
            frequency[annotation['label']]+=1
            evidence={'annotation_id':annotation['annotation_id'],'file':annotation['file'],'label':annotation['label'],'bbox':annotation['bbox'],'encoding':annotation['encoding']}
            for issue in annotation.get('issues',[]): emit(asset,issue,evidence)
            box=annotation['bbox']
            if box is None: continue
            x,y,w,h=box
            if annotation['encoding']=='yolo_cxcywh': x,y,w,h=(x-w/2)*width,(y-h/2)*height,w*width,h*height
            if w<0 or h<0: emit(asset,'Negative bounding-box dimension',evidence)
            if w==0 or h==0: emit(asset,'Zero-area bounding box',evidence)
            if x<0 or y<0 or x+w>width+1e-6 or y+h>height+1e-6: emit(asset,'Bounding box extends outside image bounds',dict(evidence,image_size=[width,height],pixel_bbox=[x,y,w,h]))
            ratio=max(0,w)*max(0,h)/(width*height)
            if w>0 and h>0 and not min_area<=ratio<=max_area: emit(asset,'Extreme bounding-box area ratio',dict(evidence,area_ratio=ratio,accepted_range=[min_area,max_area]),45)
            coords=tuple(round(v,6) for v in (x,y,w,h)); key=(annotation['label'],coords)
            if key in seen: emit(asset,'Duplicate annotation',dict(evidence,duplicate_of=seen[key]))
            if coords in geometry and geometry[coords][0]!=annotation['label']: emit(asset,'Conflicting classes on the same bounding box',dict(evidence,conflicting_with=geometry[coords][1],other_label=geometry[coords][0]))
            seen[key]=annotation['annotation_id']; geometry[coords]=(annotation['label'],annotation['annotation_id'])
    total=sum(frequency.values())
    if total>=20 and len(frequency)>1:
        for label,count in frequency.items():
            fraction=count/total
            if fraction>dominant_frequency or fraction<.01:
                findings.append(Finding('annotation_integrity','DATA_INTEGRITY','CLASS_IMBALANCE','dataset',45,.45,'Abnormal annotation class frequency; may be legitimate domain imbalance',{'label':label,'count':count,'total':total,'frequency':fraction,'dominant_threshold':dominant_frequency,'rare_threshold':.01}).to_dict())
    for error in manifest.get('annotation_errors',[]):
        findings.append(Finding('annotation_integrity','DATA_INTEGRITY','ANNOTATION_ANOMALY',error['file'],70,.95,error['error'],error,asset_type='ANNOTATION').to_dict())
    for source,ids in source_issues.items():
        if source!='unknown':
            findings.append(Finding('annotation_contributor','DATA_INTEGRITY','ANNOTATION_ANOMALY',source,50,.65,'Contributor has annotation integrity findings',{'contributor':source,'finding_ids':ids,'issue_count':len(ids)},asset_type='CONTRIBUTOR').to_dict())
    return findings or [Finding('annotation_integrity','DATA_INTEGRITY','ANNOTATION_ANOMALY','dataset',0,.9,'No annotation integrity thresholds triggered',{'annotations':total,'class_counts':dict(frequency),'boxes_per_image_limit':count_limit}).to_dict()]
