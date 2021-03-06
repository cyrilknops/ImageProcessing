import numpy as np
import cv2
import logging
import math


def detect_edges(mask):
    edges = cv2.Canny(mask, 200, 400)

    return edges

def mask_frame(frame):
    # filter for blue lane lines
    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # lower mask (0-10)
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    mask0 = cv2.inRange(hsv, lower_red, upper_red)

    # upper mask (170-180)
    lower_red = np.array([170, 50, 50])
    upper_red = np.array([190, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red, upper_red)
    mask = mask0 + mask1
    # Bitwise-AND mask and original image
    res = cv2.bitwise_and(frame, frame, mask=mask)

    return mask, res

def region_of_interest(edges, frame):
    height, width = edges.shape
    mask = np.zeros_like(edges)

    # only focus top half of the screen
    polygon = np.array([[
        (width, height * 0.5),
        (0, height * 0.5),
        (0, 60),
        (width, 60),
    ]], np.int32)

    cv2.fillPoly(mask, polygon, 255)
    cropped_edges = cv2.bitwise_and(edges, mask)
    res = cv2.bitwise_and(frame, frame, mask=mask)
    return cropped_edges, res


def detect_line_segments(cropped_edges):
    # tuning min_threshold, minLineLength, maxLineGap is a trial and error process by hand
    rho = 1  # distance precision in pixel, i.e. 1 pixel
    angle = np.pi / 180  # angular precision in radian, i.e. 1 degree
    min_threshold = 10  # minimal of votes
    line_segments = cv2.HoughLinesP(cropped_edges, rho, angle, min_threshold,
                                    np.array([]), minLineLength=8, maxLineGap=4)

    return line_segments


def average_slope_intercept(frame, line_segments):
    """
    This function combines line segments into one or two lane lines
    If all line slopes are < 0: then we only have detected left lane
    If all line slopes are > 0: then we only have detected right lane
    """
    lane_lines = []
    if line_segments is None:
        logging.info('No line_segment segments detected')
        return lane_lines

    height, width, _ = frame.shape
    left_fit = []
    right_fit = []
    boundary = 1 / 2
    left_region_boundary = width * (1 - boundary)  # left lane line segment should be on left 2/3 of the screen
    right_region_boundary = width * boundary  # right lane line segment should be on left 2/3 of the screen

    for line_segment in line_segments:
        for x1, y1, x2, y2 in line_segment:
            if x1 == x2:
                logging.info('skipping vertical line segment (slope=inf): %s' % line_segment)
                continue
            fit = np.polyfit((x1, x2), (y1, y2), 1)
            slope = fit[0]
            intercept = fit[1]
            if slope < 0:
                if x1 < left_region_boundary and x2 < left_region_boundary:
                    left_fit.append((slope, intercept))

            else:
                if x1 > right_region_boundary and x2 > right_region_boundary:
                    right_fit.append((slope, intercept))
    left_fit_average = np.average(left_fit, axis=0)
    if len(left_fit) > 0:
        lane_lines.append(make_points(frame, left_fit_average))

    right_fit_average = np.average(right_fit, axis=0)
    if len(right_fit) > 0:
        lane_lines.append(make_points(frame, right_fit_average))


    logging.debug('lane lines: %s' % lane_lines)  # [[[316, 720, 484, 432]], [[1009, 720, 718, 432]]]
    # print(lane_lines)
    return lane_lines

def get_steering_angle(frame, lane_lines):
    height, width, _ = frame.shape

    if len(lane_lines) == 2:  # if two lane lines are detected
        _, _, left_x2, _ = lane_lines[0][0]  # extract left x2 from lane_lines array
        _, _, right_x2, _ = lane_lines[1][0]  # extract right x2 from lane_lines array
        mid = int(width / 2)
        x_offset = (left_x2 + right_x2) / 2 - mid
        y_offset = int(height / 2)

    elif len(lane_lines) == 1:  # if only one line is detected
        x1, _, x2, _ = lane_lines[0][0]
        x_offset = x2 - x1
        y_offset = int(height / 2)

    elif len(lane_lines) == 0:  # if no line is detected
        x_offset = 0
        y_offset = int(height / 2)

    angle_to_mid_radian = math.atan(x_offset / y_offset)
    angle_to_mid_deg = int(angle_to_mid_radian * 180.0 / math.pi)
    steering_angle = angle_to_mid_deg + 90

    return steering_angle


def display_heading_line(frame, steering_angle, line_color=(0, 0, 255), line_width=5):
    heading_image = np.zeros_like(frame)
    height, width, _ = frame.shape
    steering_angle = 180 - steering_angle
    steering_angle_radian = steering_angle / 180.0 * math.pi
    x1 = int(width / 2)
    y1 = height
    x2 = int(x1 - height / 2 / math.tan(steering_angle_radian))
    y2 = int(height / 2)

    cv2.line(heading_image, (x1, y1), (x2, y2), line_color, line_width)

    heading_image = cv2.addWeighted(frame, 0.8, heading_image, 1, 1)

    return heading_image

def round_int(x):
    if x == float("inf") or x == float("-inf"):
        return 0  # or x or return whatever makes sense
    return x

def make_points(frame, line):
    height, width, _ = frame.shape
    slope, intercept = line
    y2 = height  # bottom of the frame
    y1 = int(1 / 2)  # make points from middle of the frame down

    # bound the coordinates within the frame
    x1 = max(-width, min(2 * width, int((y1 - intercept) / slope)))
    x2 = max(-width, min(2 * width, int((y2 - intercept) / slope)))
    return [[x1, y1, x2, y2]]


def display_lines(frame, lines, line_color=(0, 255, 0), line_width=2):
    line_image = np.zeros_like(frame)
    if lines is not None:
        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(line_image, (x1, y1), (x2, y2), line_color, line_width)
    line_image = cv2.addWeighted(frame, 0.8, line_image, 1, 1)
    return line_image


def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
    for i in np.arange(0, 256)]).astype("uint8")
    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


cap = cv2.VideoCapture('videos/race.avi')
while (cap.isOpened()):

    # Take each frame
    _, frame = cap.read()

    #frame = adjust_gamma(frame, 2)  # adjust gamma
    mask, res = mask_frame(frame)  # add the HSV mask
    edges = detect_edges(mask)  # detect edges
    cropped_edges, frame_roi = region_of_interest(edges, frame)  # define region_of_interest
    line_seg = detect_line_segments(cropped_edges)  # detect line segments
    line_seg_avr = average_slope_intercept(frame, line_seg) # combine line segments into 1 line
    lines = display_lines(frame, line_seg)  # display the line segments
    masklines = display_lines(res, line_seg)  # display the line segments with the mask
    lines_avr = display_lines(frame, line_seg_avr)  # display the line avr line segments
    steering_angle = get_steering_angle(frame, line_seg_avr)  # calculate the steering angle
    heading_image = display_heading_line(lines_avr, steering_angle)  # display the steering angle with the line segments

    cv2.namedWindow('result', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('result', 1200, 1200)
    cv2.namedWindow('ROI', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('ROI', 1200, 1200)
    cv2.namedWindow('ROI_MASK', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('ROI_MASK', 1200, 1200)
    cv2.imshow('result', heading_image)
    cv2.imshow('ROI', frame_roi)
    cv2.imshow('ROI_MASK', lines)
    k = cv2.waitKey(25) & 0xFF
    if k == 27:
        break

cv2.destroyAllWindows()
