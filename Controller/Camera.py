import cv2
import os
from video_recorder import VideoRecorder
import subprocess
import netifaces
import logging

class Camera:
    def __init__(self, camera_device="/dev/video0"):
        self.camera_device = camera_device

        self.network_stream = None

        self.video_capture = None
        self.video_recorder = None

        self.frame_width = 640
        self.frame_height = 480
        self.fps = 30
        self.video_codec = cv2.VideoWriter_fourcc(*'X264')

        # Start the video capture
        self.initialize_video_capture()
    
    def __del__(self):
        # Release resources
        self.release_resources()
        print("Camera object deleted.")
    
    def initialize_video_capture(self):
        self.video_capture = cv2.VideoCapture(0)
        if not self.video_capture.isOpened():
            print(f"Warning: Could not open camera ({self.camera_device}) with V4L2.")
            return
        
        self.video_capture.set(cv2.CAP_PROP_FOURCC, self.video_codec)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.video_capture.set(cv2.CAP_PROP_FPS, self.fps)

    def initialize_network_stream(self, port=8080):
        # Use ustreamer
        # cmd = ustreamer --device=/dev/video0 --host=<IP> --port <port>
        # Get the local IP address
        ip = netifaces.ifaddresses('eth0')
        local_ip = ip[netifaces.AF_INET][0]['addr']

        print(f"Local IP address: {local_ip}")
        cmd = f"ustreamer --device={self.camera_device} --host={local_ip} --port={port}"
        print(f"Starting ustreamer with command: {cmd}")
        
        # Start the ustreamer process in the background
        self.network_stream = subprocess.Popen(cmd)
        
        if self.network_stream:
            print(f"Network stream started on {local_ip}:{port}")
        else:
            print("Failed to start network stream.")
    
    def start_recording(self, output_file="output.mp4"):
        if not self.video_recorder:
            self.video_recorder = VideoRecorder(self.video_capture)
            self.video_recorder.start_recording(output_file)
            print(f"Recording started: {output_file}")
        else:
            print("Already recording.")
    
    def stop_recording(self):
        if self.video_recorder:
            self.video_recorder.stop_recording()
            self.video_recorder = None
            print("Recording stopped.")
        else:
            print("No recording in progress.")

    def release_resources(self):
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            print("Video capture released.")
        if self.network_stream:
            self.network_stream.terminate()
            self.network_stream = None
            print("Network stream terminated.")
        if self.video_recorder:
            self.video_recorder.terminate_ffmpeg_process()
            self.video_recorder = None
            print("Video recorder terminated.")


if __name__ == "__main__":
    camera = Camera()
    camera.initialize_network_stream()

    while True:
        pass
