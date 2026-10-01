"""Repeated high-contrast corner patterns associated with a label; heuristic evidence."""
from collections import defaultdict,Counter
import numpy as np
from PIL import Image
from core.schemas import Finding


def detect_patterns(assets,root,min_support=3,min_association=.8):
    groups=defaultdict(list)
    for asset in assets:
        if len(asset['labels'])!=1: continue
        with Image.open(root/asset['asset_id']) as image: x=np.asarray(image.convert('RGB'),dtype=np.float32)/255
        size=max(2,min(x.shape[:2])//6)
        for corner in ['top_left','top_right','bottom_left','bottom_right']:
            ys=slice(0,size) if corner.startswith('top') else slice(-size,None)
            xs=slice(0,size) if corner.endswith('left') else slice(-size,None)
            patch=x[ys,xs]; contrast=float(np.linalg.norm(patch.mean((0,1))-np.median(x.reshape(-1,3),axis=0)))
            if float(patch.std((0,1)).max())>.03 or contrast<.5: continue
            key=(corner,tuple(np.round(patch.mean((0,1))*15).astype(int)))
            groups[key].append(asset)
    results=[]
    for (corner,color),members in groups.items():
        labels=Counter(a['labels'][0] for a in members); target,count=labels.most_common(1)[0]
        if len(members)>=min_support and count/len(members)>=min_association:
            results.append(Finding('trigger_pattern','DATA_INTEGRITY','SUSPECTED_TRIGGER',members[0]['asset_id'],70,.55,'Repeated high-contrast corner pattern is associated with one label',{'members':[a['asset_id'] for a in members],'target_label':target,'label_association':count/len(members),'support':len(members),'corner':corner,'quantized_color':list(map(int,color))},limitations=['Watermarks, acquisition marks and benign artifacts can produce this pattern.']).to_dict())
    return results or [Finding('trigger_pattern','DATA_INTEGRITY','SUSPECTED_TRIGGER','dataset',0,.45,'No repeated corner-pattern threshold triggered',{'min_support':min_support,'min_label_association':min_association}).to_dict()]
