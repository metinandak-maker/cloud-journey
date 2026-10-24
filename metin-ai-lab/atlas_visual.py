"""Lightweight Atlas status animation; runs only on Tk's event loop."""
import math
from pathlib import Path
import tkinter as tk


class AtlasVisual(tk.Canvas):
    def __init__(self, parent, state, image_path, **kwargs):
        super().__init__(parent, width=160, height=160, bg="#f4f7fb",
                         highlightthickness=0, **kwargs)
        self.state = state
        self.angle = 0
        self.timer = None
        self.closed = False
        self.motion = True
        self.create_oval(8, 8, 152, 152, outline="#dce7f3", width=2)
        self.create_oval(19, 19, 141, 141, fill="#e8eef6", outline="")
        try:
            image = tk.PhotoImage(file=str(Path(image_path)))
            scale = max(1, math.ceil(max(image.width(), image.height()) / 96))
            self.image = image.subsample(scale, scale)
            self.create_image(80, 80, image=self.image)
        except (tk.TclError, OSError):
            self.create_text(80, 78, text="A", fill="#0f2a4a",
                             font=("Segoe UI", 36, "bold"))
        self.arcs = [self.create_arc(8, 8, 152, 152, start=i * 120,
                     extent=55, style="arc", outline="#2563eb", width=3)
                     for i in range(3)]
        self.dot = self.create_oval(0, 0, 0, 0, fill="#2563eb", outline="")
        self.label = self.create_text(80, 143, text="READY", fill="#2563eb",
                                     font=("Segoe UI", 8, "bold"))
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.tick()

    def set_motion(self, enabled):
        self.motion = bool(enabled)

    def tick(self):
        self.timer = None
        if self.closed:
            return
        state = self.state()
        color, speed, label = {
            "ready": ("#2563eb", 0.65, "READY"),
            "thinking": ("#0891b2", 3.0, "THINKING"),
            "cancelled": ("#b45309", 0, "STOPPING"),
            "killed": ("#dc2626", 0, "STOPPED"),
        }.get(state, ("#2563eb", 0.65, "READY"))
        if self.motion:
            self.angle = (self.angle + speed) % 360
        for i, arc in enumerate(self.arcs):
            self.itemconfigure(arc, start=self.angle + i * 120, outline=color)
        radians = math.radians(-self.angle)
        x, y = 80 + 72 * math.cos(radians), 80 + 72 * math.sin(radians)
        self.coords(self.dot, x - 4, y - 4, x + 4, y + 4)
        self.itemconfigure(self.dot, fill=color)
        self.itemconfigure(self.label, text=label, fill=color)
        self.timer = self.after(40, self.tick)

    def stop(self):
        self.closed = True
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None

    def _on_destroy(self, event):
        if event.widget is self:
            self.stop()
