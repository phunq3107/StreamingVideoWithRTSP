import os
import socket
import threading
import tkinter.messagebox as tkMessageBox
from tkinter import *

from PIL import Image, ImageTk

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    # GUI Component
    setupBtn: Button
    startBtn: Button
    pauseBtn: Button
    teardownBtn: Button

    label: Label
    message: Label

    inputName: Text

    playEvent: threading.Event

    # Socket
    rtspSocket: socket.socket

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.buildClientGUI()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0

        # custom
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def buildClientGUI(self):
        """Build GUI."""
        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=3, sticky=W + E + N + S, padx=5, pady=5)

        # Message:
        self.message = Label(self.master, text='Please choose file name before playing')
        self.message.grid(row=1, column=0, columnspan=3, sticky=W + E + N + S, padx=5, pady=5)

        # Input name
        self.inputName = Text(self.master, height=1, width=10)
        self.inputName.grid(row=2, column=0, columnspan=2, sticky=W + E + N + S, padx=5, pady=5)

        # Create Setup button
        self.setupBtn = Button(self.master, width=20, padx=3, pady=3)
        self.setupBtn["text"] = "Setup"
        self.setupBtn["command"] = self.setupMovie
        self.setupBtn.grid(row=2, column=2, padx=2, pady=2)

        # Create Play button
        self.startBtn = Button(self.master, width=20, padx=3, pady=3)
        self.startBtn["text"] = "Play"
        self.startBtn["command"] = self.playMovie
        self.startBtn.grid(row=3, column=0, padx=2, pady=2)

        # Create Pause button
        self.pauseBtn = Button(self.master, width=20, padx=3, pady=3)
        self.pauseBtn["text"] = "Pause"
        self.pauseBtn["command"] = self.pauseMovie
        self.pauseBtn.grid(row=3, column=1, padx=2, pady=2)

        # Create Teardown button
        self.teardownBtn = Button(self.master, width=20, padx=3, pady=3)
        self.teardownBtn["text"] = "Teardown"
        self.teardownBtn["command"] = self.exitClient
        self.teardownBtn.grid(row=3, column=2, padx=2, pady=2)

    def setupMovie(self):
        """Setup button handler."""
        filename = self.inputName.get(1.0, "end-1c")

        if filename != self.fileName:
            self.state = self.INIT
            self.fileName = filename
            self.sendRtspRequest(self.TEARDOWN)
            self.__init__(self.master, self.serverAddr, self.serverPort, self.rtpPort, self.fileName)

        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        print("[INFO]: Close app")

        cachename = CACHE_FILE_NAME

        for file in os.listdir():
            if file.startswith("cache-") & file.endswith(".jpg"):
                try:
                    os.remove(file)
                except:
                    print("[ERROR]: No such file or directory named " + file)
        self.master.destroy()

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.set():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    try:
                        self.rtpSocket.shutdown(socket.SHUT_RD)
                    except:
                        pass
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""

        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

        try:
            file = open(cachename, "wb")
            try:
                file.write(data)
            except:
                print("[ERROR]: Cannot write file")
            file.close()
        except:
            print("[ERROR]: Cannot open file")

        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile))
            self.label.configure(image=photo, height=288)
            self.label.image = photo
        except:
            print("[ERROR]: Cannot read photo")

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        print("[INFO]: Sending request:", requestCode)
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()

            self.rtspSeq = 1

            request = "SETUP " + str(self.fileName) + "\n" \
                      + str(self.rtspSeq) + "\n" \
                      + "RTSP/1.0 RTP/UDP " + str(self.rtpPort)

            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.SETUP

        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PLAY " + "\n" \
                      + str(self.rtspSeq)

            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.PLAY

            # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PAUSE " + "\n" \
                      + str(self.rtspSeq)
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.PAUSE

            # Resume request

            # Teardown request
        elif requestCode == self.TEARDOWN:
            self.rtspSeq = self.rtspSeq + 1
            request = "TEARDOWN " + "\n" \
                      + str(self.rtspSeq)
            self.rtspSocket.send(request.encode('utf-8'))
            self.requestSent = self.TEARDOWN
        else:
            return

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            try:
                reply = self.rtspSocket.recv(1024)
                if reply:
                    self.parseRtspReply(reply)

                if self.requestSent == self.TEARDOWN:
                    self.rtspSocket.shutdown(socket.SHUT_RDWR)
                    self.rtspSocket.close()
                    break
            except:
                pass

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        data = data.decode('utf-8')
        lines = str(data).split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            if self.sessionId == 0:
                self.sessionId = session

            if self.sessionId == session:

                if self.requestSent == self.SETUP:
                    if int(lines[0].split(' ')[1]) == 200:
                        self.state = self.READY
                        print("[INFO]: state -> READY")
                        self.openRtpPort()
                        self.message.configure(text="Ready to play")
                    elif int(lines[0].split(' ')[1]) == 404:
                        print("[ERROR]: File not exists")
                        self.message.configure(text="File not exists")
                elif self.requestSent == self.PLAY:
                    if int(lines[0].split(' ')[1]) == 200:
                        self.state = self.PLAYING
                        print("[INFO]: state -> PLAYING")
                elif self.requestSent == self.PAUSE:
                    if int(lines[0].split(' ')[1]) == 200:
                        self.state = self.READY
                        print("[INFO]: state -> READY")
                    self.playEvent.set()
                elif self.requestSent == self.TEARDOWN:
                    if int(lines[0].split(' ')[1]) == 200:
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        self.rtpSocket.settimeout(0.5)
        try:
            self.rtpSocket.bind((self.serverAddr, self.rtpPort))
            print("[INFO]: Bind RtpPort Success. Listening ...")

        except:
            tkMessageBox.showwarning('Connection Failed', 'Connection to rtpServer failed...')

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            print("[INFO]: Close app")
            threading.Thread(target=self.listenRtp).start()
            self.sendRtspRequest(self.PLAY)
