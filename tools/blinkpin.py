import Jetson.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)

target_pin = 8

print('commencing sequence')

try:
    GPIO.setup(target_pin, GPIO.OUT)

    while True:
        GPIO.output(target_pin, GPIO.HIGH)
        print('high')
        time.sleep(2)
        GPIO.output(target_pin, GPIO.LOW)
        time.sleep(2)
        print('low')
except Exception as e:
    print(f"ERROR: {e}")
finally:
    GPIO.cleanup()