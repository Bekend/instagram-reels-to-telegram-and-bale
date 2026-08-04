import os
import paramiko

VPS_IP = "148.135.207.189"
VPS_USER = "root"
VPS_PASS = "Farzad1383"
REMOTE_DIR = "/root/instagram_reels_telegram_bot"

LOCAL_DIR = os.path.dirname(os.path.dirname(__file__))

FILES_TO_UPLOAD = [
    "main.py",
    "database.py",
    "instagram_fetcher.py",
    "instagram_comments.py",
    "bale_bot.py",
    "telegram_bot.py",
    "static/app.js",
    "static/index.html",
    "static/styles.css"
]

def deploy():
    print(f"Connecting to VPS SSH {VPS_USER}@{VPS_IP}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=VPS_IP, username=VPS_USER, password=VPS_PASS, timeout=15)
    
    print("Connected! Opening SFTP...")
    sftp = ssh.open_sftp()
    
    try:
        sftp.mkdir(f"{REMOTE_DIR}/static")
    except Exception:
        pass
        
    for rel_path in FILES_TO_UPLOAD:
        local_path = os.path.join(LOCAL_DIR, rel_path)
        remote_path = f"{REMOTE_DIR}/{rel_path}".replace("\\", "/")
        print(f"Uploading {rel_path} -> {remote_path}...")
        sftp.put(local_path, remote_path)
        
    sftp.close()
    print("Files uploaded successfully!")

    print("Checking running processes on VPS...")
    stdin, stdout, stderr = ssh.exec_command("pkill -f 'python.*main.py' || pkill -f 'uvicorn' || true")
    print(stdout.read().decode())
    
    print("Starting main.py backend daemon on VPS...")
    start_cmd = f"nohup python3 {REMOTE_DIR}/main.py > {REMOTE_DIR}/app.log 2>&1 &"
    stdin, stdout, stderr = ssh.exec_command(start_cmd)
    
    import time
    time.sleep(4)
    
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep main.py")
    ps_output = stdout.read().decode()
    print("VPS Running processes:\n", ps_output)
    
    ssh.close()
    print("Deployment completed successfully!")

if __name__ == "__main__":
    deploy()
