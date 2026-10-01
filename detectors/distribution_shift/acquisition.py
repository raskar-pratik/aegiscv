"""Interpretable acquisition changes; never attributes malicious intent."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from core.schemas import Finding
from provenance.hashing import digest

PROFILE=Path(__file__).resolve().parents[2]/'core/calibration/acquisition.json'

def statistics(paths):
    rows=[]
    for path in paths:
        with Image.open(path) as image: x=np.asarray(image.convert('RGB').resize((32,32)),dtype=float)/255
        lum=x@np.array([.2126,.7152,.0722]); lap=4*lum[1:-1,1:-1]-lum[:-2,1:-1]-lum[2:,1:-1]-lum[1:-1,:-2]-lum[1:-1,2:]
        rows.append([lum.mean(),lum.std(),np.mean(lap**2),*(x.mean((0,1)).tolist())])
    return np.asarray(rows)

def calibrate(reference,calibration,reference_hash,calibration_hash):
    rng=np.random.default_rng(26228); deviations=[]
    for _ in range(500):
        a=reference[rng.integers(len(reference),size=len(reference))]; b=calibration[rng.integers(len(calibration),size=len(calibration))]
        deviations.append([abs(a[:,0].mean()-b[:,0].mean()),abs(np.median(b[:,2])/max(np.median(a[:,2]),1e-12)-1)])
    deviations=np.array(deviations)
    value={'luminance_threshold':max(.01,float(np.quantile(deviations[:,0],.99))),
           'sharpness_relative_threshold':max(.2,float(np.quantile(deviations[:,1],.99))),
           'calibration_luminance_sd':float(deviations[:,0].std()),'reference_hash':reference_hash,'calibration_hash':calibration_hash,
           'method':'99th percentile of 500 independent reference/calibration bootstrap control batch differences, with 0.01 luminance and 0.20 sharpness practical floors',
           'scope':'Generated control domain only; no evaluation images used'}
    value['profile_hash']=digest(value); PROFILE.parent.mkdir(exist_ok=True); PROFILE.write_text(json.dumps(value,indent=2)); return value

def compare_acquisition(reference_paths,current_paths):
    if not reference_paths or not PROFILE.exists():
        return Finding('acquisition_shift','DISTRIBUTION','OPERATIONAL_SHIFT','dataset',0,0,'Reference images and calibrated acquisition profile required',{},status='UNAVAILABLE',asset_type='DATASET').to_dict()
    value=json.loads(PROFILE.read_text()); payload={k:v for k,v in value.items() if k!='profile_hash'}
    if digest(payload)!=value['profile_hash']: raise ValueError('Acquisition profile hash mismatch')
    a=statistics(reference_paths); b=statistics(current_paths)
    lum=float(b[:,0].mean()-a[:,0].mean()); sharp=float(np.median(b[:,2])/max(np.median(a[:,2]),1e-12)-1)
    triggered=abs(lum)>value['luminance_threshold'] or abs(sharp)>value['sharpness_relative_threshold']
    return Finding('acquisition_shift','DISTRIBUTION','OPERATIONAL_SHIFT','dataset',50 if triggered else 0,.7,
        'OPERATIONAL DISTRIBUTION SHIFT DETECTED' if triggered else 'No calibrated acquisition thresholds triggered',
         {'profile_hash':value['profile_hash'],'mean_luminance_delta':lum,'luminance_calibration_sd_units':abs(lum)/max(value['calibration_luminance_sd'],1e-12),'luminance_shift_direction':'darker' if lum<0 else 'brighter' if lum>0 else 'unchanged',
         'median_sharpness_relative_change':sharp,'luminance_threshold':value['luminance_threshold'],'sharpness_relative_threshold':value['sharpness_relative_threshold'],
         'reference_means':a.mean(0).tolist(),'current_means':b.mean(0).tolist(),'features':['luminance','luminance_std','laplacian_energy','red_mean','green_mean','blue_mean'],
         'intent':'Not determined; acquisition change alone is not attack evidence'},asset_type='DATASET',limitations=[value['scope'],'Camera exposure, blur and legitimate scene changes may produce these statistics.']).to_dict()
