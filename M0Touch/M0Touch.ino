#include <SD.h>
#include <SPI.h>
#include "DFRobot_GDL.h"
#include "DFRobot_Touch.h"
#include "drawBMP.h"

#define TFT_DC   7
#define TFT_CS   5
#define TFT_RST  6
#define TFT_BLK  9  


const int pin0 = 10;
const int pin1 = 11;
const int pin2 = 12;


int boardID = 0;

// showActive = true means the image is dispalyed and I'm waiting for only 1 touch
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

  Serial.print("M0 board #");
  Serial.print(boardID);
  Serial.println(" is ready.");
}


void loop() {
  processSerialCommand();
  scanTouch();
}


void setupPinsAndID() {
  pinMode(pin0, INPUT_PULLUP);
  pinMode(pin1, INPUT_PULLUP);
  pinMode(pin2, INPUT_PULLUP);

  if (digitalRead(pin0) == LOW) boardID |= (1 << 0);
  if (digitalRead(pin1) == LOW) boardID |= (1 << 1);
  if (digitalRead(pin2) == LOW) boardID |= (1 << 2);
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

}

void processSerialCommand() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;


  if (cmd.equalsIgnoreCase("WHOAREYOU?")) {
    Serial.print("ID:M0_");
    Serial.println(boardID);
    return;
  }

  // BLACK => screen black, backlight off, no touch
  if (cmd.equalsIgnoreCase("BLACK")) {
    setBlackScreen(false);
    showActive = false;   // ignore touches
    return;
  }

  // SHOW => backlight on, allow 1 touch
  if (cmd.equalsIgnoreCase("SHOW")) {
    showPreloadedImage();
    showActive = true;
    Serial.println("ACK:SHOW");
    return;
  }

  // 4) IMG:/// => preload BMP while backlight is off
  if (cmd.startsWith("IMG:")) {
    String imageID = cmd.substring(4);
    pickPicture(imageID.c_str());
    Serial.print("ACK:IMG ");
    Serial.println(imageID);
    return;
  }


}


void pickPicture(const char* imageID) {
  // Turn backlight off
  analogWrite(TFT_BLK, 0);

  char filePath[16];
  snprintf(filePath, sizeof(filePath), "/%s.BMP", imageID);
  if (SD.exists(filePath)) {
    drawBMP(&screen, filePath, 0, 0, 1);
    Serial.print("Preloaded image: ");
    Serial.println(filePath);
  } else {
    Serial.print("Failed to open: ");
    Serial.println(filePath);
  }
}


void showPreloadedImage() {
  analogWrite(TFT_BLK, 255);
  Serial.println("Backlight on; image visible now.");
}


void setBlackScreen(bool backlightOn) {
  analogWrite(TFT_BLK, 0);
}


void scanTouch() {
  // Read from GT911
  String scan_s = touch.scan();
  tp.id = numberTillComma(scan_s);
  tp.x  = numberTillComma(scan_s);
  tp.y  = numberTillComma(scan_s);
  tp.w  = numberTillComma(scan_s);

  // Check validity
  if (tp.id == 255 || tp.id == -1) {
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
