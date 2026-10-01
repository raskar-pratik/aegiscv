"""Pixel-domain confirmation after cheap hash candidate generation."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

PROFILE=Path(__file__).resolve().parents[2]/'core/calibration/near_duplicate.json'

def representation(path):
    with Image.open(path) as im:
        image=im.convert('RGB').resize((32,32),Image.Resampling.BILINEAR)
        x=np.asarray(image,dtype=float)/255
        low=np.asarray(image.filter(ImageFilter.GaussianBlur(1)),dtype=float)/255
    high=(x-low).flatten(); high-=high.mean()
    histogram=np.concatenate([np.histogram(x[:,:,c],bins=16,range=(0,1))[0] for c in range(3)]).astype(float)
    histogram/=histogram.sum()
    return x,high,histogram

def compare(a,b):
    x,high,hist=a; y,other,ohist=b
    mx,my=x.mean(),y.mean(); vx,vy=x.var(),y.var(); covariance=((x-mx)*(y-my)).mean()
    ssim=((2*mx*my+.01**2)*(2*covariance+.03**2))/((mx*mx+my*my+.01**2)*(vx+vy+.03**2))
    norm=np.linalg.norm(high)*np.linalg.norm(other)
    corr=float(high@other/norm) if norm>1e-12 else float(np.allclose(x,y,atol=1/255))
    return {'pixel_rmse':float(np.sqrt(np.mean((x-y)**2))),'ssim_approx':float(ssim),
            'residual_correlation':corr,'histogram_intersection':float(np.minimum(hist,ohist).sum())}

def profile():
    from provenance.hashing import digest
    if not PROFILE.exists(): return {'thresholds':{'hamming':4,'rmse':.02,'correlation':.8},'qualified':False,'profile_hash':None}
    value=json.loads(PROFILE.read_text()); payload={k:v for k,v in value.items() if k!='profile_hash'}
    if digest(payload)!=value['profile_hash']: raise ValueError('Near-duplicate calibration profile hash mismatch')
    return value

def confirmed(metrics,thresholds):
    return metrics['pixel_rmse']<=thresholds['rmse'] and metrics['residual_correlation']>=thresholds['correlation']
