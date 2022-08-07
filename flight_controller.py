# dummy functions
import random
def read_gpio(pin):
    return random.uniform(-1,1)

def actuate_servo(pin, value):
    return f'Actuating servo {pin} to {value}'

# libraries
import numpy as np

# classes
class FlightController:
    def __init__(self, ail_pin_in, ail_pin_out, elev_pin_in, elev_pin_out, fps):
        # GPIO pins
        self.ail_pin_in = ail_pin_in
        self.ail_pin_out = ail_pin_out
        self.elev_pin_in = elev_pin_in
        self.elev_pin_out = elev_pin_out
        self.fps = fps

        # set ManualFlight as default flight program
        self.select_program(0)

        # keep track of recent detection scores for n second(s)
        n = 1 # seconds
        self.horizon_detection_arr = [0 for n in range(n * fps)]

    def run(self, roll, pitch, is_good_horizon):
        """
        Run this for each iteration of main loop.
        Takes roll, pitch and is_good_horizon, and runs the FlightProgram
        accordingly.
        """

        self.is_good_horizon = is_good_horizon

        # update the array of horizon detection results
        self.horizon_detection_arr.append(is_good_horizon)
        del self.horizon_detection_arr[0]

        # read stick values
        self.ail_stick_value = read_gpio(self.ail_pin_in)
        self.elev_stick_value = read_gpio(self.elev_pin_in)

        # run the flight program
        stop = self.program.run()
        
        # actuate the servos
        actuate_servo(self.ail_pin_out, self.ail_val)
        actuate_servo(self.elev_pin_out, self.elev_val)

        return stop, self.ail_val, self.elev_val

    def select_program(self, program_id):
        self.program = FlightProgram.__subclasses__()[program_id](self)
        print('-----------------')
        print(f'Starting program: {self.program.__class__.__name__}')

class FlightProgram:
    def __init__(self, flt_ctrl):
        """
        Metaclass for flight programs, which are 
        responsible for actuating the servos.
        """
        self.flt_ctrl = flt_ctrl
        self.flt_ctrl.program = self
        self.stop = False

class ManualFlight(FlightProgram):
    def __init__(self, flt_ctrl):
        """
        User controls the aircraft.
        """
        super().__init__(flt_ctrl)
    
    def run(self):
        # aileron 
        self.flt_ctrl.ail_val = self.flt_ctrl.ail_stick_value

        # aileron 
        self.flt_ctrl.elev_val = self.flt_ctrl.elev_stick_value

        return False

class SurfaceCheck(FlightProgram):
    def __init__(self, flt_ctrl):
        """
        Automatic surface check for preflight check.
        """
        super().__init__(flt_ctrl)

        # initialize the control surfaces in netural positions
        self.flt_ctrl.ail_val = 0
        self.flt_ctrl.elev_val = 0
        self.ail_val_prev = 0
        self.elev_val_prev = 0

        # some values for moving the servos
        self.direction = 1
        self.increment = 1 / self.flt_ctrl.fps * 2
        self.ail_iterations = 0
        self.elev_iterations = 0
    
    def run(self):
        if self.ail_iterations < 3:
            self.flt_ctrl.elev_val = 0
            if abs(self.flt_ctrl.ail_val + self.increment * self.direction) > 1:
                self.direction *= -1
            self.flt_ctrl.ail_val += (self.increment * self.direction)
            if np.sign(self.flt_ctrl.ail_val) != np.sign(self.ail_val_prev):
                self.ail_iterations += 1
        elif self.elev_iterations < 3:
            self.flt_ctrl.ail_val = 0
            if abs(self.flt_ctrl.elev_val + self.increment * self.direction) > 1:
                self.direction *= -1
            self.flt_ctrl.elev_val += (self.increment * self.direction)
            if np.sign(self.flt_ctrl.elev_val) != np.sign(self.elev_val_prev):
                self.elev_iterations += 1 
        else:
            self.flt_ctrl.ail_val
            self.flt_ctrl.elev_val = 0
            self.stop = True

        # remember previous values for next iteration
        self.ail_val_prev = self.flt_ctrl.ail_val
        self.elev_val_prev = self.flt_ctrl.elev_val

        return self.stop

class LevelFlight(FlightProgram):
    def __init__(self, flt_ctrl):
        """
        Keeps the plane level.
        """
        super().__init__(flt_ctrl)
    
    def run(self):
        if self.flt_ctrl.is_good_horizon:
            # update some values
            self.flt_ctrl.ail_val = .1
            self.flt_ctrl.elev_val = .1
        elif not any(self.flt_ctrl.horizon_detection_arr):
            # return to neutral position after a period of time
            self.flt_ctrl.ail_val = 0 
            self.flt_ctrl.elev_val = 0

        return False

def main():
    import cv2
    from draw_display import draw_horizon, draw_surfaces

    FPS = 30
    WAIT_TIME = int(np.round(1 / FPS * 1000))
    FOV = 48.8

    flt_ctrl = FlightController(7, 11, 21, 13, fps=FPS)

    canvas = np.zeros((480, 640, 3), dtype = "uint8")

    ail_val = 0
    elev_val = 0
    roll = .0001
    pitch = 0

    is_good_horizon = True
    draw_ground_line = True

    n = 0
    while True:
        # copy the canvas to draw on it
        canvas_copy = canvas.copy()

        # get roll and pitch
        roll += ail_val/100
        roll = roll % 1
        pitch -= elev_val

        # get fake roll and pitch numbers, for displaying
        # when no horizon is detected
        if n % (FPS//4) == 0:
            fake_roll = random.uniform(0,1)
            fake_pitch= random.uniform(0,1)

        # # run flight controller
        # stop, ail_val, elev_val = flt_ctrl.run(roll, pitch, is_good_horizon)

        # draw
        if is_good_horizon:
            color = (255,0,0)
            draw_ground_line = True
            draw_horizon(canvas_copy, roll, pitch, FOV, color, draw_ground_line)
        else:
            color = (0,0,255)
            draw_ground_line = False
            draw_horizon(canvas_copy, fake_roll, fake_pitch, FOV, color, draw_ground_line)

        draw_surfaces(canvas_copy, .7, .95, .83, .9, ail_val, elev_val, (0,0,255))
        # center circle
        center = (canvas_copy.shape[1]//2, canvas_copy.shape[0]//2)
        radius = canvas_copy.shape[0]//100
        cv2.circle(canvas_copy, center, radius, (255,0,0), 2)

        # show some results
        # print(f'ail_val: {ail_val} | elev_val: {elev_val}')
        cv2.imshow("Flight Controller", canvas_copy)

        # # change program
        # if n == 300:
        #     # start surface check
        #     flt_ctrl.select_program(1)

        # # check if the program has ended
        # if stop:
        #     # resume manual flight
        #     flt_ctrl.select_program(0)

        # wait
        key = cv2.waitKey(WAIT_TIME)
        
        if key == ord('q'):
            break
        elif key == ord('a'):
            ail_val = -.5
        elif key == ord('d'):
            ail_val = .5
        elif key == ord('w'):
            elev_val = .5
        elif key == ord('s'):
            elev_val = -.5
        elif key == ord('r'):
            pitch = 0
        elif key == ord('h'):
            is_good_horizon = not is_good_horizon
            if not is_good_horizon:
                print('Horizon signal lost.')
            else:
                print('Horizon signal restored.')
        else:
            ail_val = 0
            elev_val = 0
        
        n += 1

    print('Finished')


if __name__ == "__main__":
    main()