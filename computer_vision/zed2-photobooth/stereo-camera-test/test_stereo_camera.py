import cv2
from stereo_camera import capture_stereo

# Capture one stereo pair at 720p.
left, right = capture_stereo("vga",camera_index=1)

# Print the dimensions of each image.
print("Left image:", left.shape)
print("Right image:", right.shape)

# Display both images.
cv2.imshow("Left Camera", left)
cv2.imshow("Right Camera", right)

# Wait until a key is pressed.
cv2.waitKey(0)

# Close the image windows.
cv2.destroyAllWindows()
