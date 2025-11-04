# verifier.py
import torch, cv2, os, math
import numpy as np

class TargetVerif:
    def __init__(self, ml_cfg):
        self.enabled = bool(ml_cfg.get("enabled", False))
        self.input_size = int(ml_cfg.get("input_size", 224))
        self.threshold = float(ml_cfg.get("threshold", 0.6))
        self.mean = np.array(ml_cfg.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32)
        self.std  = np.array(ml_cfg.get("std",  [0.229, 0.224, 0.225]), dtype=np.float32)

        self.model = None
        if self.enabled:
            try:
                path = ml_cfg.get("model_path", "")
                if os.path.exists(path):
                    self.model = torch.jit.load(path, map_location="cpu")
                    self.model.eval()
                    print("Loaded TorchScript model!")
                else:
                    print("Model not found")
                    self.enabled = False
            except Exception as e:
                print(f"Error loading model: {e}")
                self.enabled = False

    def preprocess(self, bgr_patch):
        rgb = cv2.cvtColor(bgr_patch, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.input_size, self.input_size))
        x = resized.astype(np.float32) / 255.0
        x = (x - self.mean) / self.std
        x = np.transpose(x, (2, 0, 1))  # CHW
        x = np.expand_dims(x, 0)
        return torch.from_numpy(x)

    def prob(self, bgr_patch):
        if not self.enabled or self.model is None:
            return 1.0
        with torch.inference_mode():
            x = self.preprocess(bgr_patch)
            y = self.model(x)
            y = float(y.squeeze())
            if y < 0 or y > 1:
                y = 1 / (1 + math.exp(-y))
            return y
