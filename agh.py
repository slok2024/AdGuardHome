import tkinter as tk
from tkinter import messagebox, ttk
import os
import subprocess
import ctypes
import webbrowser
import threading

def get_real_os_arch():
    """准确检测系统架构，无视 Python 位数"""
    if os.environ.get('PROCESSOR_ARCHITEW6432') or \
       os.environ.get('PROCESSOR_ARCHITECTURE', '').upper() == 'AMD64':
        return 64
    return 32

class AGHManager:
    def __init__(self, root):
        self.root = root
        self.root.title("AdGuard Home 管理助手")
        self.root.geometry("620x560")
        self.root.configure(bg="#F0F2F5")
        
        self.os_bits = get_real_os_arch()
        self.service_name = "AdGuardHome"
        
        # 定义颜色主题
        self.colors = {
            "primary": "#1890FF",
            "success": "#52C41A",
            "warning": "#FAAD14",
            "danger": "#FF4D4F",
            "dark": "#001529",
            "bg": "#F0F2F5"
        }
        
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        # 1. 顶部装饰栏
        header = tk.Frame(self.root, bg=self.colors["dark"], height=60)
        header.pack(fill="x")
        tk.Label(header, text="🛡️ ADGUARD HOME 部署面板", fg="white", bg=self.colors["dark"], 
                 font=("微软雅黑", 14, "bold")).pack(side="left", padx=20, pady=15)
        
        self.status_dot = tk.Label(header, text="● 离线", fg="#999", bg=self.colors["dark"], font=("微软雅黑", 10, "bold"))
        self.status_dot.pack(side="right", padx=20)

        # 2. 系统信息卡片
        info_frame = tk.Frame(self.root, bg="white", padx=15, pady=10)
        info_frame.pack(fill="x", padx=20, pady=15)
        tk.Label(info_frame, text=f"系统环境: Windows {self.os_bits}-bit (系统架构)", bg="white", fg="#666").pack(side="left")
        
        # 3. 内核选择
        core_frame = tk.Frame(self.root, bg="#F0F2F5")
        core_frame.pack(fill="x", padx=20)
        self.core_var = tk.StringVar(value="AGH64.exe" if self.os_bits == 64 else "AGH32.exe")
        
        tk.Label(core_frame, text="内核路径:", bg="#F0F2F5", font=("微软雅黑", 9, "bold")).pack(side="left")
        for text, val in [("64位内核 (AGH64.exe)", "AGH64.exe"), ("32位内核 (AGH32.exe)", "AGH32.exe")]:
            rb = tk.Radiobutton(core_frame, text=text, variable=self.core_var, value=val, 
                                bg="#F0F2F5", activebackground="#F0F2F5")
            rb.pack(side="left", padx=15)

        # 4. 主功能区
        main_container = tk.Frame(self.root, bg="#F0F2F5")
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # 左栏：便携模式
        left_box = tk.LabelFrame(main_container, text=" 便携模式 (不写系统) ", font=("微软雅黑", 9, "bold"), padx=10, pady=10)
        left_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tk.Label(left_box, text="直接调用 .exe 运行\n关闭此 UI 后内核继续驻留\n直至点击“强行终止”", fg="#999", font=("微软雅黑", 8), justify="left").pack(pady=5)
        
        # --- 按钮大小一致化调整 ---
        btn_config = {'relief': 'flat', 'height': 2, 'width': 20, 'font': ("微软雅黑", 9, "bold")}
        
        self.btn_run = tk.Button(left_box, text="🚀 启动内核进程", command=self.start_direct, 
                                 bg=self.colors["primary"], fg="white", **btn_config)
        self.btn_run.pack(pady=10)
        
        # 强行终止按钮：设为与启动按钮相同大小，并使用警示色
        tk.Button(left_box, text="⏹ 强行终止所有内核", command=self.stop_direct, 
                  bg="#7f8c8d", fg="white", **btn_config).pack(pady=5)

        # 右栏：服务模式
        right_box = tk.LabelFrame(main_container, text=" 系统服务 (开机自启) ", font=("微软雅黑", 9, "bold"), padx=10, pady=10)
        right_box.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        svc_btns = [
            ("➕ 安装服务", lambda: self.exec_svc("-s install"), self.colors["dark"]),
            ("▶ 启动服务", lambda: self.exec_svc("-s start"), self.colors["success"]),
            ("⏸ 停止服务", lambda: self.exec_svc("-s stop"), self.colors["warning"]),
            ("❌ 卸载服务", lambda: self.exec_svc("-s uninstall"), self.colors["danger"])
        ]
        for txt, cmd, clr in svc_btns:
            tk.Button(right_box, text=txt, command=cmd, bg=clr, fg="white", 
                      relief="flat", width=20, pady=5, font=("微软雅黑", 9, "bold")).pack(pady=4)

        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)

        # 5. 底部跳转
        footer = tk.Frame(self.root, bg="white")
        footer.pack(fill="x", side="bottom")
        tk.Button(footer, text="🌐 进入 Web 管理后台 (127.0.0.1:3000)", command=self.open_url, 
                  bg=self.colors["dark"], fg="white", font=("微软雅黑", 10, "bold"), 
                  relief="flat", padx=40, pady=15).pack(pady=10)

    def is_admin(self):
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

    def refresh_status(self):
        is_inst, is_run = self.check_system()
        if is_run:
            self.status_dot.config(text="● 在线 (核心运行中)", fg=self.colors["success"])
            self.btn_run.config(state="disabled", text="⚡ 进程已就绪")
        else:
            self.status_dot.config(text="● 离线 (未发现进程)", fg="#999")
            self.btn_run.config(state="normal", text="🚀 启动内核进程")
        self.root.after(2000, self.refresh_status)

    def check_system(self):
        is_running = False
        # 检测进程 (同时扫描 tasklist)
        try:
            task = subprocess.run(['tasklist'], capture_output=True, text=True, creationflags=0x08000000)
            if "agh64.exe" in task.stdout.lower() or "agh32.exe" in task.stdout.lower() or "adguardhome" in task.stdout.lower():
                is_running = True
        except: pass
        
        is_installed = False
        try:
            res = subprocess.run(['sc', 'query', self.service_name], capture_output=True, text=True, creationflags=0x08000000)
            if "SERVICE_NAME" in res.stdout:
                is_installed = True
        except: pass
        
        return is_installed, is_running

    def start_direct(self):
        exe = self.core_var.get()
        if not os.path.exists(exe):
            exe_alt = os.path.join("..", exe)
            if os.path.exists(exe_alt): exe = exe_alt
            else:
                messagebox.showerror("错误", f"找不到内核文件: {exe}")
                return
        
        threading.Thread(target=lambda: subprocess.Popen([exe], creationflags=0x08000000), daemon=True).start()
        messagebox.showinfo("启动", "内核进程已在后台发起启动。")

    def stop_direct(self):
        """
        彻底 Kill 掉所有相关的内核进程
        使用 /F 强制终止，/T 终止子进程
        """
        try:
            # 尝试杀掉所有可能的名字，确保彻底
            for target in ["AGH64.exe", "AGH32.exe", "AdGuardHome.exe"]:
                subprocess.run(['taskkill', '/F', '/T', '/IM', target], creationflags=0x08000000)
            messagebox.showinfo("清理", "已强制终止并清理所有 AdGuard Home 相关进程。")
        except Exception as e:
            messagebox.showerror("清理失败", f"终止进程时发生错误: {str(e)}")

    def exec_svc(self, args):
        if not self.is_admin():
            messagebox.showwarning("权限", "修改系统服务需要管理员权限！")
            return
        exe = self.core_var.get()
        target = exe if os.path.exists(exe) else os.path.join("..", exe)
        subprocess.run(f"{target} {args}", shell=True, creationflags=0x08000000)

    def open_url(self):
        webbrowser.open("http://127.0.0.1:3000")

if __name__ == "__main__":
    root = tk.Tk()
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = AGHManager(root)
    root.mainloop()