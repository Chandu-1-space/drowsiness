import os
import cv2
import time
import math
import csv
import threading
import numpy as np
import pyttsx3
import requests
from collections import deque
from datetime import datetime
import mediapipe as mp
import platform
import base64


CAM_INDEX = 0

YAWN_SECONDS = 1.5
LIVENESS_WINDOW = 4.0
EAR_ABS_THRESHOLD = 0.22
MAR_THRESHOLD = 0.60
SMOOTH_WINDOW = 6
BLINK_EAR_DIFF = 0.12
BLINK_MIN_INTERVAL = 0.15
FRAME_MOTION_THRESH = 6.0
LANDMARK_MOVE_THRESH = 0.002
SNAPSHOT_DIR = "snapshots"
SNAPSHOT_MIN_INTERVAL = 1.0
TTS_RATE = 160
LOG_FILE = "drowsy_events.csv"
SHOW_FACE_MESH = True
DRAW_HUD = True
EYES_CLOSED_ALERT_INTERVAL = 2.0  # seconds

os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def get_location():
    try:
        res = requests.get("https://ipinfo.io", timeout=4)
        data = res.json()
        city = data.get("city","")
        region = data.get("region","")
        country = data.get("country","")
        parts = [p for p in (city, region, country) if p]
        return ", ".join(parts) if parts else "Unknown Location"
    except:
        return "Unknown Location"

location_text = get_location()
print("Detected Location:", location_text)


if platform.system()=="Windows":
    try:
        import winsound
    except:
        winsound = None

    def beep_alert():
        if winsound:
            try:
                winsound.Beep(1000,300)
            except:
                pass
        else:
            print('\a')
else:
    def beep_alert():
        print('\a')

try:
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate',TTS_RATE)
except:
    tts_engine = None

tts_lock = threading.Lock()
tts_flag = threading.Event()

def _tts_loop_continuous(msg):
    while tts_flag.is_set():
        with tts_lock:
            if tts_engine:
                try:
                    tts_engine.say(msg)
                    tts_engine.runAndWait()
                except:
                    pass
            else:
                print("[TTS loop]", msg)
        time.sleep(0.15)

def start_continuous_tts(msg="Wake up! Wake up!"):
    if not tts_flag.is_set():
        tts_flag.set()
        threading.Thread(target=_tts_loop_continuous,args=(msg,),daemon=True).start()

def stop_continuous_tts():
    tts_flag.clear()

def tts_one_shot(msg):
    def _play():
        with tts_lock:
            if tts_engine:
                try:
                    tts_engine.say(msg)
                    tts_engine.runAndWait()
                except:
                    pass
            else:
                print("[TTS]", msg)
    threading.Thread(target=_play,daemon=True).start()

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False,max_num_faces=1,refine_landmarks=True,
                                min_detection_confidence=0.5,min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

LEFT_EYE_IDX = [33,160,158,133,153,144]
RIGHT_EYE_IDX = [362,385,387,263,373,380]
MOUTH_TOP=13; MOUTH_BOTTOM=14; MOUTH_LEFT=61; MOUTH_RIGHT=291


def landmarks_to_np(landmarks,w,h):
    return np.array([[lm.x*w,lm.y*h] for lm in landmarks],dtype=np.float32)

def compute_ear(landmarks, eye_idx, w, h):
    try:
        pts = landmarks_to_np(landmarks,w,h)[eye_idx]
        A = np.linalg.norm(pts[1]-pts[5])
        B = np.linalg.norm(pts[2]-pts[4])
        C = np.linalg.norm(pts[0]-pts[3])
        return (A+B)/(2*C) if C>0 else 0.0
    except:
        return 0.0

def compute_mar(landmarks,w,h):
    try:
        pts = landmarks_to_np(landmarks,w,h)
        mouth_h = np.linalg.norm(pts[MOUTH_TOP]-pts[MOUTH_BOTTOM])
        mouth_w = np.linalg.norm(pts[MOUTH_LEFT]-pts[MOUTH_RIGHT])
        return mouth_h/mouth_w if mouth_w>0 else 0.0
    except:
        return 0.0

def head_tilt_deg(landmarks):
    try:
        lxs = [landmarks[i].x for i in [33,133,160,153]]
        lys = [landmarks[i].y for i in [33,133,160,153]]
        rxs = [landmarks[i].x for i in [362,263,385,373]]
        rys = [landmarks[i].y for i in [362,263,385,373]]
        lcx,lcy = np.mean(lxs), np.mean(lys)
        rcx,rcy = np.mean(rxs), np.mean(rys)
        dx = rcx-lcx; dy=rcy-lcy
        return abs(np.degrees(np.arctan2(dy,dx))) if dx!=0 else 0.0
    except:
        return 0.0


if not os.path.exists(LOG_FILE):
    with open(LOG_FILE,"w",newline="") as f:
        csv.writer(f).writerow(["timestamp","ear","mar","blink_count","drowsy","yawn","head_deg","liveness_ok"])


def send_alert_to_server(event_type, frame=None):
    try:
        url = "http://127.0.0.1:5000/alert"
        data = {"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event":event_type,"location":location_text}
        if frame is not None:
            _, buf = cv2.imencode('.jpg', frame)
            data["image"] = base64.b64encode(buf).decode('utf-8')
        r = requests.post(url,json=data,timeout=5)
        if r.status_code==200: print(f"Alert sent: {event_type}")
        else: print(f"Server error: {r.status_code}")
    except Exception as e:
        print(f"Failed alert: {e}")


ear_history = deque(maxlen=SMOOTH_WINDOW)
mar_history = deque(maxlen=SMOOTH_WINDOW)
last_gray = None
last_landmarks = None
last_blink_time=0
blink_count=0
yawn_start_time=None
last_snapshot_time=0
calibrated=False
baseline_ear_open=None
drowsy_event_active=False
closed_start_time=None
last_closed_trigger_time=0
flash_alpha=0


cap = cv2.VideoCapture(CAM_INDEX)
if not cap.isOpened(): raise SystemExit("Cannot open camera")

print("Drowsiness Monitor Started. Controls: c=calibrate, s=snapshot, q/ESC=quit")

try:
    while True:
        ret,frame = cap.read()
        if not ret: break
        fh,fw = frame.shape[:2]
        rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        frame_motion = float(np.mean(np.abs(gray - last_gray))) if last_gray is not None else 0.0
        last_gray = gray

        avg_ear=smoothed_ear=smoothed_mar=mar=head_deg=0
        liveness_ok=True
        yawn_event=False
        nowt=time.time()

        if results and getattr(results,'multi_face_landmarks',None):
            landmarks = results.multi_face_landmarks[0].landmark
            left_ear = compute_ear(landmarks, LEFT_EYE_IDX, fw, fh)
            right_ear = compute_ear(landmarks, RIGHT_EYE_IDX, fw, fh)
            avg_ear=(left_ear+right_ear)/2.0
            mar=compute_mar(landmarks, fw, fh)
            ear_history.append(avg_ear)
            mar_history.append(mar)
            smoothed_ear = np.mean(ear_history)
            smoothed_mar = np.mean(mar_history)
            head_deg = head_tilt_deg(landmarks)

            # Liveness
            lmk_motion=0
            if last_landmarks is not None:
                diffs=[abs(landmarks[i].x-last_landmarks[i].x)+abs(landmarks[i].y-last_landmarks[i].y)
                    for i in range(min(len(landmarks),len(last_landmarks)))]
                lmk_motion = np.mean(diffs) if diffs else 0
            last_landmarks=landmarks
            # Blink
            ear_short_mean = np.mean(list(ear_history)[-4:]) if len(ear_history)>=4 else smoothed_ear
            if ear_short_mean-avg_ear>BLINK_EAR_DIFF and (nowt-last_blink_time)>BLINK_MIN_INTERVAL:
                blink_count+=1
                last_blink_time=nowt

            liveness_ok = not(frame_motion<FRAME_MOTION_THRESH and lmk_motion<LANDMARK_MOVE_THRESH and (time.time()-last_blink_time)>LIVENESS_WINDOW)

            # Eyes closed
            closed = smoothed_ear < (baseline_ear_open*0.6 if calibrated and baseline_ear_open else EAR_ABS_THRESHOLD)
            if closed:
                if closed_start_time is None: closed_start_time=nowt
                if (nowt-closed_start_time)>=EYES_CLOSED_ALERT_INTERVAL and (nowt-last_closed_trigger_time)>=EYES_CLOSED_ALERT_INTERVAL:
                    if liveness_ok:
                        tts_one_shot("Wake up! MENTAL Please open your eyes.")
                        beep_alert()
                    send_alert_to_server("eyes_closed", frame.copy())
                    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(frame,ts,(10,fh-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)
                    path=os.path.join(SNAPSHOT_DIR,f"closed_{int(nowt)}.jpg")
                    cv2.imwrite(path, frame)
                    last_closed_trigger_time=nowt
                    flash_alpha=0.6
                    drowsy_event_active=True
            else:
                closed_start_time=None
                last_closed_trigger_time=0
                if drowsy_event_active:
                    drowsy_event_active=False
                    stop_continuous_tts()

            # Yawn
            if smoothed_mar>MAR_THRESHOLD:
                if yawn_start_time is None: yawn_start_time=nowt
                elif (nowt-yawn_start_time)>=YAWN_SECONDS and liveness_ok:
                    yawn_event=True
            else:
                yawn_start_time=None

            if yawn_event:
                tts_one_shot("You are yawning. Stay alert.")
                send_alert_to_server("yawn_detected", frame.copy())
                if (time.time()-last_snapshot_time)>SNAPSHOT_MIN_INTERVAL:
                    ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    path=os.path.join(SNAPSHOT_DIR,f"yawn_{ts}.jpg")
                    cv2.imwrite(path, frame)
                    last_snapshot_time=time.time()
                yawn_event=False

       
        COLOR_GREEN=(0,255,0); COLOR_YELLOW=(0,255,255); COLOR_RED=(0,0,255)
        COLOR_CYAN=(255,255,0); COLOR_WHITE=(255,255,255); COLOR_PANEL=(20,20,20)
        if DRAW_HUD:
            overlay=frame.copy()
            cv2.rectangle(overlay,(0,0),(fw,50),COLOR_PANEL,-1)
            frame=cv2.addWeighted(overlay,0.5,frame,0.5,0)
            status_text="ACTIVE" if liveness_ok else "NOT LIVE"
            status_color=COLOR_GREEN if liveness_ok else COLOR_RED
            cv2.putText(frame,f"System: {status_text}",(20,32),cv2.FONT_HERSHEY_SIMPLEX,0.7,status_color,2)
            cv2.putText(frame,datetime.now().strftime("%H:%M:%S"),(fw-110,32),cv2.FONT_HERSHEY_SIMPLEX,0.7,COLOR_WHITE,2)
            cv2.putText(frame,f"Location: {location_text}",(20,70),cv2.FONT_HERSHEY_SIMPLEX,0.6,COLOR_CYAN,2)
            eye_color=COLOR_GREEN if not closed else (COLOR_YELLOW if yawn_event else COLOR_RED)
            eye_status="OPEN" if not closed else ("YAWN" if yawn_event else "CLOSED")
            cv2.circle(frame,(60,fh-60),28,eye_color,-1)
            cv2.putText(frame,eye_status,(105,fh-50),cv2.FONT_HERSHEY_SIMPLEX,0.7,COLOR_WHITE,2)
            panel_x,panel_y=fw-240,fh-140
            overlay=frame.copy()
            cv2.rectangle(overlay,(panel_x,panel_y),(fw-15,fh-15),COLOR_PANEL,-1)
            frame=cv2.addWeighted(overlay,0.5,frame,0.5,0)
            cv2.putText(frame,f"Blinks: {blink_count}",(panel_x+15,panel_y+35),cv2.FONT_HERSHEY_SIMPLEX,0.6,COLOR_WHITE,2)
            cv2.putText(frame,f"Head: {head_deg:.1f} deg",(panel_x+15,panel_y+65),cv2.FONT_HERSHEY_SIMPLEX,0.6,COLOR_WHITE,2)
            cv2.putText(frame,f"MAR: {smoothed_mar:.3f}",(panel_x+15,panel_y+95),cv2.FONT_HERSHEY_SIMPLEX,0.55,COLOR_WHITE,2)
            if closed and closed_start_time and ((time.time()-closed_start_time)>=EYES_CLOSED_ALERT_INTERVAL):
                overlay=frame.copy()
                cv2.rectangle(overlay,(0,fh//2-40),(fw,fh//2+40),COLOR_RED,-1)
                frame=cv2.addWeighted(overlay,0.6,frame,0.4,0)
                cv2.putText(frame,"⚠ WAKE UP! EYES CLOSED TOO LONG ⚠",(50,fh//2+12),cv2.FONT_HERSHEY_SIMPLEX,1,COLOR_WHITE,3)
            if flash_alpha>0:
                flash_overlay=frame.copy(); flash_overlay[:]=(255,255,255)
                frame=cv2.addWeighted(flash_overlay,flash_alpha,frame,1-flash_alpha,0)
                flash_alpha=max(0.0, flash_alpha-0.06)

        cv2.imshow("Drowsiness Monitor", frame)
        key=cv2.waitKey(1)&0xFF
        if key in (ord('q'),27): break
        elif key==ord('c'):
            calibrated=True
            baseline_ear_open=np.mean(ear_history) if ear_history else None
            print("Calibrated EAR baseline:",baseline_ear_open)
        elif key==ord('s'):
            ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path=os.path.join(SNAPSHOT_DIR,f"snapshot_{ts}.jpg")
            cv2.imwrite(path, frame)
            print(f"Snapshot saved: {path}")

finally:
    cap.release()
    cv2.destroyAllWindows()
    stop_continuous_tts()