import serial
import time

test_port = '/dev/ttyUSB0' 
common_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600] 

print(f"Commencing Baud Rate Sweep on {test_port}...") 

sequence = 0

def build_packet(seq, throttle, steering, flags=0):
    """Constructs the 11-byte binary packet for the STM32."""
    packet = bytearray([
        0xAA,         # Byte 0: Header 1
        0x55,         # Byte 1: Header 2
        0x01,         # Byte 2: Message ID
        0x06,         # Byte 3: Payload length (6 bytes)
        seq & 0xFF,   # Byte 4: Sequence (0-255)
    ])
    
    # 16-bit values need to be split into Low and High bytes (Little Endian)
    packet.append(throttle & 0xFF)         # Byte 5: Throttle Low
    packet.append((throttle >> 8) & 0xFF)  # Byte 6: Throttle High
    
    packet.append(steering & 0xFF)         # Byte 7: Steering Low
    packet.append((steering >> 8) & 0xFF)  # Byte 8: Steering High
    
    packet.append(flags & 0xFF)            # Byte 9: Flags
    
    # Byte 10: Checksum (Standard 8-bit sum modulo 256 of Bytes 0-9)
    checksum = sum(packet) % 256
    packet.append(checksum)
    
    return packet

while True:
    for baud in common_bauds: 
        try: 
            print(f"\n--- Testing {baud} baud ---") 
            # Open port
            s = serial.Serial(test_port, baudrate=baud, timeout=1)
            
            # Dummy values for testing (e.g., 1500 is often neutral for PWM)
            test_throttle = 1500
            test_steering = 1500
            
            # Generate the 11-byte packet
            msg = build_packet(sequence, test_throttle, test_steering)
            
            # Fire it over UART
            s.write(msg) 
            
            # Print the raw hex output so you can see exactly what is leaving the Jetson
            print(f"Sent [Seq {sequence}]: {msg.hex(' ').upper()}")
            
            # Increment sequence and loop it back to 0 if it hits 256
            sequence = (sequence + 1) % 256
            
            time.sleep(0.1)
            
            # Important: Close the port before the next loop iteration to avoid locking it
            s.close()
            
        except serial.SerialException as e:
            print(f"ERROR: {e}")