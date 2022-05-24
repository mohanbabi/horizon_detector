# from tensorflow.keras.models import load_model
print('----------STARTING HORIZON DETECTOR----------')
import cv2
import numpy as np
from queue import Queue
from threading import Thread
from argparse import ArgumentParser
from time import sleep
from timeit import default_timer as timer

# my libraries
import global_variables as gv
from crop_and_scale import get_cropping_and_scaling_parameters, crop_and_scale
from find_horizon import find_horizon
from draw_horizon import draw_horizon

def main():
    # parse arguments
    parser = ArgumentParser()
    help_text = 'The path to the video. For webcam, enter the index of the webcam you want to use, e.g. 0 '
    parser.add_argument('--source', help=help_text, default='0', type=str)     
    help_text = 'Default resolution used when streaming from camera. Not used when streaming from video file. '\
                   'Options include: 640x480, 1280x720 and 1920x1080.'
    parser.add_argument('--res', help=help_text, default='640x480', type=str)          
    args = parser.parse_args()

    # globals
    SOURCE = args.source
    RESOLUTION = (int(args.res.split('x')[0]), int(args.res.split('x')[1]))
    INFERENCE_RESOLUTION = (100, 100) # for image processing operations
    INFERENCE_FPS = 20

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
            t1 = timer()
            while self.run:
                ret, self.frame = self.cap.read()
                t2 = timer()
                fps = 1 / (t2 - t1)
                t1 = timer()
                self.fps_list.append(fps)
                if ret == False:
                    print('Cannot get frames. Ending program.')
                    self.run = False
                    self.release()

        def get_frames_from_video_file(self):
            while self.run:
                t1 = timer()
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
                t2 = timer()
                fps = 1 / (t2 - t1)
                self.fps_list.append(fps)


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
            print(f'CustomVideoStreamer average FPS: {average_fps}')
            self.run = False
            self.cap.release()
    
    # define VideoStreamer
    video_streamer = CustomVideoStreamer(RESOLUTION, source=SOURCE)

    # get some parameters for cropping and scaling
    crop_and_scale_parameters = get_cropping_and_scaling_parameters(video_streamer.resolution, INFERENCE_RESOLUTION)
    EXCLUSION_THRESH = video_streamer.resolution[1] * .075
    if crop_and_scale_parameters is None:
        print('Could not get cropping and scaling parameters.')
        return

    # keep track of the three most recent horizons
    # used to predict the approximate area of the current horizon
    recent_horizons = [None, None, None] 

    # start VideoStreamer
    video_streamer.start_stream()
    sleep(1)

    # initialize variables for main loop
    fps_list = []
    n=0
    t1 = timer()
    while video_streamer.run:
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
            # frame.shape 

        # find the horizon
        horizon = find_horizon(scaled_and_cropped_frame, predicted_m, predicted_b, EXCLUSION_THRESH, diagnostic_mode=False)
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
        
        # # draw horizon
        # if gv.render_image:
        #     frame_copy = frame.copy()
        #     frame_copy = draw_horizon(frame_copy, angle, offset, sky_is_up, good_horizon)
        #     cv2.imshow("frame", frame_copy)
        #     # cv2.imwrite(f'images/{n}.png', frame)

        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('d'):
            gv.render_image = False

        # dynamic wait
        # figure out how much longer we need to wait in order 
        # for the frame rate to be equal to INFERENCE_FPS
        t2 = timer()
        waited_so_far = t2 - t1
        addl_time_to_wait = 1/INFERENCE_FPS - waited_so_far
        if addl_time_to_wait > 0:
            sleep(addl_time_to_wait)

        # record the fps
        t_final = timer()
        fps = 1/(t_final - t1)
        t1 = timer()
        fps_list.append(fps)
        n+=1
    
    average_fps = np.mean(fps_list)
    print(f'main loop average fps: {average_fps}')
    video_streamer.release()
    cv2.destroyAllWindows()
    print('---------------------END---------------------')

if __name__ == '__main__':
    main()

