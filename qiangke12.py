import requests
import time
import threading
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Combobox
from tkcalendar import Calendar

# 定义请求的 URL
url = "https://xsxk.zut.edu.cn/xsxk/elective/clazz/add"

# 共享状态：记录已经成功抢到的课程
success_courses = set()
# 线程锁
lock = threading.Lock()
# 控制抢课循环的标志位
stop_grabbing = False

# 免责声明内容
disclaimer_text = """
免责声明：
本程序仅供学习和研究使用，严禁用于任何非法用途。
作者不对因使用本程序而产生的任何后果负责。
请在使用前仔细阅读并同意本声明。
注意：抢课间隔过小将被视为DDOS攻击可能会负法律效应
         如果连续一小段时间内一直未抢到课程，请结束程序
"""

# 定义一个函数，用于显示免责声明弹窗
def show_disclaimer():
    # 创建弹窗
    disclaimer_window = Toplevel(root)
    disclaimer_window.title("免责声明")
    disclaimer_window.geometry("400x200")

    # 添加免责声明内容
    Label(disclaimer_window, text=disclaimer_text, justify="left", wraplength=380).pack(padx=10, pady=10)

    # 添加确认按钮
    def on_agree():
        disclaimer_window.destroy()  # 关闭弹窗
        root.deiconify()  # 显示主窗口

    Button(disclaimer_window, text="同意并继续", command=on_agree).pack(pady=10)

    # 禁止用户关闭弹窗前操作主窗口
    disclaimer_window.grab_set()
    disclaimer_window.protocol("WM_DELETE_WINDOW", lambda: messagebox.showwarning("警告", "请先同意免责声明！"))

# 抢课函数
def grab_course(headers, data, interval, result_text):
    global stop_grabbing
    while not stop_grabbing:
        try:
            with lock:
                if data["clazzId"] in success_courses:
                    break  # 如果课程已经被抢到，结束线程

            response = requests.post(url, headers=headers, data=data, timeout=10)  # 设置超时时间
            result = response.json()

            # 判断抢课成功条件
            if result["code"] == 500 and result["msg"] == "该课程已在选课结果中":
                with lock:
                    if data["clazzId"] not in success_courses:
                        success_courses.add(data["clazzId"])  # 记录成功抢到的课程
                        result_text.insert(END, f"抢课成功: {data['clazzId']}\n")
                    break  # 抢课成功，结束线程
            elif result["code"] == 200:
                result_text.insert(END, f"进入抢课队列: {data['clazzId']}\n")
            else:
                result_text.insert(END, f"抢课失败: {data['clazzId']} - {result['msg']}\n")
        except Exception as e:
            result_text.insert(END, f"请求异常: {data['clazzId']} - {str(e)}\n")
        time.sleep(interval)

# 立即抢课（单个课程）
def grab_immediately():
    global stop_grabbing
    stop_grabbing = False  # 重置标志位
    headers = {
        "Authorization": auth_entry.get(),
        "Cookie": cookie_entry.get(),
        "User-Agent": user_agent_entry.get(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    clazz_type = clazz_type_entry.get()
    clazz_id = clazz_id_entry.get()
    secret_val = secret_val_entry.get()
    interval = float(interval_entry.get())

    data = {
        "clazzType": clazz_type,
        "clazzId": clazz_id,
        "secretVal": secret_val,
    }

    threading.Thread(
        target=grab_course,
        args=(headers, data, interval, result_text),
        daemon=True,
    ).start()

# 立即连续抢课（多个课程）
def grab_multiple_immediately():
    global stop_grabbing
    stop_grabbing = False  # 重置标志位
    headers = {
        "Authorization": auth_entry.get(),
        "Cookie": cookie_entry.get(),
        "User-Agent": user_agent_entry.get(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    clazz_type = clazz_type_entry.get()
    clazz_ids = clazz_ids_entry.get().split(",")
    secret_vals = secret_vals_entry.get().split(",")
    interval = float(interval_entry.get())

    if len(clazz_ids) != len(secret_vals):
        messagebox.showerror("错误", "课程ID和密钥数量不匹配！")
        return

    for clazz_id, secret_val in zip(clazz_ids, secret_vals):
        data = {
            "clazzType": clazz_type,
            "clazzId": clazz_id.strip(),
            "secretVal": secret_val.strip(),
        }
        threading.Thread(
            target=grab_course,
            args=(headers, data, interval, result_text),
            daemon=True,
        ).start()

# 启动抢课（定时抢课）
def start_grabbing():
    global stop_grabbing
    stop_grabbing = False  # 重置标志位
    headers = {
        "Authorization": auth_entry.get(),
        "Cookie": cookie_entry.get(),
        "User-Agent": user_agent_entry.get(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    clazz_type = clazz_type_entry.get()
    clazz_id = clazz_id_entry.get()
    secret_val = secret_val_entry.get()
    interval = float(interval_entry.get())
    selected_date = cal.get_date()
    selected_time = f"{hour_combobox.get()}:{minute_combobox.get()}:{second_combobox.get()}"

    data = {
        "clazzType": clazz_type,
        "clazzId": clazz_id,
        "secretVal": secret_val,
    }

    # 定时抢课
    target_time = f"{selected_date} {selected_time}"
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if current_time != target_time:
        result_text.insert(END, f"等待定时时间: {target_time}\n")
        threading.Thread(
            target=wait_and_start,
            args=(headers, data, interval, result_text, target_time),
            daemon=True,
        ).start()
    else:
        threading.Thread(
            target=grab_course,
            args=(headers, data, interval, result_text),
            daemon=True,
        ).start()

# 等待定时时间
def wait_and_start(headers, data, interval, result_text, target_time):
    while time.strftime("%Y-%m-%d %H:%M:%S") != target_time:
        time.sleep(1)
    threading.Thread(
        target=grab_course,
        args=(headers, data, interval, result_text),
        daemon=True,
    ).start()

# 连续抢多个课程（定时抢课）
def start_multiple_grabbing():
    global stop_grabbing
    stop_grabbing = False  # 重置标志位
    headers = {
        "Authorization": auth_entry.get(),
        "Cookie": cookie_entry.get(),
        "User-Agent": user_agent_entry.get(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    clazz_type = clazz_type_entry.get()
    clazz_ids = clazz_ids_entry.get().split(",")
    secret_vals = secret_vals_entry.get().split(",")
    interval = float(interval_entry.get())
    selected_date = cal.get_date()
    selected_time = f"{hour_combobox.get()}:{minute_combobox.get()}:{second_combobox.get()}"

    if len(clazz_ids) != len(secret_vals):
        messagebox.showerror("错误", "课程ID和密钥数量不匹配！")
        return

    # 定时抢课
    target_time = f"{selected_date} {selected_time}"
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if current_time != target_time:
        result_text.insert(END, f"等待定时时间: {target_time}\n")
        threading.Thread(
            target=wait_and_start_multiple,
            args=(headers, clazz_type, clazz_ids, secret_vals, interval, result_text, target_time),
            daemon=True,
        ).start()
    else:
        for clazz_id, secret_val in zip(clazz_ids, secret_vals):
            data = {
                "clazzType": clazz_type,
                "clazzId": clazz_id.strip(),
                "secretVal": secret_val.strip(),
            }
            threading.Thread(
                target=grab_course,
                args=(headers, data, interval, result_text),
                daemon=True,
            ).start()

# 等待定时时间（多课程）
def wait_and_start_multiple(headers, clazz_type, clazz_ids, secret_vals, interval, result_text, target_time):
    while time.strftime("%Y-%m-%d %H:%M:%S") != target_time:
        time.sleep(1)
    for clazz_id, secret_val in zip(clazz_ids, secret_vals):
        data = {
            "clazzType": clazz_type,
            "clazzId": clazz_id.strip(),
            "secretVal": secret_val.strip(),
        }
        threading.Thread(
            target=grab_course,
            args=(headers, data, interval, result_text),
            daemon=True,
        ).start()

# 结束抢课
def stop_grabbing_loop():
    global stop_grabbing
    stop_grabbing = True
    result_text.insert(END, "抢课已停止\n")
    with lock:
        success_courses.clear()  # 清空成功抢到的课程记录

def re_grabbing_loop():
    global stop_grabbing
    stop_grabbing = False
    result_text.insert(END, "标志已重置\n")
def sylxlm():
    messagebox.showinfo("Hello", "PowerBy - 小懒猫")

# 创建 GUI
root = Tk()
root.title("自动抢课程序")
root.geometry("700x800")

# 隐藏主窗口，直到用户同意免责声明
root.withdraw()

# 显示免责声明弹窗
show_disclaimer()

# 请求头输入
Label(root, text="Authorization:").grid(row=0, column=0, padx=10, pady=5, sticky=W)
auth_entry = Entry(root, width=50)
auth_entry.grid(row=0, column=1, padx=10, pady=5)

Label(root, text="Cookie:").grid(row=1, column=0, padx=10, pady=5, sticky=W)
cookie_entry = Entry(root, width=50)
cookie_entry.grid(row=1, column=1, padx=10, pady=5)

Label(root, text="User-Agent:").grid(row=2, column=0, padx=10, pady=5, sticky=W)
user_agent_entry = Entry(root, width=50)
user_agent_entry.grid(row=2, column=1, padx=10, pady=5)

# 请求负载输入
Label(root, text="课程类型 (clazzType):").grid(row=3, column=0, padx=10, pady=5, sticky=W)
clazz_type_entry = Entry(root, width=50)
clazz_type_entry.grid(row=3, column=1, padx=10, pady=5)

Label(root, text="课程ID (clazzId):").grid(row=4, column=0, padx=10, pady=5, sticky=W)
clazz_id_entry = Entry(root, width=50)
clazz_id_entry.grid(row=4, column=1, padx=10, pady=5)

Label(root, text="密钥 (secretVal):").grid(row=5, column=0, padx=10, pady=5, sticky=W)
secret_val_entry = Entry(root, width=50)
secret_val_entry.grid(row=5, column=1, padx=10, pady=5)

# 多课程输入
Label(root, text="多个课程ID (逗号分隔):").grid(row=6, column=0, padx=10, pady=5, sticky=W)
clazz_ids_entry = Entry(root, width=50)
clazz_ids_entry.grid(row=6, column=1, padx=10, pady=5)

Label(root, text="多个密钥 (逗号分隔):").grid(row=7, column=0, padx=10, pady=5, sticky=W)
secret_vals_entry = Entry(root, width=50)
secret_vals_entry.grid(row=7, column=1, padx=10, pady=5)

# 抢课间隔
Label(root, text="抢课间隔 (秒):").grid(row=8, column=0, padx=10, pady=5, sticky=W)
interval_entry = Entry(root, width=50)
interval_entry.insert(0, "1")  # 默认间隔 1 秒
interval_entry.grid(row=8, column=1, padx=10, pady=5)

# 定时抢课日期选择
Label(root, text="选择日期:").grid(row=9, column=0, padx=10, pady=5, sticky=W)
cal = Calendar(root, selectmode="day", date_pattern="yyyy-mm-dd")
cal.grid(row=9, column=1, padx=10, pady=5)

# 定时抢课时间选择
Label(root, text="选择时间 (HH:MM:SS):").grid(row=10, column=0, padx=10, pady=5, sticky=W)
time_frame = Frame(root)
time_frame.grid(row=10, column=1, padx=10, pady=5, sticky=W)

hour_combobox = Combobox(time_frame, width=5, values=[f"{i:02d}" for i in range(24)])
hour_combobox.current(0)
hour_combobox.pack(side=LEFT)

minute_combobox = Combobox(time_frame, width=5, values=[f"{i:02d}" for i in range(60)])
minute_combobox.current(0)
minute_combobox.pack(side=LEFT)

second_combobox = Combobox(time_frame, width=5, values=[f"{i:02d}" for i in range(60)])
second_combobox.current(0)
second_combobox.pack(side=LEFT)

# 按钮
Button(root, text="立即抢课", command=grab_immediately).grid(row=11, column=0, padx=10, pady=10)
Button(root, text="立即连续抢课", command=grab_multiple_immediately).grid(row=11, column=1, padx=10, pady=10)
Button(root, text="开始抢课", command=start_grabbing).grid(row=12, column=0, padx=10, pady=10)
Button(root, text="连续抢多个课程", command=start_multiple_grabbing).grid(row=12, column=1, padx=10, pady=10)
Button(root, text="结束抢课", command=stop_grabbing_loop).grid(row=12, column=2, padx=10, pady=10)
Button(root, text="重置标志", command=re_grabbing_loop).grid(row=11, column=2, padx=10, pady=10)
Button(root, text="PowerBy - 小懒猫", command=sylxlm).grid(row=11, column=2, padx=10, pady=10)

# 结果显示
result_text = Text(root, height=10, width=70)
result_text.grid(row=13, column=0, columnspan=3, padx=10, pady=10)

# 运行 GUI
root.mainloop()
