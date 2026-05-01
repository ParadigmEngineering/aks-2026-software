import serial
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

sequence = 0

FLAG_AUTONOMOUS_ENABLE = 1 << 0  # 0x01
FLAG_ESTOP_REQUEST     = 1 << 1  # 0x02
FLAG_VALID_PATH        = 1 << 2  # 0x04

def checksum_xor(data):
    chk = 0
    for b in data:
        chk ^= b
    return chk

def build_packet(seq, throttle, steering, flags):
    packet = bytearray([
        0xAA,
        0x55,
        0x01,
        0x06,
        seq & 0xFF,
    ])

    packet.append(throttle & 0xFF)
    packet.append((throttle >> 8) & 0xFF)

    packet.append(steering & 0xFF)
    packet.append((steering >> 8) & 0xFF)

    packet.append(flags & 0xFF)

    packet.append(checksum_xor(packet))

    return packet

with serial.Serial(PORT, baudrate=BAUD, timeout=1) as s:
    print(f"Sending Jetson packets on {PORT} at {BAUD} baud")

    while True:
        test_throttle = 1600
        test_steering = 1600

        flags = FLAG_AUTONOMOUS_ENABLE | FLAG_VALID_PATH  # 0x05

        msg = build_packet(sequence, test_throttle, test_steering, flags)

        s.write(msg)

        print(f"Sent [Seq {sequence}]: {msg.hex(' ').upper()}")

        sequence = (sequence + 1) & 0xFF

        time.sleep(0.02)  # 50 Hz
