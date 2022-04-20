from socket import *
from urllib.parse import urlparse
import sys
from pathlib import Path

def proxy(portNum):

    #Creating a cache server socket that the client can contact through
    proxy_socket = socket(AF_INET, SOCK_STREAM)
    proxy_socket.bind(("", portNum))
    proxy_socket.listen(1)

    print("\n \n*********** We are now ready for a GET request... please provide one ***********")
    
    while True:
        #Getting an incoming request and creating a socket for the client
        client_socket, addr = proxy_socket.accept()
        print("Received a client connection from: ", addr, "\r\n")

        #Get the message sent by the client and split it into it's parts based on whitespace
        request = client_socket.recv(1024).decode()
        words = request.split()
        print("Client message is: " + request)

        #check if the client has sent a GET request to us in the right format or not
        #If not, code it a 500 and send it back to the client immediately
        if len(words) != 3 or words[0] != "GET" or (words[2] != "HTTP/1.0" and words[2] != "HTTP/1.0\r\n"):
            print("Received a non-GET request, status code is not 200 so no cache writing..." + 
            "\nNow responding to client...")
            response = "Cache-Hit: 0\r\nUnsupported Error\r\n"
            client_socket.send(response.encode()) 
        
        
        else:
            #Start checking if the cache directory exists based off of where this py file is located
            #If not, then create it using the folder name "proxyCache"
            cache = Path("./proxyCache")
            if not(cache.exists()):
                cache.mkdir()

            #getting the file path name for the client request file (example would be valid.html being requested)
            url = urlparse(words[1])
            cacheFilePath = "./proxyCache/" + url.hostname + "/" + url.path.replace("/", "-")
            cacheFile = Path(cacheFilePath)

            ##Checking if the file requested by the client is in cache, if so, encode and send it
            if cacheFile.is_file():
                with open(cacheFilePath, "r") as file:
                    data = file.read()
                    print("Huzzah! The file is in the cache and am sending it to the client now...")
                    client_socket.send("Cache-Hit: 1\r\n".encode())
                    client_socket.send(data.encode())

            #Since the file is not in cache, send a request to the actual server for the file the client wants and do things according to the response    
            else:
                print("Oopsie daisey! No cache hits this time! Getting the file from the server now...")
                client_socket.send("Cache-Hit: 0\r\n".encode())
                
                #Setting up the socket to connect to the external server
                external_socket = socket(AF_INET, SOCK_STREAM)
                ext_ip = gethostbyname(str(url.hostname))
                external_socket.connect((ext_ip, 80 if url.port == None else url.port))

                #Send request to server
                message = "GET " + url.path + " " + "HTTP/1.0\r\nhost: " + url.hostname + "\r\nConnection: close\r\n\r\n"
                print("Sending the following msg from proxy to server:\r\n" + message)
                external_socket.send(message.encode())

                #receive server response
                data = external_socket.recv(1024).decode()

                #getting rid of the non-status header data between it and the returned message response
                data = data.split("OK")[0] + "OK\r\n" + data.split("Connection: close\r\n\r\n")[1]+ "\r\n\r\n"

                #Check if the status contains 200, 404, or neither and then cache or send error accordingly
                if "200" in data:
                    #Yay it's a good hit! cache this sucker then send it to the client
                    print("Response received from the server, and the code was 200! Writing this sucker to cache to save some precious ms in response time")
                    
                    newCachePath = Path("./proxyCache/" + url.hostname + "/")
                    if not newCachePath.is_dir():
                        newCachePath.mkdir(parents=True)
                    newCachePath = newCachePath / url.path.replace("/", "-")
                    newCachePath.write_text(data)

                    print("File cached! Now responding to cleint with requested file...")

                #Error status code path, just say which error code it falls under then send it!
                else:
                    print("Response received from server, non-200 status code! No cache writing this time!\r\nNow responding to client...")
                    if "404" in data:
                        data = "HTTP/1.1 400 OK\r\n404 NOT FOUND\r\n\r\n"
                    else:
                        data = "HTTP/1.1 500 OK\r\nUnsupported Error\r\n\r\n"

                client_socket.send(data.encode())

        print("All done! Closing this socket...\r\n\r\n\r\n")
        client_socket.close()

#Creates a command line argument for the port number and 
#then feeds this into the proxy method
if __name__ == "__main__":
    port = int(sys.argv[1])
    proxy(port)
