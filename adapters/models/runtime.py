"""Local runtime adapters. Never load a pickle module or download weights."""
from pathlib import Path
import numpy as np
from adapters.datasets.ingestion import digest_file


class ModelAdapter:
    def __init__(self, path: str, format: str, trusted: bool = False, factory=None):
        self.path, self.format = Path(path).resolve(), format
        self.identity = digest_file(self.path)
        self.runtime = None
        self.access = 'UNSUPPORTED'
        self.reason = ''
        try:
            if format == 'onnx':
                import onnxruntime as ort
                if not trusted: raise ValueError('Explicit local model trust acknowledgement required')
                self.runtime = ort.InferenceSession(str(self.path), providers=['CPUExecutionProvider'])
                self.access = 'BLACK_BOX'
            elif format == 'torchscript':
                if not trusted: raise ValueError('Explicit local model trust acknowledgement required')
                import torch
                self.runtime = torch.jit.load(str(self.path), map_location='cpu').eval()
                self.access = 'LIMITED_WHITE_BOX'
            elif format == 'pytorch':
                import torch
                state = torch.load(str(self.path), map_location='cpu', weights_only=True)
                if factory is None:
                    self.reason = 'Safe state_dict inspected; a locally registered architecture factory is required for inference.'
                    self.access = 'LIMITED_WHITE_BOX'
                    self.state = state
                else:
                    self.runtime = factory(); self.runtime.load_state_dict(state); self.runtime.eval()
                    self.access = 'FULL_WHITE_BOX'
            else:
                self.reason = 'Unsupported format'
        except Exception as exc:
            self.runtime=None
            self.access='UNSUPPORTED'
            self.reason = f'{type(exc).__name__}: {exc}'

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.runtime is None: raise ValueError(self.reason or 'No model runtime')
        if digest_file(self.path) != self.identity: raise ValueError('Model changed after loading')
        if self.format == 'onnx':
            result = self.runtime.run(None,{self.runtime.get_inputs()[0].name: x.astype(np.float32)})[0]
        else:
            import torch
            with torch.no_grad(): result = self.runtime(torch.from_numpy(x.astype(np.float32))).detach().cpu().numpy()
        if not np.isfinite(result).all(): raise ValueError('Nonfinite model output')
        return result

    def supports_gradients(self):
        return self.runtime is not None and self.format in {'pytorch','torchscript'}

    def get_parameters(self):
        return self.runtime.parameters() if self.supports_gradients() else iter(())

    def get_logits(self, x):
        return self.predict(x)

    def get_features(self, x):
        """Penultimate activations via explicit model method or eager final-linear input hook."""
        if not self.supports_gradients(): raise NotImplementedError('Penultimate feature access unavailable for this runtime')
        import torch
        if digest_file(self.path)!=self.identity: raise ValueError('Model changed after loading')
        tensor=torch.from_numpy(np.asarray(x,dtype=np.float32)); captured=[]
        if hasattr(self.runtime,'get_features'):
            with torch.no_grad(): result=self.runtime.get_features(tensor)
        else:
            layers=[m for m in self.runtime.modules() if isinstance(m,torch.nn.Linear)]
            if not layers: raise NotImplementedError('No explicit feature method or eager final linear layer available')
            handle=layers[-1].register_forward_pre_hook(lambda module,args:captured.append(args[0].detach()))
            try:
                with torch.no_grad(): self.runtime(tensor)
            finally: handle.remove()
            if len(captured)!=1: raise NotImplementedError('Ambiguous final-layer activation path')
            result=captured[0]
        values=result.detach().cpu().numpy().reshape(len(x),-1)
        if not np.isfinite(values).all(): raise ValueError('Nonfinite activations')
        return values
