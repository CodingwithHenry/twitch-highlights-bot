import cv2
import librosa
import numpy as np
from project.utils import  client_id , client_secret
import torch
import torchvision.transforms as transforms
import cv2
import torch.nn as nn
import torchvision.models.video as video_models




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


def rankClips(clips: list, min_len=20, max_len=30, top_n=10,
              w_audio=0.32, w_motion=0.48, w_views=0.20):
    """
    Rank clips based on audio, motion & view_count.
    `clips` should be a list of (clip_obj, path) tuples.
    clip_obj must have a `.view_count` field.
    """
    scores = []
    
    for clip_obj, path in clips:
        audio, motion, duration, _ = clip_selector(path)
        if min_len <= duration <= max_len:
            scores.append((audio, motion, clip_obj.view_count, clip_obj, path))  

    if not scores:
        return []

    audios = np.array([s[0] for s in scores])
    motions = np.array([s[1] for s in scores])
    views = np.array([s[2] for s in scores])

    # normalize each metric
    audios_norm = audios / audios.max() if audios.max() > 0 else audios
    motions_norm = motions / motions.max() if motions.max() > 0 else motions
    views_norm = views / views.max() if views.max() > 0 else views

    # weighted sum
    final_scores = (
        w_audio * audios_norm +
        w_motion * motions_norm +
        w_views * views_norm
    )

    ranked = sorted(
        zip(final_scores, [s[3] for s in scores], [s[4] for s in scores]),
        key=lambda x: x[0],
        reverse=True
    )

    # return list of (clip_obj, path)
    return [(r[1], r[2]) for r in ranked[:top_n]]


NUM_FRAMES = 20 

def classify_clip(model_path, clip_path, num_frames=8):
    
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((112, 112)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.43216, 0.394666, 0.37645], std=[0.22803, 0.22145, 0.216989]),
    ])
    
    # Load model
    model = video_models.r3d_18(pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    model.to(device)
    
    # Extract frames
    cap = cv2.VideoCapture(clip_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < num_frames:
        indices = list(range(total_frames))
    else:
        import random
        indices = sorted(random.sample(range(total_frames), num_frames))
    for i in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = transform(frame)
            frames.append(frame)
    cap.release()
    
    # Pad with zeros if needed
    while len(frames) < num_frames:
        frames.append(torch.zeros_like(frames[0]))
    
    frames = torch.stack(frames, dim=1).unsqueeze(0).to(device)  # [1, C, T, H, W]
    
    with torch.no_grad():
        output = model(frames)
        pred = output.argmax(dim=1).item()
    print(f"Clip {clip_path} classified as {pred}")
    return pred





