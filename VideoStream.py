class VideoStream:
    speed = 1

    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except IOError as e:
            raise e
        self.frameNum = 0

    def nextFrame(self):
        """Get next frame."""
        data = self.file.read(5)  # Get the framelength from the first 5 bits
        if data:
            framelength = int(data)
            data = self.file.read(framelength)
            # Read the current frame
            for i in range(0, self.speed - 1):
                tempData = self.file.read(5)
                if tempData:
                    tempData = self.file.read(int(tempData))

            self.frameNum += 1
        return data

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum

    def setSpeed(self, newSpeed):
        self.speed = newSpeed
