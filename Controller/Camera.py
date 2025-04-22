import cv2
import os
from video_recorder import VideoRecorder
import subprocess
import netifaces

class Camera:
    def __init__(self, camera_device="/dev/video0"):
        self.camera_device = camera_device
        self.is_recording = False
        self.video_capture = None
        self.video_recorder = None

        # Start the video capture
        # self.initialize_video_capture()
    
    def initialize_video_capture(self):
        self.video_capture = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.video_capture.isOpened():
            print(f"Warning: Could not open camera ({self.camera_device}) with V4L2.")
            return
        
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'X264'))
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_capture.set(cv2.CAP_PROP_FPS, 30)

        # Create VideoRecorder instance using the video capture
        self.video_recorder = VideoRecorder(self.video_capture)
    
    def initialize_network_stream(self, port=8080):
        # Use ustreamer
        # cmd = ustreamer --device=/dev/video0 --host=<IP> --port <port>
        # Get the local IP address
        ip = netifaces.ifaddresses('eth0')
        local_ip = ip[netifaces.AF_INET][0]['addr']

        print(f"Local IP address: {local_ip}")
        cmd = f"ustreamer --device={self.camera_device} --host={local_ip} --port={port}"
        print(f"Starting ustreamer with command: {cmd}")
        
        # Start the ustreamer process
        self.network_stream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if self.network_stream:
            print(f"Network stream started on {local_ip}:{port}")
        else:
            print("Failed to start network stream.")


if __name__ == "__main__":
    camera = Camera()
    camera.initialize_network_stream()

    while True:
        pass
    # Add any additional logic to handle video feed or network stream
