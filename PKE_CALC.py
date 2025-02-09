import tkinter as tk
from tkinter import ttk, messagebox
import struct

# -----------------------------
# Dictionary for Error Codes (Based on Table 2-3)
# -----------------------------
error_codes = {
    0: "Illegal parameter number (PNU) - Parameter does not exist",
    1: "Parameter value cannot be modified - Parameter is read-only",
    2: "Minimum/maximum not reached/exceeded",
    3: "Faulty subindex",
    4: "No array - Single parameter has been accessed with array request and subindex > 0",
    5: "Incorrect data type - Mix-up between word and double word",
    6: "Setting not allowed (resetting only)",
    7: "Descriptive element cannot be modified - Description can never be modified",
    11: "No status as master control - Modification request without status as master control (see P0927)",
    12: "Key word missing",
    17: "Request cannot be processed due to operating state - Current inverter status is not compatible with the received request",
    101: "Parameter number currently deactivated - Dependent on inverter status",
    102: "Channel not wide enough - Communication channel too small for response",
    104: "Illegal parameter value - Parameter permits only certain values",
    106: "Request not implemented - After request identifier 5, 10, 15",
    200: "Modified minimum/maximum not reached/exceeded",
    201: "Modified minimum/maximum not reached/exceeded",
    204: "Available access authorization does not cover modification of parameters"
}

# -----------------------------
# Functions for Telegram Generation and Conversion
# -----------------------------

def calculate_pke(parameter, ak):
    """
    محاسبه کلمه PKE و مقدار ext (PARA PAGE SEL) بر اساس شماره پارامتر:
    
      Parameter Range      Offset   PARA PAGE SEL (ext)
      0 … 1999             0        0x00
      2000 … 3999          2000     0x80
      4000 … 5999          4000     0x10
      6000 … 7999          6000     0x90
      8000 … 9999          8000     0x20
      60000 … 61999        60000    0x74
    """
    if parameter < 2000:
        offset = 0
        ext = 0x00
    elif parameter < 4000:
        offset = 2000
        ext = 0x80
    elif parameter < 6000:
        offset = 4000
        ext = 0x10
    elif parameter < 8000:
        offset = 6000
        ext = 0x90
    elif parameter < 10000:
        offset = 8000
        ext = 0x20
    elif 60000 <= parameter < 62000:
        offset = 60000
        ext = 0x74
    else:
        raise ValueError("Parameter out of supported range.")
    
    adjusted = parameter - offset
    pke = (ak << 12) | adjusted
    return pke, ext

def build_ind(subindex, ext):
    """ساخت کلمه IND از subindex (بایت بالا) و ext (بایت پایین)."""
    return (subindex << 8) | ext

def convert_ieee(value):
    """
    تبدیل مقدار اعشاری به فرمت IEEE 754 (32 بیت).
    خروجی: (PWE1, PWE2)
    مثال: 50.00 -> 0x4248 0000.
    """
    packed = struct.pack('!f', value)
    int_val = struct.unpack('!I', packed)[0]
    pwe1 = (int_val >> 16) & 0xFFFF
    pwe2 = int_val & 0xFFFF
    return pwe1, pwe2

def convert_word(value):
    """
    تبدیل مقدار به عدد صحیح 16-بیتی (word).
    خروجی: (PWE1 = 0x0000, PWE2 = مقدار به صورت هگز)
    مثال: 27 -> 0x0000 و 0x001B.
    """
    pwe1 = 0x0000
    pwe2 = int(value) & 0xFFFF
    return pwe1, pwe2

def convert_custom(value):
    """
    تبدیل اختصاصی (برای مثال، برای P0845):
      - قسمت صحیح -> PWE1
      - قسمت کسری (ضرب در 10) -> PWE2
    مثال: 722.2 -> PWE1 = 0x02D2, PWE2 = 0x0002.
    """
    int_part = int(value)
    frac_part = value - int_part
    frac_converted = round(frac_part * 10)
    pwe1 = int_part & 0xFFFF
    pwe2 = frac_converted & 0xFFFF
    return pwe1, pwe2

def auto_conversion(parameter, param_value):
    """
    انتخاب خودکار نوع تبدیل بر اساس شماره پارامتر:
      - برای 2051: از تبدیل word استفاده شود.
      - برای 1082: از تبدیل IEEE استفاده شود.
      - برای 2010: از تبدیل word استفاده شود.
      - برای 845: از تبدیل custom استفاده شود.
      - سایر پارامترها: اگر مقدار اعشاری است → IEEE، در غیر این صورت word.
    """
    if parameter == 2051:
        return convert_word(param_value)
    elif parameter == 1082:
        return convert_ieee(param_value)
    elif parameter == 2010:
        return convert_word(param_value)
    elif parameter == 845:
        return convert_custom(param_value)
    else:
        if param_value != int(param_value):
            return convert_ieee(param_value)
        else:
            return convert_word(param_value)

# -----------------------------
# Function for Generating Telegram (Request/Write)
# -----------------------------
def calculate_telegram():
    try:
        op = operation_var.get()   # "read" یا "write"
        parameter = int(parameter_entry.get())
        # استخراج عدد AK از منوی کشویی (قبل از اولین فاصله)
        ak = int(ak_var.get().split()[0])
        subindex = int(subindex_entry.get()) if subindex_entry.get() else 0

        pke, ext = calculate_pke(parameter, ak)
        ind = build_ind(subindex, ext)
        
        if op == "write":
            param_value = float(parameter_value_entry.get())
            pwe1, pwe2 = auto_conversion(parameter, param_value)
        else:
            pwe1 = 0x0000
            pwe2 = 0x0000

        output = f"1st word (PKE): 0x{pke:04X}\n"
        output += f"2nd word (IND): 0x{ind:04X}\n"
        output += f"3rd word (PWE1): 0x{pwe1:04X}\n"
        output += f"4th word (PWE2): 0x{pwe2:04X}\n"
        result_text.config(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, output)
        result_text.config(state=tk.DISABLED)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def toggle_parameter_value_entry():
    if operation_var.get() == "write":
        parameter_value_entry.config(state=tk.NORMAL)
    else:
        parameter_value_entry.config(state=tk.DISABLED)

# -----------------------------
# Function for Decoding a Response Telegram
# -----------------------------
def decode_response():
    try:
        # دریافت ورودی‌های تلگرام پاسخ (به صورت هگز)
        pke_resp = int(response_pke_entry.get(), 16)
        ind_resp = int(response_ind_entry.get(), 16)
        pwe1_resp = int(response_pwe1_entry.get(), 16)
        pwe2_resp = int(response_pwe2_entry.get(), 16)
        
        # استخراج AK از PKE (بیت‌های 12 تا 15)
        ak_resp = (pke_resp >> 12) & 0xF
        raw_param = pke_resp & 0x07FF  # بیت‌های 0 تا 10
        
        # استخراج subindex و ext از IND
        subindex = (ind_resp >> 8) & 0xFF
        ext = ind_resp & 0xFF
        
        # تعیین offset بر اساس ext
        if ext == 0x00:
            offset = 0
        elif ext == 0x80:
            offset = 2000
        elif ext == 0x10:
            offset = 4000
        elif ext == 0x90:
            offset = 6000
        elif ext == 0x20:
            offset = 8000
        elif ext == 0x74:
            offset = 60000
        else:
            offset = 0
        
        actual_param = raw_param + offset
        
        result = f"Decoded Response Telegram:\n"
        result += f"1st word (PKE): 0x{pke_resp:04X} -> AK = {ak_resp}\n"
        result += f"Parameter number (PNU): {actual_param} (raw: 0x{raw_param:03X}, offset: {offset})\n"
        result += f"Subindex: {subindex}\n"
        result += f"2nd word (IND): 0x{ind_resp:04X}\n"
        result += f"3rd word (PWE1): 0x{pwe1_resp:04X}\n"
        result += f"4th word (PWE2): 0x{pwe2_resp:04X}\n"
        
        # در صورتیکه AK برابر 7 باشد، پاسخ خطا دارد.
        if ak_resp == 7:
            error_code = pwe2_resp
            error_meaning = error_codes.get(error_code, "Unknown error code")
            result += f"\nError Code: {error_code} -> {error_meaning}\n"
        else:
            # تفسیر مقدار پارامتر:
            # اگر PWE1 غیر صفر باشد، فرض می‌کنیم مقدار به صورت IEEE (double word) است.
            if pwe1_resp != 0:
                int_val = (pwe1_resp << 16) | pwe2_resp
                try:
                    float_val = struct.unpack('!f', struct.pack('!I', int_val))[0]
                    result += f"\nInterpreted Value (IEEE float): {float_val}\n"
                except Exception as e:
                    result += f"\nError decoding IEEE float: {e}\n"
            else:
                result += f"\nInterpreted Value (Word): {pwe2_resp}\n"
        
        decode_result_text.config(state=tk.NORMAL)
        decode_result_text.delete("1.0", tk.END)
        decode_result_text.insert(tk.END, result)
        decode_result_text.config(state=tk.DISABLED)
    except Exception as e:
        messagebox.showerror("Decode Error", str(e))

# -----------------------------
# Build UI with Notebook (2 Tabs: Generate Telegram and Decode Response)
# -----------------------------
root = tk.Tk()
root.title("PKE/Telegram Calculator and Response Decoder")

notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# ----- Tab 1: Generate Telegram (Request/Write) -----
tab_generate = ttk.Frame(notebook)
notebook.add(tab_generate, text="Generate Telegram")

# Operation (read/write)
tk.Label(tab_generate, text="Operation:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
operation_var = tk.StringVar(value="read")
operation_frame = tk.Frame(tab_generate)
operation_frame.grid(row=0, column=1, sticky="w", padx=5, pady=5)
tk.Radiobutton(operation_frame, text="Read", variable=operation_var, value="read", command=toggle_parameter_value_entry).pack(side=tk.LEFT)
tk.Radiobutton(operation_frame, text="Write", variable=operation_var, value="write", command=toggle_parameter_value_entry).pack(side=tk.LEFT)

# Parameter number
tk.Label(tab_generate, text="Parameter number:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
parameter_entry = tk.Entry(tab_generate)
parameter_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
parameter_entry.insert(0, "2051")

# AK dropdown
tk.Label(tab_generate, text="AK (Request/Response Identifier):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
ak_options = [
    "1 - Request parameter value",
    "2 - Modify parameter value (word)",
    "3 - Modify parameter value (double word)"
]
ak_var = tk.StringVar(value=ak_options[2])
ak_dropdown = ttk.Combobox(tab_generate, textvariable=ak_var, values=ak_options, state="readonly", width=35)
ak_dropdown.grid(row=2, column=1, sticky="w", padx=5, pady=5)

# Subindex
tk.Label(tab_generate, text="Subindex (default 0):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
subindex_entry = tk.Entry(tab_generate)
subindex_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
subindex_entry.insert(0, "0")

# Parameter value (only active in write mode)
tk.Label(tab_generate, text="Parameter value:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
parameter_value_entry = tk.Entry(tab_generate)
parameter_value_entry.grid(row=4, column=1, sticky="w", padx=5, pady=5)
parameter_value_entry.insert(0, "27")
if operation_var.get() == "read":
    parameter_value_entry.config(state=tk.DISABLED)

# Calculate Telegram button
calculate_button = tk.Button(tab_generate, text="Calculate Telegram", command=calculate_telegram)
calculate_button.grid(row=5, column=0, columnspan=2, pady=10)

# Output Text widget for generated telegram
result_text = tk.Text(tab_generate, height=7, width=40, state=tk.DISABLED)
result_text.grid(row=6, column=0, columnspan=2, padx=5, pady=10)

# ----- Tab 2: Decode Response Telegram -----
tab_decode = ttk.Frame(notebook)
notebook.add(tab_decode, text="Decode Response")

tk.Label(tab_decode, text="Enter Response Telegram Fields (in hex):").grid(row=0, column=0, columnspan=2, pady=5)

tk.Label(tab_decode, text="1st word (PKE):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
response_pke_entry = tk.Entry(tab_decode)
response_pke_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

tk.Label(tab_decode, text="2nd word (IND):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
response_ind_entry = tk.Entry(tab_decode)
response_ind_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

tk.Label(tab_decode, text="3rd word (PWE1):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
response_pwe1_entry = tk.Entry(tab_decode)
response_pwe1_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

tk.Label(tab_decode, text="4th word (PWE2):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
response_pwe2_entry = tk.Entry(tab_decode)
response_pwe2_entry.grid(row=4, column=1, sticky="w", padx=5, pady=5)

decode_button = tk.Button(tab_decode, text="Decode Response", command=decode_response)
decode_button.grid(row=5, column=0, columnspan=2, pady=10)

decode_result_text = tk.Text(tab_decode, height=7, width=40, state=tk.DISABLED)
decode_result_text.grid(row=6, column=0, columnspan=2, padx=5, pady=10)

root.mainloop()
