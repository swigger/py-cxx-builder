import sys
import os
import re
import subprocess


class Embedder:
    def __init__(self, input_filename, output_obj):
        self.input_filename = input_filename
        basename = os.path.basename(input_filename)
        self.var_name = re.sub(r'[.-]', '_', basename)
        if os.path.isdir(output_obj):
            self.c_filename = os.path.join(output_obj, f"{basename}.c")
            self.output_obj = os.path.join(output_obj, basename + (".obj" if os.name == 'nt' else '.o'))
        else:
            output_dir = os.path.dirname(output_obj) or '.'
            self.c_filename = os.path.join(output_dir, f"{basename}.c")
            self.output_obj = output_obj

    def embed_file(self):
        with open(self.input_filename, 'rb') as f:
            content = f.read()

        c_array = ', '.join(f'0x{byte:02x}' for byte in content)
        c_code = f"unsigned char const {self.var_name}_content[] = {{\n {c_array}\n,0\n}};\n"
        c_code += f"unsigned int const {self.var_name}_size = sizeof({self.var_name}_content)-1;"
        return c_code

    def write_c_file(self, c_code):
        with open(self.c_filename, 'w') as f:
            f.write("#include <stddef.h>\n")  # 为了使用 sizeof
            f.write(c_code)

    def compile_c_file(self):
        if os.name == 'nt':
            command = ['cl', '/nologo', '/c', self.c_filename, '/Fo:' + self.output_obj]
        else:
            command = ['gcc', '-c', self.c_filename, '-o', self.output_obj]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error during compilation: {e}")
            sys.exit(1)  # 以代码1退出

    def clean_up(self):
        if os.path.exists(self.c_filename):
            os.remove(self.c_filename)

    def run(self):
        c_code = self.embed_file()
        self.write_c_file(c_code)
        self.compile_c_file()
        self.clean_up()


def main():
    def usage():
        print("Usage: python -m py_cxx_builder embed filename.ext out.obj")

    if len(sys.argv) != 4:
        usage()
        sys.exit(1)

    match sys.argv[1]:
        case "embed":
            input_filename, output_obj = sys.argv[2], sys.argv[3]
            if not os.path.isfile(input_filename):
                print(f"Error: {input_filename} is not a valid file.")
                sys.exit(1)
            embedder = Embedder(input_filename, output_obj)
            embedder.run()

        case _:
            usage()
            sys.exit(1)
