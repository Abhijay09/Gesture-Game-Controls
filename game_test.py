import socket

# Listen on the exact same port the controller is broadcasting to
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Game Console turned on. Waiting for hand signals...")

while True:
    data, addr = sock.recvfrom(1024) # Buffer size is 1024 bytes
    print(f"BUTTON PRESSED: {data.decode('utf-8')}")
