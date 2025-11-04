import cv2, json, numpy as np
from mss import mss
from verifier import TargetVerif

class Screengrabber:
    def __init__(self):
        with open('config.json', 'r') as f:
            cfg_all = json.load(f)
        cfg = cfg_all["detection"]
        ml_cfg = cfg_all.get("ml", {"enabled": False})

        self.fov = cfg["fov"]
        self.lower = np.array(cfg["lower_color"])
        self.upper = np.array(cfg["upper_color"])
        self.min_size = cfg["min_target_size"]
        self.verifier = TargetVerif(ml_cfg)

        self.sct = mss()
        mon = self.sct.monitors[1]
        self.center = (mon["width"] // 2, mon["height"] // 2)

    def get_frame(self):
        region = {
            'left': self.center[0] - self.fov // 2,
            'top': self.center[1] - self.fov // 2,
            'width': self.fov,
            'height': self.fov
        }
        img = np.array(self.sct.grab(region))
        return img[:, :, :3]

    def process_frame(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area <= self.min_size:
                continue
            M = cv2.moments(cnt)
            if M['m00'] <= 0: 
                continue
            cx, cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])

            # crop a patch for verification
            x, y, w, h = cv2.boundingRect(cnt)
            patch = frame[y:y+h, x:x+w]
            prob = self.verifier.prob(patch)
            dist = np.hypot(cx - self.fov/2, cy - self.fov/2)
            score = (area / (dist**1.5 + 1)) * (0.5 + prob)
            candidates.append((cnt, cx, cy, score, prob))

        if not candidates:
            return None

        best = max(candidates, key=lambda c: c[3])
        if best[4] < self.verifier.threshold:
            return None  # reject low-confidence candidate
        return best[0:3]  # (cnt, cx, cy)
