import socket
import sys

BUFF_SIZE = 16 * 4096
HOST, PORT = '127.0.0.1', 8888

def check_request(request):
    # Get method from request
    method = request.split()[0]

    # check method
    if method not in [b'GET', b'POST', b'HEAD']:
        return False
    return True

def get_host_name(request):
    return request.decode("utf8").split()[4]


def proxy_server():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((HOST, PORT))
    proxy_socket.listen(1)

    while True:
        print("Ready to serve...")
        while True:
            client_socket, client_addr = proxy_socket.accept()
            data = client_socket.recv(BUFF_SIZE)
            if not check_request(data):
                continue
            break
        print("Received a connection from:", client_addr)

        # Receive the request from the client
        print(data)
        request_data = data

        host_name = get_host_name(request_data)

        # Forward the client's request to the web server
        web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        web_socket.connect((host_name, 80))
        web_socket.sendall(request_data)

        # Receive the response from the web server
        response_data = web_socket.recv(BUFF_SIZE)

        print('\n', response_data)

        # Send the response back to the client
        client_socket.sendall(response_data)
  
        # Close the sockets
        web_socket.close()
        client_socket.close()    

if __name__ == "__main__":
    proxy_server()
