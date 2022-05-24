# from tensorflow.keras.models import load_model
import cv2
import numpy as np
import platform
from queue import Queue
from threading import Thread
from argparse import ArgumentParser
from time import sleep
from timeit import default_timer as timer

import global_variables as gv

# for later
from crop_and_scale import get_cropping_and_scaling_parameters, crop_and_scale
from find_horizon import find_horizon
from draw_horizon import draw_horizon

class CustomVideoStreamer:
    def __init__(self, resolution=None, source=SOURCE):
        self.run = False
        self.source = source
        self.fps_list = []

        # determine if we are streaming from a webcam or a video file
        if source.isnumeric():
            self.source = int(source)
            self.using_camera = True
        else:
            self.using_camera = False
            self.queue = Queue(maxsize=1000)

        # define the VideoCapture object
        if gv.os == "Linux" or self.using_camera == False:
            self.cap = cv2.VideoCapture(self.source)
        elif self.using_camera == True:
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            
        # define the resolution
        if self.using_camera:
            self.resolution = resolution
        else:
            ret, self.frame = self.cap.read() # read the first frame to get the resolution
            self.resolution = self.frame.shape[:2][::-1]
            # redefine the VideoCapture object so that we start over at frame 0
            self.cap = cv2.VideoCapture(self.source) 
            self.cap.set(3,self.resolution[0])
            self.cap.set(4,self.resolution[1])

        print(f'resolution: {self.resolution}')

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    def get_frames_from_webcam(self):
        while self.run:
            t1 = timer()
            ret, self.frame = self.cap.read()
            t2 = timer()
            fps = 1 / (t2 - t1)
            self.fps_list.append(fps)
            if ret == False:
                print('Cannot get frames. Ending program.')
                self.run = False
                self.release()

    def get_frames_from_video_file(self):
        while self.run:
            if self.queue.full():
                sleep(1) # wait a bit for the main loop to catch up
                continue # terminate the current iteration of the loop early
                
            else:
                ret, frame = self.cap.read()
            
            if ret == False:
                print('Cannot get frames. Ending program.')
                self.release()
                break
            else:
                self.queue.put(frame)

    def read_frame(self):
        # if using webcam
        if self.using_camera:
            return self.frame

        # if streaming from a video file
        if self.queue.empty():
            self.run = False
            print('No more frames left in the queue.')
            self.release()
        else:
            frame = self.queue.get()
            return frame         

    def start_stream(self):
        self.run = True
        print(f'using_camera: {self.using_camera}')
        if self.using_camera:
            Thread(target=self.get_frames_from_webcam).start()
        else:
            Thread(target=self.get_frames_from_video_file).start()
            
    def set_resolution(self, resolution):
        self.cap.set(3, resolution[0])
        self.cap.set(4, resolution[1])

    def release(self):
        average_fps = np.average(self.fps_list)
        print(f'average_fps from CustomVideoStreamer class: {average_fps}')
        self.run = False
        self.cap.release()

def main():
    # parse arguments
    parser = ArgumentParser()
    help_text = 'The path to the video. For webcam, enter the index of the webcam you want to use, e.g. 0 '
    parser.add_argument('--source', help=help_text, default='0', type=str)     
    help_text = 'Default resolution used when streaming from camera. Not used when streaming from video file. '#\
                   # 'Example format: 640x480. Other options include 1280x720 and 1920x1080.'
    parser.add_argument('--res', help=help_text, default='640x480', type=str)          
    args = parser.parse_args()

    # globals
    SOURCE = args.source
    RESOLUTION = (args.res.split('x')[0], args.res.split('x')[1])
    INFERENCE_RESOLUTION = (100, 100) # for image processing operations
    
    # define VideoStreamer
    video_streamer = CustomVideoStreamer(RESOLUTION, source=SOURCE)

    # get some parameters for cropping and scaling
    crop_and_scale_parameters = get_cropping_and_scaling_parameters(video_streamer.resolution, INFERENCE_RESOLUTION)
    scaled_and_cropped_frame = crop_and_scale(video_streamer.frame, **crop_and_scale_parameters)
    EXCLUSION_THRESH = video_streamer.resolution * .075
    if crop_and_scale_parameters is None:
        print('Could not get cropping and scaling parameters.')
        return

    # keep track of the three most recent horizons
    # used to predict the approximate area of the current horizon
    recent_horizons = [None, None, None] 

    # start VideoStreamer
    video_streamer.start_stream()
    sleep(1)
    fps_list = []
    n=0
    while video_streamer.run:
        t1 = timer()
        # get a frame
        frame = video_streamer.read_frame()

        # crop and scale the image
        scaled_and_cropped_frame = crop_and_scale(frame, **crop_and_scale_parameters)

        # predict the next horizon
        if None in recent_horizons:
            predicted_m = None
            predicted_b = None
        else: 
            angle_velocity = 0
            offset_velocity = 0
            
            new_angle = recent_horizons[-1]['angle'] + angle_velocity
            new_offset = recent_horizons[-1]['offset'] + offset_velocity

            # convert from radians and offset to m and b
            frame.shape 

        # find the horizon
        horizon = find_horizon(scaled_and_cropped_frame, predicted_m, predicted_b, EXCLUSION_THRESH, diagnostic_mode=True)
        if horizon is not None:
            angle = horizon['angle'] 
            offset = horizon['offset'] 
            sky_is_up = horizon['sky_is_up'] 
            variance = horizon['variance'] 
        else:
            angle = None
            offset = None
            sky_is_up = None 
            variance = None

        # check the variance to determine if this is a good horizon
        good_horizon = True
        
        # draw horizon
        if gv.render_image:
            frame = draw_horizon(frame, angle, offset, sky_is_up, good_horizon)
            cv2.imshow("frame", frame)
            # cv2.imwrite(f'images/{n}.png', frame)

        key = cv2.waitKey(60)
        if key == ord('q'):
            break
        elif key == ord('d'):
            gv.render_image = False

        t2 = timer()
        fps_list.append(1/(t2 - t1))
        n+=1
    
    average_fps = np.mean(fps_list)
    print(f'main loop average fps: {average_fps}')
    video_streamer.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()

