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
        self._autofocus_control_name = None

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
            self.disable_autofocus()
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
        self.disable_autofocus()

    def _set_focus_auto(self, enabled: bool):
        """Set camera autofocus state using v4l2-ctl."""
        if shutil.which("v4l2-ctl") is None:
            logger.warning("v4l2-ctl is not installed; cannot change camera focus_auto control.")
            return False

        control_name = self._get_autofocus_control_name()
        if control_name is None:
            logger.warning(
                "No supported autofocus control found for %s (expected focus_auto or focus_automatic_continuous).",
                self.device,
            )
            return False

        value = "1" if enabled else "0"
        try:
            result = subprocess.run(
                ["v4l2-ctl", "-d", self.device, f"--set-ctrl={control_name}={value}"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            logger.error(f"Error setting focus_auto={value}: {e}")
            return False

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.warning(
                "Unable to set %s=%s on %s. %s",
                control_name,
                value,
                self.device,
                stderr,
            )
            return False

        return True

    def _get_autofocus_control_name(self):
        """Detect autofocus control name exposed by the camera."""
        if self._autofocus_control_name is not None:
            return self._autofocus_control_name

        try:
            result = subprocess.run(
                ["v4l2-ctl", "-d", self.device, "--list-ctrls"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            logger.warning(f"Unable to inspect camera controls on {self.device}: {e}")
            return None

        controls_text = result.stdout or ""
        if "focus_automatic_continuous" in controls_text:
            self._autofocus_control_name = "focus_automatic_continuous"
        elif "focus_auto" in controls_text:
            self._autofocus_control_name = "focus_auto"
        else:
            self._autofocus_control_name = None

        if self._autofocus_control_name:
            logger.debug(
                "Using autofocus control '%s' for device %s",
                self._autofocus_control_name,
                self.device,
            )

        return self._autofocus_control_name

    def disable_autofocus(self):
        """Keep autofocus disabled so focus remains fixed during a session."""
        if self._set_focus_auto(False):
            logger.info("Camera autofocus disabled.")

    def autofocus_once_and_lock(self, focus_seconds: float = 3.0):
        """Briefly autofocus, then disable autofocus to lock focus for the session."""
        def focus_routine():
            if not self._set_focus_auto(True):
                return
            logger.info("Camera autofocus enabled for %.1f seconds...", focus_seconds)
            time.sleep(max(0.0, float(focus_seconds)))
            self.disable_autofocus()
            logger.info("Camera focus locked for the remainder of the session.")

        threading.Thread(target=focus_routine, daemon=True).start()

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
        """Backward-compatible alias for one-shot autofocus then lock."""
        self.autofocus_once_and_lock()

if __name__ == "__main__":
    camera = Camera()

    while True:
        pass
