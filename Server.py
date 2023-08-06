import socket
import sys
from datetime import datetime, time

BUFF_SIZE =  4096
HOST, PORT = '127.0.0.1', 8888
current_time = datetime.now().hour
cache_time = int(0)
while_list = ""
num_while_list = -1
open_time = int(-1)
end_time = int(-1)

# check valid request (GET, POST, HEAD)
def check_request(request):
    # Get method from request
    method = request.split()[0]

    # check method
    if method not in [b'GET', b'POST', b'HEAD']:
        return False
    return True

# get web server's name
def get_host_name(request):
    return request.decode("utf8").split()[4]

def read_config():
    global cache_time
    global while_list
    global num_while_list
    global open_time
    global end_time

    f = open("config.txt", 'r')
    
    cache_time = f.readline()
    while_list = f.readline()
    time = f.readline()

    # Handle input
    cache_time = cache_time.split()[2]

    while_list = while_list.split("=")[1].split(",")

    time = time.split('=')[1]
    open_time = int(time.split('-')[0])
    end_time = int(time.split('-')[1])

    num_while_list = len(while_list)

    f.close()

def configure_403(response_data):
    response_data = b"HTTP/1.0 403 Forbidden\r\n"
    response_data += b"Content-Type: text/html\r\n"
    response_data += b"Content-Length: 130\r\n"  # Length of the HTML content
    response_data += b"Connection: close\r\n"  # Close the connection after sending the response
    response_data += b"\r\n"
    response_data += b"<html>"
    response_data += b"<head>"
    response_data += b"<title>403 Forbidden</title>"
    response_data += b"<style>"
    response_data += b"h1 { color: blue; }"  # Define the CSS style for the h1 element (red color)
    response_data += b"</style>"
    response_data += b"</head>"
    response_data += b"<body>"
    response_data += b"<h1>403 Not this time, access forbidden</h1>"
    response_data += b"</body>"
    response_data += b"</html>"

    return response_data

def check_valid_web(web):
    i = 0  
    print(num_while_list)
    while i < num_while_list:
        if web.find(while_list[i]) != -1 :
            return False
        i += 1
    return True

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
        print(data.decode())
        request_data = data

        host_name = get_host_name(request_data)

        # Forward the client's request to the web server
        web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        web_socket.connect((host_name, 80))
        web_socket.sendall(request_data)

        # Receive the response from the web server
        response_data = web_socket.recv(BUFF_SIZE)     

        # check all 403 situations
        if current_time < open_time and current_time > end_time:
            response_data = configure_403(response_data)

        if not check_valid_web(host_name):
            response_data = configure_403(response_data)

        print(response_data, '\n')

        # Send the response back to the client
        client_socket.sendall(response_data)
  
        # Close the sockets
        web_socket.close()
        client_socket.close()    

if __name__ == "__main__":
    read_config()
    proxy_server()
