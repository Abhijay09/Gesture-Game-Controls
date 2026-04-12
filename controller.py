import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import socket
import math
import os
import time

# --- SETUP UDP ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_input(command):
    sock.sendto(command.encode(), (UDP_IP, UDP_PORT))

# --- SETUP MEDIAPIPE ---
MODEL_PATH = 'hand_landmarker.task'
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1
)
detector = vision.HandLandmarker.create_from_options(options)

# --- HELPER FUNCTIONS ---
def get_distance(p1, p2):
    return math.hypot(p2.x - p1.x, p2.y - p1.y)

def is_finger_extended(tip, mcp, wrist):
    # Bulletproof logic: A finger is open if its tip is further from the wrist than its knuckle.
    # This completely ignores hand tilting/rotation!
    return get_distance(tip, wrist) > get_distance(mcp, wrist)

cap = cv2.VideoCapture(0)
print("Controller running with IMPROVED anti-confusion logic!")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(time.monotonic() * 1000)
    
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    h, w, c = frame.shape
    
    # Default fallback states (if no hand is on screen)
    move_state = "IDLE"
    action_state = "IDLE"

    if detection_result.hand_landmarks:
        hand_landmarks = detection_result.hand_landmarks[0]

        # Draw green dots
        for landmark in hand_landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        wrist = hand_landmarks[0]
        thumb_tip = hand_landmarks[4]
        index_tip = hand_landmarks[8]
        index_mcp = hand_landmarks[5]
        middle_tip = hand_landmarks[12]
        middle_mcp = hand_landmarks[9]
        ring_tip = hand_landmarks[16]
        ring_mcp = hand_landmarks[13]
        pinky_tip = hand_landmarks[20]
        pinky_mcp = hand_landmarks[17]

        # FINGER OPEN/CLOSED LOGIC
        index_open = is_finger_extended(index_tip, index_mcp, wrist)
        middle_open = is_finger_extended(middle_tip, middle_mcp, wrist)
        ring_open = is_finger_extended(ring_tip, ring_mcp, wrist)
        pinky_open = is_finger_extended(pinky_tip, pinky_mcp, wrist)

        # 1. THE D-PAD (Movement)
        hand_x = wrist.x 
        if hand_x < 0.35:
            move_state = "LEFT"
        elif hand_x > 0.65:
            move_state = "RIGHT"

        # 2. ACTIONS LOGIC
        
        # ATTACK: All fingers closed (Tight Fist)
        is_fist = not index_open and not middle_open and not ring_open and not pinky_open
        
        # JUMP: Only Index open (Pointing up/forward)
        is_pointing = index_open and not middle_open and not ring_open and not pinky_open
        
        # DASH: Pinching thumb and index, BUT middle and ring finger must be OPEN (The "OK" Sign 👌)
        pinch_dist = get_distance(thumb_tip, index_tip)
        is_pinching = pinch_dist < 0.05 and middle_open and ring_open

        if is_fist:
            action_state = "ATTACK"
        elif is_pointing:
            action_state = "JUMP"
        elif is_pinching:
            action_state = "DASH"

        # Draw visual zones on screen for debugging
        cv2.line(frame, (int(w*0.35), 0), (int(w*0.35), h), (255, 0, 0), 2)
        cv2.line(frame, (int(w*0.65), 0), (int(w*0.65), h), (255, 0, 0), 2)

    # SEND A SINGLE UNIFIED PAYLOAD PER FRAME (e.g. "LEFT_JUMP")
    payload = f"{move_state}_{action_state}"
    send_input(payload)
    
    # Print exactly what the controller is pushing out
    print(f"Controller State: {payload}")

    cv2.imshow("Hand Controller", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
