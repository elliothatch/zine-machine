ENDC = '\033[0m'
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
INVERT = "\033[7m"

class ConsolePrinter(object):
    def __init__(self):
        self.styles = {}

    def set(self, **styles):
        # print(f"Set {styles}")
        self.styles = styles
        print(ENDC, end="")
        if "bold" in styles and styles["bold"] == 1:
            print(BOLD, end="")
        if "underline" in styles and (styles["underline"] == 1 or styles["underline"] == 2):
            print(UNDERLINE, end="") 


    def text(self, txt):
        print(txt, end="")

    def image(self, src, **options):
        print(f"\nImage: {src}, {options}")

