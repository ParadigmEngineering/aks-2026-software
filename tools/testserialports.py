import serial
import time

ports_to_test = ['/dev/ttyTHS0','/dev/ttyTHS1', '/dev/ttyTHS2', '/dev/ttyTHS4', 
'/dev/ttyTCU0', '/dev/ttyAMA0', '/dev/ttyS0']

for port in ports_to_test:
    test_port = port

    try:
        print(f"Testing Port at {test_port}")
        s = serial.Serial(test_port, baudrate=115200, timeout=1, rtscts=False)

        s.write(b"Hello Self\n")
        time.sleep(0.1)

        response = s.read(200)
        print(f"Raw response: {response}")

        if b"Hello Self" in response:
            print("great success")
        elif b"login" in response.lower() or b"ubuntu" in response.lower():
            print("excuse me sir")
        else:
            print("o no")
    except serial.SerialException as e:
        print(f"ERROR: {e}")
        continue