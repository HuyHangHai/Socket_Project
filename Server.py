import socket
import sys
import threading
from datetime import datetime, time
import time
from turtle import forward

BUFF_SIZE = 4096
HOST, PORT = "127.0.0.1", 8888
current_time_hour = datetime.now().hour
current_time_minute = datetime.now().minute
cache_timeout = int(0)
while_list = ""
num_while_list = -1
open_time = int(-1)
end_time = int(-1)
cache = {}


# read file 'config.txt'
def readFile(filename):
    global cache_timeout
    global while_list
    global num_while_list
    global open_time
    global end_time

    f = open(filename, "r")

    Cache_time = f.readline().strip()
    while_list = f.readline().strip()
    time = f.readline().strip()

    # Handle input
    cache_timeout = int(Cache_time.split()[2])

    while_list = while_list.split("=")[1].split(", ")

    time = time.split("=")[1]
    open_time = int(time.split("-")[0])
    end_time = int(time.split("-")[1])

    num_while_list = len(while_list)

    f.close()


# check valid request (GET, POST, HEAD)
def check_request(request):
    # Get method from request
    method = request.split()[0]

    # check method
    if method in [b"GET", b"POST", b"HEAD"]:
        return 1
    elif method in [b"CONNECT"]:
        return 2
    else:
        return 3

    return 0


# get web server's name
def get_host_name(request):
    return request.decode("utf8").split()[4]

def check_valid_time(response_data):
    if not (current_time_hour >= open_time and current_time_hour <= end_time):
        response_data = configure_403(response_data)
    if current_time_hour == end_time:
        if current_time_minute > 0:
            response_data = configure_403(response_data)
    return response_data

def configure_403(response_data):
    response_data = b"HTTP/1.0 403 Forbidden\r\n"
    response_data += b"Content-Type: text/html\r\n"
    response_data += b"Content-Length: 130\r\n"  # Length of the HTML content
    response_data += (
        b"Connection: close\r\n"  # Close the connection after sending the response
    )
    response_data += b"\r\n"
    response_data += b"<html>"
    response_data += b"<head>"
    response_data += b"<title>403 Forbidden</title>"
    response_data += b"<style>"
    response_data += (
        b"h1 { color: black; }"  # Define the CSS style for the h1 element (red color)
    )
    response_data += b"</style>"
    response_data += b"</head>"
    response_data += b"<body>"
    response_data += b"<h1>403 Not this time, access forbidden</h1>"
    response_data += b"</body>"
    response_data += b"</html>"

    return response_data

def check_valid_web(request_path):
    for item in while_list:
        index = request_path.find(item)
        if index != -1:
            return True
    return False

# it's cache time!
def isImageURL(url):
    image = url.split("/")[3]
    if image != "":
        extension = image.split(".")[1]
        if extension in ["png", "jpg", "jpeg", "gif"]:
            return True

        return False

    return False

def Caching(url):
    global cache

    now = time.time()
    if url in cache and now - cache[url]["timestamp"] <= cache_timeout:
        print("Image from cache: ")
        return cache[url]["image"]
    
    return ""

# Forward the client's request to the web server
def forward2Server(request, url):
    global cache

    host_name = get_host_name(request)

    web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_socket.connect((host_name, 80))
    web_socket.sendall(request)

    # Receive the response from the web server
    response = web_socket.recv(BUFF_SIZE)
    web_socket.close()

    # check all 403 situations
    response = check_valid_time(response)
    if check_request(request) == 3:
        response = configure_403(response)

    elif isImageURL(url) == True:
        cache[url] = {"image": response, "timestamp": time.time()}

    return response

def process_request(request_data):
    global cache

    url = request_data.decode("utf8").split("\n")[0].split()[1]

    if not check_valid_web(url):
        return configure_403(b"")

    if isImageURL(url):
        cache_response = Caching(url)
        if cache_response != "":
            return cache_response
        else:
            return forward2Server(request_data, url)
    else:
        return forward2Server(request_data, url)

def handle_client(client_socket):
    data = client_socket.recv(BUFF_SIZE)
    response_data = process_request(data)

    client_socket.sendall(response_data)
    client_socket.close()


def proxy_server():
    global cache

    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((HOST, PORT))
    proxy_socket.listen(1)

    
    thread_manager = threading.Thread(target=manage_threads)
    thread_manager.start()
    while True:
        print("Ready to serve...")
        while True:
            client_socket, client_addr = proxy_socket.accept()
            data = client_socket.recv(BUFF_SIZE)
            if check_request(data) == 2:
                continue
            break
        print("Received a connection from:", client_addr)

        # Receive the request from the client
        print(data.decode())
        request_data = data
        response_data = b""

        # check valid web for 403
        if not check_valid_web(request_data.decode().split()[1]):
            response_data = configure_403(response_data)

        else:
            # caching time
            request_str = data.decode("utf8")
            url = request_str.split("\n")[0].split()[1]

            if isImageURL(url) == True:

                cache_response = Caching(url)

                if cache_response != "":
                    response_data += cache_response
                else:
                    response_data = forward2Server(request_data, url)

            else:
                response_data = forward2Server(request_data, url)

            # print(response_data, "\n")

            # Send the response back to the client
        client_socket.sendall(response_data)

        # Close the sockets
        client_socket.close()

              # Tăng số luồng đang hoạt động
        active_thread_count += 1

def manage_threads():
    global active_thread_count
    active_thread_count = 0  # Số luồng đang hoạt động
    MAX_CONCURRENT_THREADS = 10  # Số lượng luồng đồng thời tối đa
    while True:
        if active_thread_count >= MAX_CONCURRENT_THREADS:
            time.sleep(1)
        else:
            active_thread_count -= 1




        


if __name__ == "__main__":
    filename = "config.txt"
    readFile(filename)
    proxy_server()

