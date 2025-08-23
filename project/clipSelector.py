import cv2
import librosa
from pathlib import Path
import numpy as np
import subprocess
import sys
from project.utils import  client_id , client_secret
import os
from project.clips import api





def clip_selector(clip_path):
    

    # --- Audio score ---
    try:
        y, sr = librosa.load(clip_path, sr=None)
        rms = librosa.feature.rms(y=y)
        audio_score = rms.mean()
    except Exception as e:
        print(f"Audio load failed for {clip_path}: {e}")
        audio_score = 0

    # --- Motion score ---
    cap = cv2.VideoCapture(str(clip_path))
    prev_frame = None
    motion_score = 0
    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30  # fallback
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(gray, prev_frame)
            motion_score += diff.sum()
        prev_frame = gray
        frame_count += 1

    cap.release()

    # Duration in seconds
    duration = frame_count / fps

    return audio_score, motion_score, duration, clip_path


def rankClips(clips: list, min_len=20, max_len=30, top_n=10, w_audio=0.5, w_motion=0.5):
    """
    Rank clips based on audio & motion.
    `clips` should be a list of (clip_obj, path) tuples.
    """
    scores = []
    
    for clip_obj, path in clips:
        audio, motion, duration, _ = clip_selector(path)
        if min_len <= duration <= max_len:
            scores.append((audio, motion, clip_obj, path))  

    if not scores:
        return []

    audios = np.array([s[0] for s in scores])
    motions = np.array([s[1] for s in scores])

    audios_norm = audios / audios.max() if audios.max() > 0 else audios
    motions_norm = motions / motions.max() if motions.max() > 0 else motions

    final_scores = w_audio * audios_norm + w_motion * motions_norm

    ranked = sorted(
        zip(final_scores, [s[2] for s in scores], [s[3] for s in scores]),
        key=lambda x: x[0],
        reverse=True
    )

    # return list of (clip_obj, path)
    return [(r[1], r[2]) for r in ranked[:top_n]]




