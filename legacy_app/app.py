"""Staged legacy app: CairoTrade Order Entry v3.2 (2004). Tkinter."""
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
from .rules import order_total, discounted_subtotal, vat_amount, exceeds_credit_limit

CUSTOMERS = [
    {"id": "C001", "name": "Ahmed Hassan", "limit": Decimal("5000")},
    {"id": "C002", "name": "Mona El-Sayed", "limit": Decimal("2000")},
]
ITEMS = [
    {"sku": "ITM-01", "name": "Valve A", "price": Decimal("100")},
    {"sku": "ITM-02", "name": "Gasket B", "price": Decimal("10")},
]

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CairoTrade Order Entry v3.2 (2004)")
        self.geometry("640x480")
        self.user: str | None = None
        self.lines: list[dict] = []
        self.orders: list[dict] = []
        menubar = tk.Menu(self)
        fmenu = tk.Menu(menubar, tearoff=0)
        fmenu.add_command(label="Archive", command=self.do_nothing)  # trap for coverage ledger
        fmenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=fmenu)
        self.config(menu=menubar)
        self.frames: dict[str, ttk.Frame] = {}
        for name in ("login", "menu", "customers", "order", "report"):
            fr = ttk.Frame(self, padding=12)
            fr.grid(row=0, column=0, sticky="nsew")
            self.frames[name] = fr
        self._build_login()
        self._build_menu()
        self._build_customers()
        self._build_order()
        self._build_report()
        self.show("login")
        self.bind_all("<F2>", lambda e: self.save_order())
        self.bind_all("<F5>", lambda e: self.refresh())
        self.bind_all("<Escape>", lambda e: self.cancel())

    def do_nothing(self) -> None:
        pass  # File > Archive intentionally does nothing

    def show(self, name: str) -> None:
        self.frames[name].tkraise()
        self.current = name

    def _build_login(self) -> None:
        f = self.frames["login"]
        ttk.Label(f, text="CairoTrade Login").pack()
        self.e_user = ttk.Entry(f); self.e_user.pack()
        self.e_user.insert(0, "admin")
        self.e_pass = ttk.Entry(f, show="*"); self.e_pass.pack()
        self.e_pass.insert(0, "admin")
        ttk.Button(f, text="Login", command=self.login).pack()

    def login(self) -> None:
        if self.e_user.get() == "admin" and self.e_pass.get() == "admin":
            self.user = "admin"
            self.show("menu")
        else:
            messagebox.showerror("Login", "Invalid credentials")

    def _build_menu(self) -> None:
        f = self.frames["menu"]
        ttk.Label(f, text="Main menu").pack()
        ttk.Button(f, text="Customer lookup", command=lambda: self.show("customers")).pack(fill="x")
        ttk.Button(f, text="Order entry", command=lambda: self.show("order")).pack(fill="x")
        ttk.Button(f, text="Daily report", command=lambda: self.show("report")).pack(fill="x")

    def _build_customers(self) -> None:
        f = self.frames["customers"]
        ttk.Label(f, text="Customer lookup").pack()
        self.e_search = ttk.Entry(f); self.e_search.pack(fill="x")
        self.lb_cust = tk.Listbox(f); self.lb_cust.pack(fill="both", expand=True)
        ttk.Button(f, text="Search", command=self.search_cust).pack()
        ttk.Button(f, text="Back", command=lambda: self.show("menu")).pack()
        self.search_cust()

    def search_cust(self) -> None:
        q = self.e_search.get().lower() if hasattr(self, "e_search") else ""
        self.lb_cust.delete(0, tk.END)
        for c in CUSTOMERS:
            if q in c["name"].lower() or q in c["id"].lower() or not q:
                self.lb_cust.insert(tk.END, f"{c['id']} {c['name']} lim={c['limit']}")

    def _build_order(self) -> None:
        f = self.frames["order"]
        ttk.Label(f, text="Order entry (F2 save, F5 refresh, Esc cancel)").pack()
        self.cb_cust = ttk.Combobox(f, values=[c["id"] for c in CUSTOMERS])
        self.cb_cust.set("C001"); self.cb_cust.pack(fill="x")
        self.cb_item = ttk.Combobox(f, values=[i["sku"] for i in ITEMS])
        self.cb_item.set("ITM-01"); self.cb_item.pack(fill="x")
        self.e_qty = ttk.Entry(f); self.e_qty.insert(0, "1"); self.e_qty.pack(fill="x")
        ttk.Button(f, text="Add line", command=self.add_line).pack()
        self.lb_lines = tk.Listbox(f); self.lb_lines.pack(fill="both", expand=True)
        self.lbl_tot = ttk.Label(f, text="Total: 0.00 EGP"); self.lbl_tot.pack()
        ttk.Button(f, text="Back", command=lambda: self.show("menu")).pack()

    def add_line(self) -> None:
        sku = self.cb_item.get()
        price = next(i["price"] for i in ITEMS if i["sku"] == sku)
        try:
            qty = int(self.e_qty.get())
        except ValueError:
            messagebox.showerror("Order", "Qty must be integer")
            return
        self.lines.append({"sku": sku, "qty": qty, "price": price})
        self.lb_lines.insert(tk.END, f"{sku} x{qty} @ {price}")
        self.update_totals()

    def update_totals(self) -> None:
        sub = discounted_subtotal(self.lines) if self.lines else Decimal("0")
        vat = vat_amount(sub) if self.lines else Decimal("0")
        tot = order_total(self.lines) if self.lines else Decimal("0")
        self.lbl_tot.config(text=f"Sub={sub} VAT={vat} Total={tot} EGP")

    def save_order(self) -> None:
        if getattr(self, "current", "") != "order":
            return
        if not self.lines:
            messagebox.showwarning("Order", "No lines")
            return
        tot = order_total(self.lines)
        cust = next(c for c in CUSTOMERS if c["id"] == self.cb_cust.get())
        if exceeds_credit_limit(tot, cust["limit"]):
            ok = messagebox.askyesno("Credit warning",
                f"Total {tot} exceeds limit {cust['limit']}. Continue?")
            if not ok:
                return
        self.orders.append({"cust": cust["id"], "lines": list(self.lines), "total": str(tot)})
        messagebox.showinfo("Order", f"Saved total {tot} EGP")
        self.lines.clear(); self.lb_lines.delete(0, tk.END); self.update_totals()

    def refresh(self) -> None:
        if getattr(self, "current", "") == "order":
            self.update_totals()
        elif getattr(self, "current", "") == "customers":
            self.search_cust()
        elif getattr(self, "current", "") == "report":
            self.load_report()

    def cancel(self) -> None:
        if getattr(self, "current", "") == "order":
            self.lines.clear()
            if hasattr(self, "lb_lines"):
                self.lb_lines.delete(0, tk.END); self.update_totals()
        self.show("menu")

    def _build_report(self) -> None:
        f = self.frames["report"]
        ttk.Label(f, text="Daily report").pack()
        self.lb_rep = tk.Listbox(f); self.lb_rep.pack(fill="both", expand=True)
        ttk.Button(f, text="Refresh", command=self.load_report).pack()
        ttk.Button(f, text="Back", command=lambda: self.show("menu")).pack()

    def load_report(self) -> None:
        self.lb_rep.delete(0, tk.END)
        for o in self.orders:
            self.lb_rep.insert(tk.END, f"{o['cust']} total={o['total']}")
        if not self.orders:
            self.lb_rep.insert(tk.END, "(no orders today)")

if __name__ == "__main__":
    App().mainloop()