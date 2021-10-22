import socket
import sys

from ServerWorker import ServerWorker


class Server:

    @staticmethod
    def main():
        try:
            SERVER_PORT = int(sys.argv[1])
            rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            rtspSocket.bind(('', SERVER_PORT))
            rtspSocket.listen(5)

            while True:
                clientInfo = {
                    'rtspSocket': rtspSocket.accept()
                }
                ServerWorker(clientInfo).run()
        except:
            print("[Usage: Server.py Server_port]\n")

        # # Receive client info (address,port) through RTSP/TCP session
        # while True:
        #     clientInfo = {
        #         'rtspSocket': rtspSocket.accept()
        #     }
        #     ServerWorker(clientInfo).run()


if __name__ == "__main__":
    (Server()).main()
