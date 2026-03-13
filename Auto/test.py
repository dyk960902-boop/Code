import pyautogui
import time

print("5초 안에 1번 버튼 위에 마우스를 올려두세요.")
time.sleep(5)
x1, y1 = pyautogui.position()
print(f"버튼1 좌표: {x1}, {y1}")

print("5초 안에 2번 버튼 위에 마우스를 올려두세요.")
time.sleep(5)
x2, y2 = pyautogui.position()
print(f"버튼2 좌표: {x2}, {y2}")