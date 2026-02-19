#include <SD.h>
#include <SPI.h>
#include "DFRobot_GDL.h"
#include "DFRobot_Touch.h"
#include "drawBMP.h"


#define TFT_DC   7
#define TFT_CS   5
#define TFT_RST  6
#define TFT_BLK  9  

const char* VERSION = "0.2.0_20260219";


const int pin0 = 10;
const int pin1 = 11;
const int pin2 = 12;

int boardID = 0;

// showActive = true means the image is displayed and I'm waiting for only 1 touch
bool showActive = false;


DFRobot_ILI9488_320x480_HW_SPI screen(TFT_DC, TFT_CS, TFT_RST);
DFRobot_Touch_GT911 touch;

// TouchPoint struct
typedef struct {
  bool isValid;
  uint16_t id;
  uint16_t x;
  uint16_t y;
  uint16_t w;
} TouchPoint;

TouchPoint tp;
extern "C" char* sbrk(int incr);
int freeRam() {
  char stackTop;
  // Address of stack top minus where the heap currently ends:
  return &stackTop - sbrk(0);
}

// Function Declarations
void setupPinsAndID();
void setupDisplayAndSD();
void processSerialCommand();
void pickPicture(const char* imageID);
void showPreloadedImage();
void setBlackScreen(bool backlightOn = true);
void scanTouch();
uint16_t numberTillComma(String &s);


void setup() {
  Serial.begin(115200);
  while (!Serial) {
    // Wait for native USB on SAMD21
  }
  setupPinsAndID();

  setupDisplayAndSD();

  analogWrite(TFT_BLK, 0);
  screen.fillScreen(0x0000); 

  Serial.print("ID:M0_");
  Serial.print(boardID);
  Serial.println(" is ready.");
}


void loop() {
  processSerialCommand();
  scanTouch();
}


void setupPinsAndID() {
  pinMode(pin0, INPUT);
  pinMode(pin1, INPUT);
  pinMode(pin2, INPUT);

  // Address is Pin0*4 + Pin1*2 + Pin2*1
  // e.g. 0 0 0 => ID 0; 0 0 1 => ID 1; 0 1 0 => ID 2; ... 1 1 1 => ID 7
  if (digitalRead(pin0) == HIGH) boardID |= (1 << 2);
  if (digitalRead(pin1) == HIGH) boardID |= (1 << 1);
  if (digitalRead(pin2) == HIGH) boardID |= (1 << 0);
}

void printSDFileList(File dir) {
  while (true) {
    File entry = dir.openNextFile();
    if (!entry) {
      // no more files
      break;
    }
    Serial.print(entry.isDirectory() ? "DIR : " : "FILE: ");
    Serial.println(entry.name());

    entry.close();
  }
}

void setupDisplayAndSD() {
  // Init GT911
  touch.begin();

  // Init TFT
  screen.begin();
  screen.setColorMode(COLOR_MODE_RGB565);

  while (!SD.begin()) {
    Serial.println("SD init failed, retrying...");
    delay(1000);
  }
  Serial.println("SD init success!");

  // List SD contents for debugging
  Serial.println("SD contents:");
  File root = SD.open("/");
  printSDFileList(root);
  root.close();
}

void processSerialCommand() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;


  if (cmd.equalsIgnoreCase("WHOAREYOU?")) { // identify myself using the 3 pins
    Serial.print("ID:M0_");
    Serial.println(boardID);
    return;
  }
  else if (cmd.equalsIgnoreCase("VERSION?")) { // report version
    Serial.print("VERSION:");
    Serial.println(VERSION);
    return;
  }
  else if (cmd.equalsIgnoreCase("BLACK")) { // backlight off, show black screen, detect 1 touch
    setBlackScreen(false);
    showActive = true;   // detect 1 touch
    Serial.println("ACK:BLACK");
    return;
  } // SHOW => backlight on, allow 1 touch
  else if (cmd.equalsIgnoreCase("OFF")) { // backlight off, show black screen, ignore touches
    setBlackScreen(false);
    showActive = false;   // ignore touches
    Serial.println("ACK:OFF");
    return;
  }
  else if (cmd.equalsIgnoreCase("SHOW")) { // backlight on, detect 1 touch
    showPreloadedImage();
    showActive = true;  // detect 1 touch
    Serial.println("ACK:SHOW");
    return;
  }
  else if (cmd.startsWith("IMG:")) { // preload image with backlight off, wait for SHOW command to show it
    String imageID = cmd.substring(4);
    pickPicture(imageID.c_str());
    Serial.print("ACK:IMG ");
    Serial.println(imageID);
    return;
  }
  else {
    Serial.println("ERR:UNKNOWN_CMD");
    Serial.println(cmd);
    return;
  }
}


void pickPicture(const char* imageID) {
  // Turn backlight off
  analogWrite(TFT_BLK, 0);

  char fileName[32];
  snprintf(fileName, sizeof(fileName), "%s.BMP", imageID);
  if (SD.exists(fileName)) {
    drawBMP(&screen, fileName, 0, 0, 1);
    Serial.print("Preloaded image: ");
    Serial.println(fileName);
  } else {
    Serial.print("Failed to open: ");
    Serial.println(fileName);
  }
}


void showPreloadedImage() {
  analogWrite(TFT_BLK, 255);
  // Serial.println("Backlight on; image visible now.");
  // Serial.print("Free RAM (after showing image): ");
  // Serial.println(freeRam());
}


void setBlackScreen(bool backlightOn) {
  analogWrite(TFT_BLK, 0);
  // Serial.print("Free RAM (after backlight off): ");
  // Serial.println(freeRam());
}


void scanTouch() {
  // Read from GT911
  String scan_s = touch.scan();
  tp.id = numberTillComma(scan_s);
  tp.x  = numberTillComma(scan_s);
  tp.y  = numberTillComma(scan_s);
  tp.w  = numberTillComma(scan_s);

  // Check validity
  if (tp.id == 255 || tp.id == -1 || tp.x < 10 || tp.x > 310 || tp.y < 10 || tp.y > 470) {
    tp.isValid = false;
  } else {
    tp.isValid = true;
  }

  // If not valid or not in "showActive" mode, do nothing
  if (!tp.isValid || !showActive) return;

  // I have a valid touch and showActive = true
  Serial.print("TOUCH:X=");
  Serial.print(tp.x);
  Serial.print(",Y=");
  Serial.println(tp.y);

  // Now that I reported the touch, I do NOT want more
  showActive = false;

  // Immediately turn screens black
  analogWrite(TFT_BLK, 0);
}


uint16_t numberTillComma(String &s) {
  int commaIdx = s.indexOf(',');
  if (commaIdx == -1) {
    return (uint16_t)(-1);
  }
  int val = s.substring(0, commaIdx).toInt();
  s = s.substring(commaIdx + 1);
  return val;
}
