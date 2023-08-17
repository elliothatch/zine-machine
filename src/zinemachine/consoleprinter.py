ENDC = '\033[0m'
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
INVERT = "\033[7m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"

class ConsolePrinter(object):
    def __init__(self):
        self.styles = {}
        # add void flush function
        self.device = type('obj', (object,), {'flush': lambda: None})

    def set(self, **styles):
        # print(f"Set {styles}")
        self.styles = styles
        print(ENDC, end="")
        if "bold" in styles and styles["bold"] == True:
            print(BOLD, end="")
        if "underline" in styles and (styles["underline"] == 1 or styles["underline"] == 2):
            print(UNDERLINE, end="") 
        if "double_width" in styles and styles["double_width"] == True:
            print(GREEN, end="") 
        if "invert" in styles and styles["invert"] == True:
            print(INVERT, end="") 
        if "flip" in styles and styles["flip"] == True:
            print(CYAN, end="") 



    def text(self, txt):
        print(txt, end="")

    def image(self, src, **options):
        print(f"\nImage: {src}, {options}")

    def qr(self, content, **options):
        print(f"\nQR code: {content}, {options}")

