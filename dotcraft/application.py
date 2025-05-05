import cv2

from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import tkinter as tk
import os

from .core import (
    create_pixel_art,
    imread_unicode
)

class Application(tk.Tk):
    def __init__(self):
        '''
        Application クラスの初期化
        '''
        super().__init__()
        self.title("Dotcraft")
        self.geometry("900x500")
        self.minsize(900, 500)
        
        self.original_img = None   # OpenCV(BGR)
        self.pixelated_img = None  # OpenCV(BGR)

        self._build_menu()
        self._build_widgets()
    
    def _build_menu(self):
        '''
        メニューバーを構築
        '''
        mbar = tk.Menu(self)
        file_menu = tk.Menu(mbar, tearoff=False)
        file_menu.add_command(label="開く...", command=self.open_image)
        file_menu.add_command(label="保存 (ドット絵)...", command=self.save_pixelated)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.destroy)
        mbar.add_cascade(label="ファイル", menu=file_menu)
        self.config(menu=mbar)
    
    def _build_widgets(self):
        '''
        メインウィンドウのレイアウトを構築
        '''
        # 左：設定　右：画像エリア
        root_frame = ttk.Frame(self, padding=5)
        root_frame.pack(fill="both", expand=True)

        # --- 設定パネル --- #
        settings = ttk.LabelFrame(root_frame, text="設定")
        settings.pack(side="left", fill="y", padx=(0, 5))

        ttk.Label(settings, text="Pixel Size").pack(anchor="w")
        self.pixel_size_var = tk.IntVar(value=10)
        ttk.Spinbox(settings, from_=2, to=100, textvariable=self.pixel_size_var,
                    width=5).pack(anchor="w", pady=2)

        ttk.Label(settings, text="Color (k)").pack(anchor="w")
        self.k_var = tk.IntVar(value=8)
        ttk.Spinbox(settings, from_=2, to=32, textvariable=self.k_var,
                    width=5).pack(anchor="w", pady=2)

        ttk.Button(settings, text="適用", command=self.apply_pixelate)\
            .pack(anchor="w", pady=(10, 0))

        # --- 画像表示エリア --- #
        img_frame = ttk.Frame(root_frame)
        img_frame.pack(side="left", fill="both", expand=True)

        self.orig_label = ttk.Label(img_frame, text="元の画像", anchor="center")
        self.dot_label  = ttk.Label(img_frame, text="ドット絵", anchor="center")

        # Grid で左右に並べる
        img_frame.columnconfigure(0, weight=1)
        img_frame.columnconfigure(1, weight=1)
        img_frame.rowconfigure(0, weight=1)

        self.orig_label.grid(row=0, column=0, sticky="nsew", padx=5)
        self.dot_label.grid(row=0, column=1, sticky="nsew", padx=5)
    
    def open_image(self):
        '''
        画像を開くダイアログを表示し、選択された画像を読み込む
        '''
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        
        self.original_img = imread_unicode(path) # OpenCV で画像を読み込む
        
        if self.original_img is None:
            messagebox.showerror("Error", "画像を読み込めませんでした")
            return
        
        self._update_label(self.orig_label, self.original_img)
        self.pixelated_img = None
        self.dot_label.config(image="", text="ドット絵")
    
    def apply_pixelate(self):
        '''
        ピクセル化を適用し、結果を表示する
        '''
        if self.original_img is None:
            messagebox.showinfo("Info", "先に画像を開いてください")
            return
        p = max(2, self.pixel_size_var.get())
        k = max(2, self.k_var.get())
        self.pixelated_img = create_pixel_art(self.original_img, p, k)
        self._update_label(self.dot_label, self.pixelated_img)
    
    def save_pixelated(self):
        '''
        ピクセル化された画像を保存するダイアログを表示
        '''
        if self.pixelated_img is None:
            messagebox.showinfo("Info", "まだドット絵を生成していません")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")])
        if path:
            cv2.imwrite(path, self.pixelated_img)
            messagebox.showinfo("Saved", f"保存しました: {os.path.basename(path)}")
    
    def _update_label(self, label, img_bgr):
        '''
        OpenCV(BGR) 画像を Tkinter 用に変換して表示する
        
        Parameters
        ----------
        label : ttk.Label
            画像を表示するラベル
        img_bgr : numpy.ndarray
            OpenCV で読み込んだ画像 (BGR)
        '''
        # BGR -> RGB 変換
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # ウィンドウサイズに合わせて表示を縮小
        max_w = self.winfo_width() // 2 - 40
        scale = max_w / w if w > max_w else 1
        disp = cv2.resize(img_rgb, (int(w*scale), int(h*scale)),
                          interpolation=cv2.INTER_AREA)
        pil = Image.fromarray(disp)
        tkimg = ImageTk.PhotoImage(pil)
        label.config(image=tkimg, text="")
        label.image = tkimg  # keep reference
