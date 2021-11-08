import socket
import threading
from random import randint

from RtpPacket import RtpPacket
from VideoStream import VideoStream


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    SPEEDUP = 'SPEEDUP'
    DESCRIBE = 'DESCRIBE'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}
    speed = 1

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)
            if data:
                self.processRtspRequest(data.decode("utf-8"))

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        request = data.splitlines()
        line1 = request[0].split(' ')
        requestType = line1[0]

        filename = line1[1]

        seq = request[1].strip()

        # Process SETUP request
        if requestType == self.SETUP:
            print("[INFO]", self.state)
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")
                # Generate a randomized RTSP session ID
                try:
                    if self.clientInfo['session']:
                        pass
                except:
                    self.clientInfo['session'] = randint(100000, 999999)
                # Get the RTP/UDP port from the last line
                try:
                    if self.clientInfo['rtpPort']:
                        pass
                except:
                    self.clientInfo['rtpPort'] = request[2].split(' ')[2]
            try:
                self.clientInfo['videoStream'] = VideoStream(filename)
                self.state = self.READY
                # Send RTSP reply
                self.replyRtsp(self.OK_200, seq)
            except IOError:
                self.replyRtsp(self.FILE_NOT_FOUND_404, seq)

        # Process PLAY request
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.replyRtsp(self.OK_200, seq)

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.replyRtsp(self.OK_200, seq)

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")
            try:
                self.clientInfo['event'].set()
            except:
                pass

            self.replyRtsp(self.OK_200, seq)

            # Close the RTP socket
            try:
                self.clientInfo['rtpSocket'].close()
            except:
                pass
        elif requestType == self.SPEEDUP:
            print("processing SPEEDUP\n")
            self.speed = int(request[1].split(' ')[0])
            self.clientInfo['videoStream'].setSpeed(self.speed)

        elif requestType == self.DESCRIBE:
            print("processing DESCRIBE\n")
            self.replyDescribe(self.OK_200, seq)

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber), (address, port))
                except:
                    print("Connection Error")
            # print('-'*60)
            # traceback.print_exc(file=sys.stdout)
            # print('-'*60)

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            # print("200 OK")
            reply = 'RTSP/1.0 200 OK' + '\n' \
                    + 'CSeq: ' + seq + '\n' + \
                    'Session: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            reply = 'RTSP/1.0 404 NOTFOUND' + '\n' \
                    + 'CSeq: ' + seq + '\n' + \
                    'Session: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")

    def describe(self):
        seq1 = "v=0\n" \
                + "m=video " + str(self.clientInfo['rtpPort']) + " RTP/AVP 26\n" \
                + "a=control:streamid=" \
                + str(self.clientInfo['session']) + "\n" \
                + "a=mimetype:string;\"video/Mjpeg\"\n"
        seq2 = "Content-Base: " + str(self.clientInfo['videoStream'].filename) + "\n" \
                + "Content-Length: " \
                + str(len(seq1)) + "\n"
        return seq2 + seq1

    def replyDescribe(self, code, seq):
        des = self.describe()
        if code == self.OK_200:
            reply = "RTSP/1.0 200 OK\n" \
                    + "CSeq: " + seq + "\n" \
                    + "Session: " + str(self.clientInfo['session']) + "\n" \
                    + des
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
