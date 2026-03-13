import threading
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox

import pyautogui

pyautogui.FAILSAFE = False

try:
    import keyboard
except ImportError:
    keyboard = None

REWARD_ICON = "rewardicon.png"

BUTTON1_X = 1616
BUTTON1_Y = 1031
BUTTON2_X = 1719
BUTTON2_Y = 1032

REGION1 = (1556, 971, 120, 120)
REGION2 = (1659, 972, 120, 120)

CONFIDENCE = 0.85
SCAN_INTERVAL = 0.7
WAIT_AFTER_CLICK = 1.5
BUTTON_COOLDOWN = 5.0
MOVE_DURATION = 0.12


class RewardAutoClickApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reward Auto Click")
        self.root.geometry("520x560")
        self.root.resizable(False, False)

        self.running = False
        self.detecting_ok = False
        self.worker_thread = None
        self.hotkey_registered = False
        self.last_click_btn1 = 0.0
        self.last_click_btn2 = 0.0

        self.status_var = tk.StringVar(value="시작 버튼을 눌러주세요")

        self.build_ui()
        self.register_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown_app)

        self.log("프로그램 실행 완료")
        self.log("시작 버튼을 누르면 감시를 시작합니다")

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="Reward Auto Click",
            font=("Malgun Gothic", 16, "bold")
        )
        title.pack(pady=(14, 8))

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=16)

        tk.Label(
            status_frame,
            text="상태:",
            font=("Malgun Gothic", 11, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Malgun Gothic", 11)
        ).pack(side=tk.LEFT, padx=8)

        tk.Label(
            self.root,
            text="단축키: Ctrl+3 강제 종료",
            font=("Malgun Gothic", 9)
        ).pack(pady=(4, 8))

        # 버튼 영역을 먼저 아래에 고정
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(fill="x", padx=16, pady=(0, 16), side=tk.BOTTOM)

        self.start_button = tk.Button(
            self.button_frame,
            text="시작",
            width=12,
            height=2,
            command=self.start_monitoring,
            font=("Malgun Gothic", 10, "bold")
        )
        self.start_button.pack(side=tk.LEFT, padx=8, pady=4)

        self.restart_button = tk.Button(
            self.button_frame,
            text="재시작",
            width=12,
            height=2,
            command=self.restart_monitoring,
            font=("Malgun Gothic", 10, "bold")
        )

        self.exit_button = tk.Button(
            self.button_frame,
            text="종료",
            width=12,
            height=2,
            command=self.shutdown_app,
            font=("Malgun Gothic", 10, "bold")
        )

        # 로그창은 고정 높이로
        log_frame = tk.LabelFrame(
            self.root,
            text="실시간 상태",
            font=("Malgun Gothic", 10, "bold"),
            padx=8,
            pady=8
        )
        log_frame.pack(fill="both", padx=16, pady=(0, 12))

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            width=60,
            height=12,
            font=("Consolas", 10),
            state="disabled",
            wrap=tk.WORD
        )
        self.log_box.pack(fill="both")

    def register_hotkey(self):
        if keyboard is None:
            self.log("keyboard 패키지가 없어 Ctrl+3 강제 종료는 비활성화됨")
            return

        try:
            keyboard.add_hotkey("ctrl+3", self.force_quit_hotkey)
            self.hotkey_registered = True
            self.log("Ctrl+3 강제 종료 단축키 등록 완료")
        except Exception as e:
            self.log(f"단축키 등록 실패: {e}")

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert(tk.END, line)
            self.log_box.see(tk.END)
            self.log_box.configure(state="disabled")

        self.root.after(0, append)

    def show_runtime_buttons(self):
        self.start_button.pack_forget()

        if not self.restart_button.winfo_ismapped():
            self.restart_button.pack(side=tk.LEFT, padx=8, pady=4)

        if not self.exit_button.winfo_ismapped():
            self.exit_button.pack(side=tk.LEFT, padx=8, pady=4)

    def start_monitoring(self):
        if self.running:
            return

        self.running = True
        self.detecting_ok = False
        self.last_click_btn1 = 0.0
        self.last_click_btn2 = 0.0

        self.show_runtime_buttons()
        self.set_status("감시 시작 중")
        self.log("감시 시작 요청")

        self.worker_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.worker_thread.start()

    def restart_monitoring(self):
        self.log("재시작 요청")
        self.running = False
        time.sleep(0.2)
        self.start_monitoring()

    def shutdown_app(self):
        self.running = False
        self.detecting_ok = False

        try:
            if self.hotkey_registered and keyboard is not None:
                keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        self.root.destroy()

    def force_quit_hotkey(self):
        self.log("Ctrl+3 입력 감지 -> 프로그램 강제 종료")
        self.root.after(0, self.shutdown_app)

    def click_button(self, x, y, name):
        pyautogui.moveTo(x, y, duration=MOVE_DURATION)
        pyautogui.click()
        self.log(f"{name} 선택 완료")

    def check_reward_icon(self, region):
        try:
            return pyautogui.locateCenterOnScreen(
                REWARD_ICON,
                confidence=CONFIDENCE,
                region=region
            )
        except pyautogui.ImageNotFoundException:
            return None
        except Exception as e:
            self.log(f"아이콘 탐색 오류: {type(e).__name__} / {repr(e)}")
            return None

    def monitor_loop(self):
        while self.running:
            now = time.time()

            try:
                if not self.detecting_ok:
                    self.detecting_ok = True
                    self.set_status("정상 감시중")
                    self.log("정상 동작 상태 진입")

                found1 = self.check_reward_icon(REGION1)
                if found1 and (now - self.last_click_btn1 >= BUTTON_COOLDOWN):
                    self.set_status("정상 감시중")
                    self.log("1번영역에서 rewardicon 감지")
                    self.click_button(BUTTON1_X, BUTTON1_Y, "1번 버튼")
                    self.last_click_btn1 = time.time()
                    time.sleep(WAIT_AFTER_CLICK)
                    continue

                found2 = self.check_reward_icon(REGION2)
                if found2 and (now - self.last_click_btn2 >= BUTTON_COOLDOWN):
                    self.set_status("정상 감시중")
                    self.log("2번영역에서 rewardicon 감지")
                    self.click_button(BUTTON2_X, BUTTON2_Y, "2번 버튼")
                    self.last_click_btn2 = time.time()
                    time.sleep(WAIT_AFTER_CLICK)
                    continue

            except FileNotFoundError:
                self.running = False
                self.detecting_ok = False
                self.set_status("오류: rewardicon 파일 없음")
                self.log("rewardicon.png 파일을 찾을 수 없어 감시 중단")
                return

            except Exception as e:
                self.running = False
                self.detecting_ok = False
                self.set_status("오류 발생 - 재시작 가능")
                self.log(f"오류 타입: {type(e).__name__}")
                self.log(f"오류 내용: {repr(e)}")
                self.log("재시작 버튼으로 다시 시도할 수 있습니다")
                return

            time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = RewardAutoClickApp(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("오류", str(e))