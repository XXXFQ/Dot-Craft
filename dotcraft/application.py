import os
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Optional drag‑and‑drop support (pip install tkinterdnd2)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    BaseTk = TkinterDnD.Tk  # type: ignore[attr-defined]
    DND_AVAILABLE = True
except ImportError:  # graceful fallback if tkinterdnd2 is missing
    BaseTk = tk.Tk  # fallback to normal Tk
    DND_AVAILABLE = False

from .core import (
    create_pixel_art,
    imread_unicode,
)

class Application(BaseTk):
    '''
    Tkinter GUI for Dotcraft – compare original and pixel‑art images.
    '''
    def __init__(self) -> None:
        super().__init__()
        self.title("Dotcraft v1.0")
        self.geometry("900x500")
        self.minsize(900, 500)

        # placeholders for images (OpenCV BGR format)
        self.original_img = None  # type: ignore[arg-type]
        self.pixelated_img = None  # type: ignore[arg-type]

        self._update_job = None  # throttle real‑time updates

        self._build_menu()
        self._build_widgets()
        self._configure_dnd()

    # ---------------------------------------------------------------------
    # GUI building helpers
    # ---------------------------------------------------------------------
    def _build_menu(self) -> None:
        '''
        Construct the menubar.
        '''
        mbar = tk.Menu(self)
        file_menu = tk.Menu(mbar, tearoff=False)
        file_menu.add_command(label="開く...", command=self.open_image_dialog)
        file_menu.add_command(label="保存 (ドット絵)...", command=self.save_pixelated)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.destroy)
        mbar.add_cascade(label="ファイル", menu=file_menu)
        self.config(menu=mbar)

    def _build_widgets(self) -> None:
        '''
        Main window layout.
        '''
        # root container
        root_frame = ttk.Frame(self, padding=5)
        root_frame.pack(fill="both", expand=True)

        # -----------------------------------------------------------------
        # Settings panel (left)
        # -----------------------------------------------------------------
        settings = ttk.LabelFrame(root_frame, text="設定")
        settings.pack(side="left", fill="y", padx=(0, 5))

        # pixel size
        ttk.Label(settings, text="Pixel Size").pack(anchor="w")
        self.pixel_size_var = tk.IntVar(value=10)
        ttk.Spinbox(
            settings,
            from_=2,
            to=100,
            textvariable=self.pixel_size_var,
            width=6,
        ).pack(anchor="w", pady=2)

        # K colours
        ttk.Label(settings, text="Color (k)").pack(anchor="w")
        self.k_var = tk.IntVar(value=8)
        ttk.Spinbox(
            settings,
            from_=2,
            to=32,
            textvariable=self.k_var,
            width=6,
        ).pack(anchor="w", pady=2)

        # algorithm choice
        ttk.Label(settings, text="Algorithm").pack(anchor="w")
        self.algorithm_var = tk.StringVar(value="kmeans")
        ttk.Combobox(
            settings,
            state="readonly",
            values=("kmeans", "median", "octree"),
            textvariable=self.algorithm_var,
            width=10,
        ).pack(anchor="w", pady=2)

        # manual apply button (still useful for bulk changes)
        '''
        ttk.Button(settings, text="適用", command=self.apply_pixelate).pack(
            anchor="w", pady=(10, 0)
        )
        '''

        # trace variables for *real‑time* preview
        for var in (self.pixel_size_var, self.k_var, self.algorithm_var):
            var.trace_add("write", self._schedule_live_update)

        # -----------------------------------------------------------------
        # Image display area (right)
        # -----------------------------------------------------------------
        img_frame = ttk.Frame(root_frame)
        img_frame.pack(side="left", fill="both", expand=True)

        # configure grid (two columns)
        img_frame.columnconfigure(0, weight=1)
        img_frame.columnconfigure(1, weight=1)
        img_frame.rowconfigure(0, weight=1)

        self.orig_label = ttk.Label(img_frame, text="元の画像", anchor="center")
        self.dot_label = ttk.Label(img_frame, text="ドット絵", anchor="center")
        self.orig_label.grid(row=0, column=0, sticky="nsew", padx=5)
        self.dot_label.grid(row=0, column=1, sticky="nsew", padx=5)

    def _configure_dnd(self) -> None:
        '''
        Enable drag‑and‑drop for image files if library is available.
        '''
        if not DND_AVAILABLE:
            return  # silently ignore if tkinterdnd2 not installed
        self.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        self.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[arg-type]

    # ---------------------------------------------------------------------
    # File loading helpers
    # ---------------------------------------------------------------------
    def open_image_dialog(self) -> None:
        '''
        File‑dialog‑based loader (fallback).
        '''
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if path:
            self._load_image(path)

    def _on_drop(self, event) -> None:  # DnD callback
        paths = self.tk.splitlist(event.data)
        if not paths:
            return

        path = paths[0] # first file only
        path = path.strip("{}")  # braces appear when path contains spaces

        if os.path.isfile(path):
            self._load_image(path)

    def _load_image(self, path: str) -> None:
        '''
        Read the image (Unicode‑safe) and show it.
        '''
        img = imread_unicode(path)
        if img is None:
            messagebox.showerror("Error", "画像を読み込めませんでした")
            return
        self.original_img = img
        self._update_label(self.orig_label, img)
        self.pixelated_img = None
        self.dot_label.config(image="", text="ドット絵")

        # auto‑generate first preview
        self.apply_pixelate()

    # ---------------------------------------------------------------------
    # Image processing / preview
    # ---------------------------------------------------------------------
    def _schedule_live_update(self, *_) -> None:
        '''
        Debounce live preview to keep UI responsive.
        '''
        if self.original_img is None:
            return
        if self._update_job is not None:
            self.after_cancel(self._update_job)
        # refresh after 200 ms of inactivity
        self._update_job = self.after(200, self.apply_pixelate)

    def apply_pixelate(self) -> None:
        '''
        Generate pixel‑art preview using current parameters.
        '''
        if self.original_img is None:
            return
        p = max(2, self.pixel_size_var.get())
        k = max(2, self.k_var.get())
        algo = self.algorithm_var.get()
        self.pixelated_img = create_pixel_art(self.original_img, p, k, algo)
        self._update_label(self.dot_label, self.pixelated_img)
        self._update_job = None  # reset debounce flag

    # ---------------------------------------------------------------------
    # Saving
    # ---------------------------------------------------------------------
    def save_pixelated(self) -> None:
        '''
        Save the pixelated image to a file.
        '''
        if self.pixelated_img is None:
            messagebox.showinfo("Info", "まだドット絵を生成していません")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")],
        )
        if path:
            cv2.imwrite(path, self.pixelated_img)
            messagebox.showinfo("Saved", f"保存しました: {os.path.basename(path)}")

    # ---------------------------------------------------------------------
    # Utility – render OpenCV BGR as Tk image
    # ---------------------------------------------------------------------
    def _update_label(self, label: ttk.Label, img_bgr) -> None:  # type: ignore[override]
        '''
        Update the label with a new image (OpenCV BGR format).
        '''
        import numpy as np  # local import to avoid hard dependency if core handles images

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # fit into half the window width (with margin)
        max_w = self.winfo_width() // 2 - 40
        scale = max_w / w if w > max_w else 1
        disp = cv2.resize(img_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        pil_img = Image.fromarray(disp.astype(np.uint8))  # ensure uint8 type
        tk_img = ImageTk.PhotoImage(pil_img)
        label.config(image=tk_img, text="")
        label.image = tk_img  # reference to prevent GC
