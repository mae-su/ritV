import os
import shutil
import subprocess
import time
dist_path = '.\dist3'
src_path = '.\src'
excluded_files = ['.\\ritv.credentials.aes','.\\bot.token',dist_path,src_path, '.\\post.py']

# Delete './dist3/' and all of its contents recursively
if os.path.exists('.\dist3'):
    print('Deleting existing .\\dist3 directory.')
    shutil.rmtree('.\dist3')

if os.path.exists('.\dist'):
    print('Deleting existing .\\dist directory.')
    shutil.rmtree('.\dist')

if os.path.exists('.\\build'):
    print('Deleting existing .\\build directory.')
    shutil.rmtree('.\\build')

if os.path.exists('.\\__pycache__'):
    print('Deleting existing .\\__pycache__ directory.')
    shutil.rmtree('.\\__pycache__')

print('Encrypting source:')
subprocess.run(['pyarmor', 'gen', '-O', dist_path, '-r', '-i', src_path])
for item in os.listdir('.'):
    item_path = os.path.join('.', item)
    dist_item_path = os.path.join(dist_path, item)
    
    if item_path not in excluded_files:  # Check if item is not excluded
        if os.path.isdir(item_path):
            shutil.copytree(item_path, dist_item_path, dirs_exist_ok=True)
        elif os.path.isfile(item_path):
            # Copy file, overwrite if exists
            shutil.copy(item_path,dist_path)
        print(f'Copied {item_path} to {dist_item_path}')
    else:
        print(f'Excluded {item_path}')
os.system('cls')
print('Compiling main.exe from encryption:')
os.system('pyinstaller --noconfirm --onedir --console --clean --collect-all "smtplib" --collect-all "mysql" --collect-all "rich" --collect-all "pyAesCrypt" --collect-all "email" --collect-all "discord"  "C:/Users/maeib/OneDrive/Documents/GitHub/ritV/dist3/main.py"')
os.system('cls')
print('Testing main.exe!')
time.sleep(2)
os.chdir('.\\dist\\main\\')
print('main.exe output:')
os.system('.\\main.exe')