import cv2
import numpy as np

def convert_to_HSV(frame):
  hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
  cv2.imshow("HSV",hsv)
  return hsv

def detect_edges(frame):
    lower_blue = np.array([90, 120, 0], dtype = "uint8") # lower limit of blue color
    upper_blue = np.array([150, 255, 255], dtype="uint8") # upper limit of blue color
    mask = cv2.inRange(hsv,lower_blue,upper_blue) # this mask will filter out everything but blue

    # detect edges
    edges = cv2.Canny(mask, 50, 100)
    cv2.imshow("edges",edges)
    return edges
def region_of_interest(edges):
    height, width = edges.shape # extract the height and width of the edges frame
    mask = np.zeros_like(edges) # make an empty matrix with same dimensions of the edges frame

    # only focus lower half of the screen
    # specify the coordinates of 4 points (lower left, upper left, upper right, lower right)
    polygon = np.array([[
        (width, height * 1 / 2),
        (0, height * 1 / 2),
        (0, 0),
        (width, 0),
    ]], np.int32)

    cv2.fillPoly(mask, polygon, 255) # fill the polygon with blue color
    cropped_edges = cv2.bitwise_and(edges, mask)
    cv2.imshow("roi",cropped_edges)
    return cropped_edges

video = cv2.VideoCapture('videos/race.avi')
video.set(cv2.CAP_PROP_FRAME_WIDTH,320) # set the width to 320 p
video.set(cv2.CAP_PROP_FRAME_HEIGHT,240) # set the height to 240 p

# The loop
while True:
  ret,frame = video.read()
  cv2.namedWindow('original', cv2.WINDOW_NORMAL)
  cv2.resizeWindow('original', 1200, 1200)
  cv2.imshow("original",frame)

  key = cv2.waitKey(1)
  if key == 27:
    break

video.release()
cv2.destroyAllWindows()