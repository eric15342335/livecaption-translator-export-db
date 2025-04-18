import tkinter as tk
from tkinter import filedialog, messagebox, Menu
import sqlite3
import subprocess
import os
import tempfile
import webbrowser

# Try to import pyperclip for clipboard operations
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

class SQLiteReaderApp:
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("LiveCaption Translator DB Reader")
        
        # Make Windows aware of application name for taskbar grouping
        try:
            # For Windows only
            if os.name == 'nt':
                self.root.wm_iconbitmap(default=None)
                self.root.tk.call('wm', 'iconphoto', self.root._w, tk.PhotoImage())
        except Exception:
            pass
        
        # Center the window on screen
        self.center_window(500, 300)
        
        # Create menus
        self.create_menus()
        
        # Create widgets
        self.create_widgets()
        
        # Set focus to this window
        self.root.focus_force()
    
    def create_menus(self):
        """Create the application menu bar."""
        menubar = Menu(self.root)
        
        # File menu
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Help menu
        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        
        self.root.config(menu=menubar)
    
    def create_widgets(self):
        """Create and arrange all UI widgets."""
        # Instructions label
        tk.Label(self.root, text="Select SQLite database file:").pack(pady=10)
        
        # Frame for file selection
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10, fill='x', padx=20)
        
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("")  # Default empty
        self.file_entry = tk.Entry(file_frame, textvariable=self.file_path_var, width=40)
        self.file_entry.pack(side=tk.LEFT, fill='x', expand=True)
        
        browse_btn = tk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        # Execute button
        execute_btn = tk.Button(self.root, text="Execute Query", command=self.execute_query)
        execute_btn.pack(pady=20)
        
        # Status label
        self.status_var = tk.StringVar()
        status_label = tk.Label(self.root, textvariable=self.status_var, wraplength=450)
        status_label.pack(pady=10)
    
    def center_window(self, width, height):
        """Center the window on the screen."""
        # Get screen width and height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position coordinates
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # Set the window size and position
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make window non-resizable for consistent appearance
        self.root.resizable(False, False)
    
    def browse_file(self):
        """Open file dialog to select SQLite database file."""
        filetypes = [("SQLite Database", "*.db"), ("All Files", "*.*")]
        filename = filedialog.askopenfilename(
            title="Select a SQLite Database File",
            filetypes=filetypes,
            initialfile="translation_history.db"
        )
        if filename:
            self.file_path_var.set(filename)
    
    def execute_query(self):
        """Execute the SQL query on the selected database file."""
        db_path = self.file_path_var.get()
        if not db_path:
            self.status_var.set("Please select a database file first.")
            return
        
        if not os.path.exists(db_path):
            self.status_var.set(f"File not found: {db_path}")
            return
        
        sql_query = """
        WITH FilteredTexts AS (
          -- First, select distinct source texts with their minimum ID
          SELECT DISTINCT SourceText, MIN(Id) as MinId
          FROM TranslationHistory
          GROUP BY SourceText
        ),
        NonContainedTexts AS (
          -- Then filter out texts that are contained within others
          SELECT FT1.SourceText, FT1.MinId
          FROM FilteredTexts FT1
          WHERE NOT EXISTS (
            SELECT 1 
            FROM FilteredTexts FT2
            WHERE FT2.SourceText != FT1.SourceText
            AND FT2.SourceText LIKE '%' || FT1.SourceText || '%'
          )
        )

        -- Finally, concatenate the filtered texts in ID order
        select group_concat(SourceText) from (SELECT SourceText
        FROM NonContainedTexts
        ORDER BY MinId ASC) as a
        """
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchone()[0]  # Get the first column of the first row
            conn.close()
            
            if result:
                # Copy to clipboard if pyperclip is available
                if HAS_PYPERCLIP:
                    pyperclip.copy(result)
                    clipboard_msg = "Result copied to clipboard and "
                else:
                    clipboard_msg = ""
                
                # Open in Notepad
                self.open_in_notepad(result)
                
                self.status_var.set(f"Query executed successfully. {clipboard_msg}opened in Notepad.")
            else:
                self.status_var.set("Query executed but returned no results.")
        except sqlite3.Error as e:
            self.status_var.set(f"SQLite error: {e}")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
    
    def open_in_notepad(self, text):
        """Open the result in Notepad."""
        try:
            # Create a temporary file with the text content
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_file:
                temp_file.write(text)
                temp_file_path = temp_file.name
            
            # Open the file with Notepad
            subprocess.Popen(['notepad.exe', temp_file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Notepad: {e}")
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        if HAS_PYPERCLIP:
            pyperclip.copy(text)
            messagebox.showinfo("Copied", "Text copied to clipboard successfully!")
        else:
            messagebox.showinfo("Not Available", "Clipboard functionality is not available. Please install pyperclip.")
    
    def show_about(self):
        """Show the about dialog."""
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Center the about window
        width, height = 400, 300
        about_window.resizable(False, False)
        
        # Calculate position based on main window
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        
        # Ensure window is on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = max(0, min(x, screen_width - width))
        y = max(0, min(y, screen_height - height))
        
        # Set the window size and position
        about_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add some padding
        frame = tk.Frame(about_window, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(frame, text="LiveCaption Translator SQLite Database Reader", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Version and author info
        info_text = "Version: 1.0\nAuthor: @eric15342335\nCoding Assistant: Claude 3.7 Sonnet"
        info_label = tk.Label(frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 15), anchor=tk.W)
        
        # Description
        desc_label = tk.Label(frame, 
                             text="This program extracts and combines text entries from a LiveCaption Translator SQLite database.", 
                             wraplength=350, 
                             justify=tk.LEFT)
        desc_label.pack(pady=(0, 15), anchor=tk.W)
        
        # Links
        link1 = tk.Label(frame, text="LiveCaptions-Translator GitHub Repository", fg="blue", cursor="hand2")
        link1.pack(anchor=tk.W, pady=(0, 5))
        link1.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/SakiRinn/LiveCaptions-Translator"))
        
        link2 = tk.Label(frame, text="Author's Website", fg="blue", cursor="hand2")
        link2.pack(anchor=tk.W, pady=(0, 15))
        link2.bind("<Button-1>", lambda e: webbrowser.open_new("https://eric15342335.github.io"))
        
        # Close button
        close_button = tk.Button(frame, text="Close", command=about_window.destroy)
        close_button.pack(pady=(10, 0))
        
        # Set focus to the about window
        about_window.focus_force()

def main():
    """Main entry point for the application."""
    # Create the root window
    root = tk.Tk()
    
    # Initialize the app
    app = SQLiteReaderApp(root)
    
    # Check for dependencies
    if not HAS_PYPERCLIP:
        messagebox.showwarning(
            "Missing Module", 
            "The 'pyperclip' module is not installed. Clipboard functionality will be disabled.\n\n"
            "To enable clipboard functionality, install pyperclip using pip:\n"
            "pip install pyperclip"
        )
    
    # Start the main event loop
    root.mainloop()

if __name__ == "__main__":
    main()
