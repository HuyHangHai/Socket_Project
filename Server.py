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
white_list = []
num_white_list = -1
open_time = int(-1)
end_time = int(-1)
cache = {}
active_thread_count = 0


# read file 'config.txt'
def readFile(filename):
    global cache_timeout
    global white_list
    global num_white_list
    global open_time
    global end_time

    f = open(filename, "r")

    Cache_time = f.readline().strip()
    white_list = f.readline().strip()
    time = f.readline().strip()

    # Handle input
    cache_timeout = int(Cache_time.split()[2])

    white_list = white_list.split("=")[1].split(", ")

    time = time.split("=")[1]
    open_time = int(time.split("-")[0])
    end_time = int(time.split("-")[1])

    num_white_list = len(white_list)

    f.close()


# check valid request (GET, POST, HEAD)
def check_request(request):
    if request == b"":
        return 2
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


def check_valid_time(response):
    if not (current_time_hour >= open_time and current_time_hour <= end_time):
        response = configure_403(response)
    if current_time_hour == end_time:
        if current_time_minute > 0:
            response = configure_403(response)
    return response


def configure_403(response):
    response = b"HTTP/1.0 403 Forbidden\r\n"
    response += b"Content-Type: text/html\r\n"
    response += b"Content-Length: 130\r\n"  # Length of the HTML content
    response += (
        b"Connection: close\r\n"  # Close the connection after sending the response
    )
    response += b"\r\n"
    response += b"<html>"
    response += b"<head>"
    response += b"<title>403 Forbidden</title>"
    response += b"<style>"
    response += (
        b"h1 { color: black; }"  # Define the CSS style for the h1 element (red color)
    )
    response += b"</style>"
    response += b"</head>"
    response += b"<body>"
    response += b"<h1>403 Not this time, access forbidden</h1>"
    response += b"</body>"
    response += b"</html>"

    return response


def check_valid_web(request_path):
    for item in white_list:
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

    # check valid web for 403
    if not check_valid_web(request.decode().split()[1].split("/")[2]):
        response = configure_403(response)

    return response


def process_request(request):
    global cache

    url = request.decode("utf8").split("\n")[0].split()[1]

    if not check_valid_web(url):
        return configure_403(b"")

    if isImageURL(url):
        cache_response = Caching(url)
        if cache_response != "":
            return cache_response
        else:
            return forward2Server(request, url)
    else:
        return forward2Server(request, url)


def handle_client(client_socket):
    data = client_socket.recv(BUFF_SIZE)
    response = process_request(data)

    client_socket.sendall(response)
    client_socket.close()


def cut_byteSeq(byteSeq):
    for i in range(0, len(byteSeq)):
        if str(byteSeq[i : i + 4]) == "b'\\r\\n\\r\\n'":
            return i + 4


def proxy_server():
    global cache
    global active_thread_count

    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((HOST, PORT))
    proxy_socket.listen(1)

    thread_manager = threading.Thread(target=manage_threads)
    thread_manager.start()
    while True:
        print("Ready to serve...")
  
        while True:
            client_socket, client_addr = proxy_socket.accept()
            # Receive the request from the client
            request = client_socket.recv(BUFF_SIZE)
            if check_request(request[0 : cut_byteSeq(request)]) == 2:
                continue
            
            print("Received a connection from:", client_addr)
            
            request_cut = request[0 : cut_byteSeq(request)]
            response = b""

            print(request_cut.decode())

            # caching time
            request_str = request_cut.decode("utf8")
            url = request_str.split("\n")[0].split()[1]

            if isImageURL(url) == True:
                cache_response = Caching(url)

                if cache_response != "":
                    response += cache_response
                else:
                    response = forward2Server(request, url)

            else:
                response = forward2Server(request, url)

            end = cut_byteSeq(response)
            response_str = response[0:end].decode()
            print(response_str)

            # Send the response back to the client
            client_socket.sendall(response)

            if "Connection: close" in response_str:
                break

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