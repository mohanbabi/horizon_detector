CENTER = 0
MAX_DEFLECTION = 1

def get_aileron_value(angle: float) -> float:
    # determine direction and current error
    if angle < .5:
        direction = 1
        current_error = angle
    else:
        direction = -1
        current_error = 1 - angle
    
    # determine duty difference
    if current_error > .1:
        duty_diff = MAX_DEFLECTION * direction
    else:
        duty_diff = current_error ** 2 / .1 ** 2 * MAX_DEFLECTION * direction

    # determine duty
    aileron_value = CENTER + duty_diff

    return aileron_value

if __name__ == "__main__":
    angle = .2
    aileron_value = get_aileron_value(angle)
    print(aileron_value)