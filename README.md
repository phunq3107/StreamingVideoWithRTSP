# Streaming Video with RTSP and RTP

## Introduction
ASSIGNMENT 1 

Course: Computer Network, Semester 1, 2021-2022

## Running the code
### Install list of all of a project’s dependencies
```shell
pip install -r requirements.txt
```

### Start the server with the command
```shell
python Server.py server_port 
# server_port: the standard RTSP port is 554,
# but you will need to choose a port number greater than 1024
```

### The client starts listening with the command
```shell
python ClientLauncher.py server_host server_port RTP_port video_file
# server_host: the name of the machine where the server is running
# server_port: is the port where the server is listening on
# RTP_port: is the port where the RTP packets are received
# video_file is the name of the video file you want to request
```

## Example
```shell
pip install -r requirements.txt
python .\Server.py 8081
python ClientLauncher.py 127.0.0.1 8081 5008 movie.Mjpeg
```




