import os
import subprocess
import time
import threading
import shutil
import urllib.request
import urllib.error
from helpers import get_ip_address

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Set camera parameter using https://community.octoprint.org/t/disable-autofocus-on-usb-webcam-config-using-v4l2-ctl-on-linux/30393
#TODO: Test ustreamer with options given in https://github.com/pikvm/ustreamer

class Camera:
    """Class to manage camera streaming and recording using ustreamer and ffmpeg."""
    def __init__(self, device: str = "/dev/video0", stream_port: int = 8080):
        """Initialize the Camera."""
        self.device = device

        self.network_stream = None
        self.stream_port = stream_port
        self.video_recorder = None

        # Start the video capture
        self.start_video_stream()
    
    def __del__(self):
        """Clean up resources when the Camera object is deleted."""
        self.stop_video_stream()
        logger.info("Camera object deleted.")
    
    def reinitialize(self):
        """Reinitialize the camera by stopping any existing streams and recorders, killing any lingering processes, and starting a new stream."""
        if self.video_recorder:
            self.stop_recording()
        if self.network_stream:
            self.stop_video_stream()
            self.kill_ustreamer()
            self.kill_ffmpeg()
            # Wait for a short time to ensure processes are killed
            self.start_video_stream()

        logger.info("Camera reinitialized.")
    
    def kill_ustreamer(self):
        """Kill all ustreamer processes."""
        try:
            subprocess.call(['pkill', '-f', 'ustreamer'])
            logger.debug("Killed all ustreamer processes.")
        except Exception as e:
            logger.error(f"Error killing ustreamer processes: {e}")
    
    def kill_ffmpeg(self):
        """Kill all ffmpeg processes."""
        try:
            subprocess.call(['pkill', '-f', 'ffmpeg'])
            logger.debug("Killed all ffmpeg processes.")
        except Exception as e:
            logger.error(f"Error killing ffmpeg processes: {e}")
    
    def start_video_stream(self):
        """Start the video stream using ustreamer."""
        if self._is_stream_reachable():
            logger.info(
                "Detected existing camera stream on port %s; reusing it.",
                self.stream_port,
            )
            self.network_stream = None
            return

        if shutil.which("ustreamer") is None:
            logger.error("ustreamer is not installed. Install it with: sudo apt install ustreamer")
            self.network_stream = None
            return

        cmd = [
            "ustreamer",
            f"--device={self.device}",
            "--host=0.0.0.0",
            f"--port={self.stream_port}",
            "--sink=demo::ustreamer::sink",
            "--sink-mode=660",
            "--sink-rm",
        ]
        logger.debug("Starting ustreamer with command: %s", " ".join(cmd))

        self.network_stream = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

        # Give ustreamer a moment to fail fast (e.g., missing device/permissions).
        time.sleep(0.4)
        if self.network_stream.poll() is not None:
            stderr = ""
            try:
                stderr = self.network_stream.stderr.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(
                "Failed to start ustreamer on %s:%s for device %s. Error: %s",
                "0.0.0.0",
                self.stream_port,
                self.device,
                stderr.strip()[:400],
            )
            self.network_stream = None
            return

        logger.info("Network stream started on 0.0.0.0:%s", self.stream_port)

    def _is_stream_reachable(self):
        """Return True when a stream endpoint is already serving on localhost."""
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.stream_port}/state", timeout=1.0) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
    
    def stop_video_stream(self):
        """Stop the video stream and kill the ustreamer process."""
        self.stop_recording()
        if self.network_stream:
            # self.network_stream.kill()
            os.killpg(os.getpgid(self.network_stream.pid), subprocess.signal.SIGTERM)
            self.network_stream = None
            logger.info("Network stream terminated.")
        else:
            logger.warning("No network stream to terminate.")
    
    def start_recording(self, output_file: str = "/mnt/shared/output.ts"):
        """Start recording the video stream."""
        if not self.video_recorder:
            cmd = f"ustreamer-dump --sink=demo::ustreamer::sink --output - | ffmpeg -use_wallclock_as_timestamps 1 -i pipe: -c:v libx264 {output_file}"
            logger.debug(f"Starting recording with command: {cmd}")
            # Start the video recorder
            self.video_recorder = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            logger.info(f"Recording started: {output_file}")
        else:
            logger.warning("Recording is already in progress.")
    
    def stop_recording(self):
        """Stop recording the video stream."""
        if self.video_recorder:
            # Stop the video recorder
            os.killpg(os.getpgid(self.video_recorder.pid), subprocess.signal.SIGTERM)
            self.video_recorder = None
            logger.info("Recording stopped.")
        else:
            logger.warning("No recording in progress.")

    def lock_focus(self):
        """Enable autofocus for a few seconds to focus, then disable it to lock focus."""
        def focus_routine():
            try:
                logger.info("Camera autofocus enabled. Waiting 3 seconds for it to focus...")
                subprocess.call(f"v4l2-ctl -d {self.device} --set-ctrl=focus_auto=1", shell=True)
                time.sleep(3)
                subprocess.call(f"v4l2-ctl -d {self.device} --set-ctrl=focus_auto=0", shell=True)
                logger.info("Camera autofocus disabled (focus locked).")
            except Exception as e:
                logger.error(f"Error locking focus: {e}")

        threading.Thread(target=focus_routine, daemon=True).start()

if __name__ == "__main__":
    camera = Camera()

    while True:
        pass
