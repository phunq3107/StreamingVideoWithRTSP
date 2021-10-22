import sys
from tkinter import Tk
from Client import Client

if __name__ == "__main__":
    try:
        serverAddr = sys.argv[1]
        serverPort = sys.argv[2]
        rtpPort = sys.argv[3]
        fileName = sys.argv[4]

        root = Tk()

        # Create a new client
        app = Client(root, serverAddr, serverPort, rtpPort, fileName)
        app.master.title("Assignment 1: Video streaming with RTSP and RTP")
        root.mainloop()
    except Exception as e:
        print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")

    # root = Tk()
    #
    # # Create a new client
    # app = Client(root, serverAddr, serverPort, rtpPort, fileName)
    # app.master.title("RTPClient")
    # root.mainloop()
