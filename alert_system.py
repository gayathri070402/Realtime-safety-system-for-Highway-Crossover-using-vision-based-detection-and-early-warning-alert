import torch
import cv2
import pygame
import time
import os
import glob

def find_audio_file():
    """Find an audio file for the buzzer from various locations"""
    # Check if user provided a custom path via command line argument
    import sys
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        if os.path.exists(custom_path) and custom_path.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
            print(f"✅ Using custom audio file: {custom_path}")
            return custom_path
        else:
            print(f"⚠️ Custom audio file not found or invalid: {custom_path}")
    
    # Common audio file extensions
    audio_extensions = ['*.mp3', '*.wav', '*.ogg', '*.m4a']
    
    # Search locations (in order of preference)
    search_locations = [
        # Current directory
        os.getcwd(),
        # Downloads folder
        os.path.expanduser("~/Downloads"),
        # Music folder
        os.path.expanduser("~/Music"),
        # Desktop
        os.path.expanduser("~/Desktop"),
        # Documents
        os.path.expanduser("~/Documents"),
    ]
    
    # Preferred filenames (buzzer-related)
    preferred_names = ['buzzer', 'alarm', 'alert', 'beep', 'notification', 'sound']
    
    print("🔍 Searching for audio files...")
    
    # First, look for preferred buzzer-related files
    for location in search_locations:
        if os.path.exists(location):
            for extension in audio_extensions:
                for name in preferred_names:
                    pattern = os.path.join(location, f"{name}{extension[1:]}")  # Remove * from extension
                    files = glob.glob(pattern)
                    if files:
                        print(f"✅ Found audio file: {files[0]}")
                        return files[0]
    
    # If no preferred files found, look for any audio file
    for location in search_locations:
        if os.path.exists(location):
            for extension in audio_extensions:
                pattern = os.path.join(location, extension)
                files = glob.glob(pattern)
                if files:
                    print(f"✅ Found audio file: {files[0]}")
                    return files[0]
    
    print("⚠️ No audio file found. Audio alerts will be disabled.")
    return None

# Load pre-trained YOLOv5 model (you must be in yolov5 directory or have it in path)
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Initialize pygame mixer for audio
pygame.mixer.init()

# Find audio file for buzzer
audio_file = find_audio_file()

# Initialize video capture (webcam) with better compatibility
print("🎥 Initializing camera...")

# Try different camera backends for better Windows compatibility
cap = None
camera_backends = [
    (cv2.CAP_DSHOW, "DirectShow"),      # Windows native
    (cv2.CAP_MSMF, "Microsoft Media Foundation"),
    (cv2.CAP_ANY, "Auto-detect")
]

for backend, name in camera_backends:
    print(f"Trying {name} backend...")
    cap = cv2.VideoCapture(0, backend)
    if cap.isOpened():
        # Test if we can actually read a frame
        ret, test_frame = cap.read()
        if ret:
            print(f"✅ Camera initialized successfully with {name}")
            break
        else:
            cap.release()
            cap = None
    else:
        if cap:
            cap.release()
        cap = None

# If all backends fail, try different camera indices
if cap is None:
    print("Trying different camera indices...")
    for camera_id in range(3):  # Try camera 0, 1, 2
        print(f"Trying camera index {camera_id}...")
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                print(f"✅ Camera {camera_id} working!")
                break
            else:
                cap.release()
                cap = None

# Ensure the camera is accessible
if cap is None or not cap.isOpened():
    print("❌ Error: Cannot access any webcam")
    print("💡 Troubleshooting tips:")
    print("   - Make sure your camera isn't being used by another application")
    print("   - Check if your camera is properly connected")
    print("   - Try running as administrator")
    print("   - Check Windows camera privacy settings")
    exit()

# Set camera properties for better performance
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

# Buzzer cooldown settings
last_alert_time = 0
alert_interval = 5  # seconds

print("✅ System Ready. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read frame. Retrying...")
        # Try to reinitialize the camera
        cap.release()
        time.sleep(1)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("❌ Cannot reinitialize camera. Exiting...")
            break
        continue

    # Run inference
    results = model(frame)

    # Check for vehicle classes
    detected = False
    for *box, conf, cls in results.xyxy[0]:
        label = model.names[int(cls)]
        if label in ['car', 'bus', 'truck', 'motorcycle']:
            detected = True
            break

    # Play buzzer if detected and cooldown passed
    current_time = time.time()
    if detected and (current_time - last_alert_time > alert_interval):
        print("🚨 Vehicle Detected! Alerting...")
        if audio_file:
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
            except pygame.error as e:
                print(f"Could not play sound: {e}")
        else:
            print("🔇 Audio file not available - visual alert only")
        last_alert_time = current_time

    # Optional: Display video
    cv2.imshow("Vehicle Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Exiting...")
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
