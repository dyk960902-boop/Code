import os
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

import pyautogui

pyautogui.FAILSAFE = False

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    from pynput import mouse
except ImportError:
    mouse = None


# 실행 파일 기준 경로로 이동 (상대경로 정상 동작을 위해)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 아이콘 이미지 (상대경로 사용 - 한글 경로 문제 방지)
REWARD_ICON1 = "reward_icon1.png"
REWARD_ICON2 = "reward_icon2.png"

# 각 아이콘별 탐색 영역 (버튼 좌표 기준 주변 영역)
SEARCH_REGION1 = (1985, 1310, 120, 120)   # 버튼1 (2045, 1370) 기준
SEARCH_REGION2 = (2117, 1308, 120, 120)   # 버튼2 (2177, 1368) 기준

# 탐색 정확도
CONFIDENCE = 0.85

# 탐색 주기
SCAN_INTERVAL = 0.7

# 클릭 후 대기
WAIT_AFTER_CLICK = 1.5

# 좌표 입력 제한시간
CLICK_CAPTURE_TIMEOUT = 30


class RewardAutoClickApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Reward Auto Click")
        self.root.geometry("520x560")

        # 상태 변수
        self.running = False
        self.stop_requested = False

        # 클릭 좌표
        self.rewardpoint1 = None
        self.rewardpoint2 = None

        # UI 상태
        self.status_var = tk.StringVar(value="현재 상태: 시작 대기")

        self.build_ui()

        # 초기 안내 로그
        self.log("시작 버튼을 눌러 주세요.")

        if keyboard:
            keyboard.add_hotkey("ctrl+3", self.shutdown_app)

    # ---------------- UI ---------------- #

    def build_ui(self):

        tk.Label(
            self.root,
            text="Reward Auto Click",
            font=("Malgun Gothic", 16, "bold")
        ).pack(pady=10)

        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Malgun Gothic", 11)
        ).pack(pady=5)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)

        self.start_button = tk.Button(
            self.button_frame,
            text="시작",
            width=12,
            command=self.start_process
        )

        self.retry_button = tk.Button(
            self.button_frame,
            text="재시도",
            width=12,
            command=self.start_process
        )

        self.stop_button = tk.Button(
            self.button_frame,
            text="중단",
            width=12,
            command=self.stop_process
        )

        self.exit_button = tk.Button(
            self.button_frame,
            text="종료",
            width=12,
            command=self.shutdown_app
        )

        self.log_frame = tk.LabelFrame(self.root, text="로그")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_box = scrolledtext.ScrolledText(
            self.log_frame,
            state="disabled",
            height=14
        )

        self.log_box.pack(fill="both", expand=True)

        self.show_start_buttons()

    # ---------------- 로그 ---------------- #

    def log(self, msg):

        timestamp = time.strftime("%H:%M:%S")

        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state="disabled")

        self.root.after(0, append)

    def clear_log(self):

        def clear():
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", tk.END)
            self.log_box.configure(state="disabled")

        self.root.after(0, clear)

    # ---------------- 상태 ---------------- #

    def update_status(self, state):
        self.status_var.set(f"현재 상태: {state}")

    # ---------------- 버튼 상태 ---------------- #

    def clear_buttons(self):

        for w in self.button_frame.winfo_children():
            w.pack_forget()

    def show_start_buttons(self):

        self.clear_buttons()
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.exit_button.pack(side=tk.LEFT, padx=5)

    def show_retry_buttons(self):

        self.clear_buttons()
        self.retry_button.pack(side=tk.LEFT, padx=5)
        self.exit_button.pack(side=tk.LEFT, padx=5)

    def show_stop_button(self):

        self.clear_buttons()
        self.stop_button.pack()

    # ---------------- 좌표 입력 ---------------- #

    def capture_click(self):

        clicked = {"value": None}
        finished = threading.Event()

        def on_click(x, y, button, pressed):
            if pressed:
                clicked["value"] = (x, y)
                finished.set()
                return False

        listener = mouse.Listener(on_click=on_click)
        listener.start()

        start = time.time()

        while time.time() - start < CLICK_CAPTURE_TIMEOUT:

            if finished.is_set():
                listener.stop()
                return True, clicked["value"]

            # 중단 요청 시 즉시 탈출
            if self.stop_requested:
                listener.stop()
                return False, None

            time.sleep(0.05)

        listener.stop()
        return False, None

    # ---------------- 시작 흐름 ---------------- #

    def start_process(self):

        if mouse is None:
            self.update_status("pynput 패키지 필요")
            return

        # 플래그 초기화 및 로그 초기화
        self.stop_requested = False
        self.running = False
        self.clear_log()

        self.show_stop_button()
        self.update_status("좌표 설정 중")

        threading.Thread(target=self.setup_flow, daemon=True).start()

    def setup_flow(self):

        # STEP 1
        self.log("첫번째 좌표를 클릭해 주세요.")

        ok, point = self.capture_click()

        if self.stop_requested:
            return

        if not ok:
            self.root.after(0, lambda: self.update_status("좌표 저장 실패"))
            self.log("좌표 저장에 실패했습니다. 다시 시도해 주세요.")
            self.root.after(0, self.show_retry_buttons)
            return

        self.rewardpoint1 = point
        self.log(f"첫번째 좌표가 저장되었습니다: {point}")

        # STEP 2
        self.log("두번째 좌표를 클릭해 주세요.")

        ok, point = self.capture_click()

        if self.stop_requested:
            return

        if not ok:
            self.root.after(0, lambda: self.update_status("좌표 저장 실패"))
            self.log("좌표 저장에 실패했습니다. 다시 시도해 주세요.")
            self.root.after(0, self.show_retry_buttons)
            return

        self.rewardpoint2 = point
        self.log(f"두번째 좌표가 저장되었습니다: {point}")

        self.running = True
        self.root.after(0, lambda: self.update_status("정상 동작 중"))
        self.log("정상적으로 감지 중입니다. 아이콘이 나타나면 자동으로 클릭됩니다.")

        threading.Thread(target=self.monitor_loop, daemon=True).start()

    # ---------------- 백그라운드 클릭 ---------------- #

    def post_click(self, point):

        x, y = point
        pyautogui.moveTo(x, y)
        pyautogui.click()

    # ---------------- 감시 루프 ---------------- #

    def monitor_loop(self):

        while self.running and not self.stop_requested:

            try:

                # 아이콘1 탐지
                found1 = None
                try:
                    found1 = pyautogui.locateCenterOnScreen(
                        REWARD_ICON1,
                        confidence=CONFIDENCE,
                        region=SEARCH_REGION1
                    )
                except pyautogui.ImageNotFoundException:
                    pass

                if found1:
                    self.post_click(self.rewardpoint1)
                    self.log("아이템 상자 보상을 수령했습니다.")
                    time.sleep(WAIT_AFTER_CLICK)
                    continue

                # 아이콘2 탐지
                found2 = None
                try:
                    found2 = pyautogui.locateCenterOnScreen(
                        REWARD_ICON2,
                        confidence=CONFIDENCE,
                        region=SEARCH_REGION2
                    )
                except pyautogui.ImageNotFoundException:
                    pass

                if found2:
                    self.post_click(self.rewardpoint2)
                    self.log("이모지 상자 보상을 수령했습니다.")
                    time.sleep(WAIT_AFTER_CLICK)
                    continue

            except Exception as e:
                self.log(f"오류 발생: {type(e).__name__} / {repr(e)}")

            time.sleep(SCAN_INTERVAL)

    # ---------------- 중단 ---------------- #

    def stop_process(self):

        self.running = False
        self.stop_requested = True

        self.root.after(0, lambda: self.update_status("시작 대기"))
        self.log("프로그램이 중단되었습니다.")
        self.log("다시 시작하려면 시작 버튼을 눌러 주세요.")
        self.root.after(0, self.show_start_buttons)

    # ---------------- 종료 ---------------- #

    def shutdown_app(self):

        self.running = False
        self.stop_requested = True

        if keyboard:
            keyboard.unhook_all_hotkeys()

        self.root.destroy()


if __name__ == "__main__":

    try:

        root = tk.Tk()
        app = RewardAutoClickApp(root)
        root.mainloop()

    except Exception as e:

        messagebox.showerror("오류", str(e))