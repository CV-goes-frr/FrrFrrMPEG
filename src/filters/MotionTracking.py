import cv2
import numpy as np
from typing import List
from multiprocessing import Pool

from .Filter import Filter


class MotionTracking(Filter):
    def __init__(self):
        super().__init__()  # Call the constructor of the parent class (Filter)

    def apply(self, first_frame : np.ndarray, second_frame : np.ndarray,
              processes_limit: int, pool: Pool) -> List[np.ndarray]:
        """
        Simple motion tracking with absolute difference
        :param first_frame: np.ndarray of pixels - Input frame as a NumPy array
        :param second_frame: np.ndarray of pixels - Next frame as a NumPy array
        :param processes_limit: we'll try to parallel it later
        :param pool: processes pool
        :return:List containing the edited frame as a NumPy array
        """

        # compute the absolute difference between the current frame and
        diff = cv2.absdiff(first_frame, second_frame)

        # Apply GaussianBlur to reduce noise
        blur = cv2.GaussianBlur(diff, (5, 5), 0)

        # Convert images to grayscale
        gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh.copy(), None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        # loop over the contours
        for contour in contours:
            # if the contour is too small, ignore it
            if cv2.contourArea(contour) < 8000:
                continue

            # compute the bounding box for the contour
            (x, y, w, h) = cv2.boundingRect(contour)
            bboxes.append((x, y, w, h))

        # Merge the bounding boxes that overlap
        suppress = set()
        for i in range(len(bboxes)):
            x1, y1, w1, h1 = bboxes[i]
            for j in range(i + 1, len(bboxes)):
                x2, y2, w2, h2 = bboxes[j]
                # Calculate the area of the first bounding box
                area1 = w1 * h1

                # Calculate the area of the second bounding box
                area2 = w2 * h2

                # Define the points of the intersection rectangle
                x_min = max(x1, x2)
                y_min = max(y1, y2)
                x_max = min(x1 + w1, x2 + w2)
                y_max = min(y1 + h1, y2 + h2)

                # Calculate the area of the intersection rectangle
                width = max(0, x_max - x_min)
                height = max(0, y_max - y_min)
                area = min(area1, area2)
                intersection_area = width * height

                # Calculate the IoU
                iou = intersection_area / area

                if iou > 0.1:
                    if area1 > area2:
                        suppress.add(j)
                    else:
                        suppress.add(i)

        # Draw the bounding boxes on the frame
        for i in sorted(set(range(len(bboxes))) - suppress):
            x, y, w, h = bboxes[i]
            cv2.rectangle(first_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return [first_frame]