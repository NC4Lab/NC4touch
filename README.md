# MSRRA

# Setting Up Raspberry Pi OS with SSH and VS Code Remote Development

## 1. Install Raspberry Pi OS
1. Flash Raspberry Pi OS onto the SD card using the Raspberry Pi Imager.
2. During setup, set the following:
   - **Username**: `nc4`
   - **Password**: `1434`

## 2. Enable SSH on the Raspberry Pi
1. Boot the Raspberry Pi.
2. Open a terminal on the Pi and run:
   ```bash
   sudo raspi-config
   ```
3. Navigate to:
   - **Interface Options > SSH**
   - Select **Enable**.

## 3. Configure Your Windows PC for Ethernet Connection
1. Connect the Raspberry Pi to the PC via Ethernet.
2. Find the Raspberry Pi's IP address:
   - Open Command Prompt (`Win + R`, type `cmd`, press Enter).
   - Run:
     ```bash
     arp -a
     ```
   - Compare the output with the Raspberry Pi plugged in and unplugged.
   - Alternatively, run:
     ```bash
     ipconfig
     ```
   - Look for the associated `169.254.x.x` IP address.

## 4. Assign a Static IP to the Raspberry Pi
1. Power off the Raspberry Pi and pull out the SD card.
2. Insert the SD card into your computer and open the **boot** partition.
3. Open the `cmdline.txt` file with a text editor.
4. Add the following to the end of the single line:
   ```
   ip=169.254.55.240::169.254.55.239:255.255.0.0::eth0:off
   ```
   - Replace `169.254.55.240` with the desired static IP for the Pi.
   - Replace `169.254.55.239` with your PC's IP.

5. Save the file, eject the SD card, and reboot the Raspberry Pi.

## 5. Test the Connection
1. Open Command Prompt and ping the Raspberry Pi:
   ```bash
   ping 169.254.55.240
   ```
2. If the ping is successful, SSH into the Raspberry Pi:
   ```bash
   ssh nc4@169.254.55.240
   ```
3. When prompted:
   - Type `yes` to continue connecting.
   - Enter the password: `1434`.
4. Verify the connection works, then exit the SSH session:
   ```bash
   exit
   ```

## 6. Set Up Remote Development in VS Code
1. Open Visual Studio Code on your Windows PC.
2. Press `Ctrl + Shift + P` to open the Command Palette.
3. Search for and select:
   ```
   Remote-SSH: Add New SSH Host...
   ```
4. Enter the Raspberry Pi's SSH connection string:
   ```
   nc4@169.254.55.240
   ```
5. Save the configuration when prompted (e.g., `~/.ssh/config`).
6. Click **Connect**.

## 7. Complete the Remote-SSH Setup
1. A new VS Code window will open.
2. When prompted to select the platform, choose:
   ```
   Linux
   ```
3. Enter the password again: `1434`.
4. VS Code will automatically download and set up the remote server on the Raspberry Pi.

Your Raspberry Pi is now ready for remote development with VS Code!

# Working is SSH
1. Open Visual Studio Code on your Windows PC.
2. Press `Ctrl + Shift + P` to open the Command Palette.
3. Search for and select:
   ```
   Remote-SSH: Add New SSH Host...
   ```
4. Enter the Raspberry Pi's SSH connection string:
   ```
   nc4@169.254.55.240
   ```
5. Select your config when prompted (e.g., `~/.ssh/config`).
6. Click **Connect**.
7. Close the VS Code instance when you are done.  