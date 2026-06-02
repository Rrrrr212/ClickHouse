import subprocess
try:
    output = subprocess.check_output(['git', 'diff', 'master'], stderr=subprocess.STDOUT)
    print(output.decode('utf-8'))
except subprocess.CalledProcessError as e:
    print(f"Error: {e.output.decode('utf-8')}")
