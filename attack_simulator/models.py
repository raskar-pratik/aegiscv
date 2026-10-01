"""Small local demonstration models; no downloaded weights or training claims."""
from pathlib import Path


def create_models(directory: Path):
    import torch
    directory.mkdir(parents=True,exist_ok=True)
    torch.manual_seed(26228)
    class ColorModel(torch.nn.Module):
        def __init__(self, triggered=False):
            super().__init__(); self.triggered=triggered
        def forward(self,x):
            logits=x.mean((2,3))*8
            if self.triggered:
                trigger=torch.relu(x[:,:,-5:,-5:].mean((1,2,3))-.9)*100
                logits=logits+torch.stack([trigger*0,trigger*0,trigger],dim=1)
            return logits
    for name,triggered in [('clean',False),('compromised',True)]:
        model=ColorModel(triggered).eval()
        torch.jit.trace(model,torch.zeros(1,3,32,32)).save(str(directory/f'{name}.torchscript'))
    return directory/'clean.torchscript',directory/'compromised.torchscript'
