import serial
import time

test_port = '/dev/ttyUSB0' 

common_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600] 
print(f"Commencing Baud Rate Sweep on {test_port}...") 

while True:
    for baud in common_bauds: 
        try: 
            print(f"\n--- Testing {baud} baud ---") 
            s = serial.Serial(test_port, baudrate=baud, timeout=1)
            s.write(b"Hello STM\n") 
            time.sleep(0.1)
        except serial.SerialException as e:
            print(f"ERROR: {e}")