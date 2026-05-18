import serial 
import time 
test_port = '/dev/ttyUSB0' 

# The most common baud rates in embedded systems 
common_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600] 
print(f"Commencing Baud Rate Sweep on {test_port}...") 

for baud in common_bauds: 
    try: 
        print(f"\n--- Testing {baud} baud ---") 
        s = serial.Serial(test_port, baudrate=baud, timeout=1) 
        
        # We send a few common "wake up" or "invalid" commands 
        # to try and force the STM32 to complain and send an error string back 
        s.write(b"\r\n") 
        time.sleep(0.1) 
        s.write(b"?\r\n") 
        time.sleep(0.1) 
        
        # Read a chunk of data 
        response = s.read(100) 
        
        if response != b'': 
            print(f"Received response: {response}") 
        else: 
            print("No response from STM.")
            s.close() 
    except serial.SerialException as e:
        print(f"ERROR: {e}")